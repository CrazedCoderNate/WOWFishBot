import time
import random

import cv2
import mss
import numpy as np
import pyautogui
import sounddevice as sd


def find_bobber_center(frame_bgra):
    """Locate the bobber by color (red + blue feathers) in a BGRA frame.

    Returns (cx, cy) in *cropped frame* coordinates, or (None, None) if not found.
    """
    # Convert BGRA -> BGR -> HSV for easier color thresholding
    frame_bgr = cv2.cvtColor(frame_bgra, cv2.COLOR_BGRA2BGR)
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)

    # Color ranges are approximate and may need tuning based on your monitor/game settings.
    # Red wraps around the hue axis, so we use two ranges.
    lower_red1 = np.array([0, 80, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 80, 50])
    upper_red2 = np.array([180, 255, 255])

    # Darkish blue range for the feathers
    lower_blue = np.array([100, 80, 40])
    upper_blue = np.array([140, 255, 255])

    mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask_red = cv2.bitwise_or(mask_red1, mask_red2)
    mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)

    # Combine red and blue
    mask = cv2.bitwise_or(mask_red, mask_blue)

    # Optional: small morphological cleanup
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.dilate(mask, kernel, iterations=1)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, None

    # Use the largest colored blob as the bobber
    largest = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest)
    cx = x + w // 2
    cy = y + h // 2
    return cx, cy


def monitor_audio_and_bobber(
    top,
    left,
    width,
    height,
    audio_threshold_factor=1.5,
    audio_block_duration=0.1,
    audio_cooldown=2.0,
    post_cast_wait=5.0,
    watchdog_timeout=30.0,
):
    """Combined bot: locate bobber by color + trigger catch on audio spikes.

    - Screen region is defined by (top, left, width, height).
    - Audio spikes are detected relative to a rolling baseline RMS.
    - On spike + valid bobber center, performs Shift+right-click and recast.
    """

    pyautogui.FAILSAFE = True

    sample_rate = 44100
    block_size = int(sample_rate * audio_block_duration)

    print("Monitoring region:", {"top": top, "left": left, "width": width, "height": height})
    print("Audio sample rate:", sample_rate, "Hz, block:", audio_block_duration, "s")
    print("Audio spike threshold factor:", audio_threshold_factor)
    print("Press 'q' in the video window to quit.")
    print("Starting in 5 seconds...")
    time.sleep(5)

    # Audio baseline state
    baseline_rms = None
    audio_alpha = 0.98  # smoothing factor for baseline
    last_spike_time = 0.0

    # Action cooldown / watchdog
    last_action_time = time.time()

    with mss.mss() as sct:
        monitor = {"top": top, "left": left, "width": width, "height": height}

        try:
            while True:
                # --- Screen capture ---
                img = np.array(sct.grab(monitor))  # BGRA

                # Locate bobber center by color
                bobber_cx, bobber_cy = find_bobber_center(img)
                bobber_found = bobber_cx is not None and bobber_cy is not None

                # Draw debug overlays on the cropped frame
                cv2.rectangle(img, (0, 0), (width - 1, height - 1), (0, 0, 255), 2)
                if bobber_found:
                    cv2.circle(img, (bobber_cx, bobber_cy), 8, (0, 255, 0), 2)

                # --- Audio capture ---
                data = sd.rec(
                    frames=block_size,
                    samplerate=sample_rate,
                    channels=1,
                    dtype="float32",
                )
                sd.wait()

                rms = float(np.sqrt(np.mean(np.square(data))))

                if baseline_rms is None:
                    baseline_rms = max(rms, 1e-6)
                    print(f"Initial audio baseline RMS: {baseline_rms:.6f}")
                    # Show initial frame while baseline stabilizes
                    cv2.imshow("Audio Bobber Bot", img)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                    continue

                baseline_rms = audio_alpha * baseline_rms + (1.0 - audio_alpha) * rms
                ratio = rms / baseline_rms if baseline_rms > 0 else 0.0

                now = time.time()
                spike = (
                    ratio > audio_threshold_factor
                    and now - last_spike_time > audio_cooldown
                )

                # Text overlay with audio info
                cv2.putText(
                    img,
                    f"RMS: {rms:.4f} ratio: {ratio:.2f}" + (" SPIKE" if spike else ""),
                    (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 255) if spike else (255, 255, 0),
                    2,
                )

                # Display window
                cv2.imshow("Audio Bobber Bot", img)

                # --- Action logic ---
                if spike and bobber_found and (now - last_action_time > 2.0):
                    last_spike_time = now

                    bobber_x = left + bobber_cx
                    bobber_y = top + bobber_cy
                    print(f"Audio spike + bobber located at ({bobber_x}, {bobber_y}). Catching...")

                    # Shift + Right Click on bobber
                    pyautogui.keyDown("shift")
                    pyautogui.rightClick(bobber_x, bobber_y)
                    pyautogui.keyUp("shift")

                    # Wait for looting
                    time.sleep(random.uniform(1.0, 1.5))

                    # Recast (Press '1')
                    print("Recasting after catch...")
                    pyautogui.press("1")

                    # Wait for bobber to land
                    time.sleep(post_cast_wait)

                    # Reset timers/baseline reference
                    last_action_time = time.time()

                    # Continue to next loop iteration
                    continue

                # Watchdog: ensure we are still casting every watchdog_timeout seconds
                if now - last_action_time > watchdog_timeout:
                    print("No catch/cast for a while. Forcing recast...")
                    pyautogui.press("1")
                    time.sleep(post_cast_wait)
                    last_action_time = time.time()

                # Key to exit
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

        finally:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    # Start with the same region you tuned for the visual bot.
    # Adjust these values if needed.
    monitor_audio_and_bobber(
        top=180,
        left=4600,
        width=2600,
        height=800,
        audio_threshold_factor=2.0,   # your splash ratio was ~2.3
        audio_block_duration=0.1,
        audio_cooldown=2.0,
        post_cast_wait=5.0,
        watchdog_timeout=30.0,
    )
