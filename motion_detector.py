import cv2
import numpy as np
import mss
import time
import pyautogui
import random

def monitor_region(top, left, width, height):
    """
    Monitors a specific screen region for visual changes (motion) and triggers a
    mouse interaction when a threshold is met.
    """
    # Safety feature: shoving the mouse to a corner will abort the script
    pyautogui.FAILSAFE = True

    # MSS is efficient for screen capture
    with mss.mss() as sct:
        monitor = {"top": top, "left": left, "width": width, "height": height}
        
        print(f"Monitoring region: {monitor}")
        print("Press 'q' to quit.")
        print("Starting detection in 5 seconds...")
        time.sleep(5)

        # Initialize the first frame
        first_frame = None
        
        # Debounce/Cooldown tracker
        last_action_time = time.time()
        
        while True:
            # 1. Capture the screen region
            img = np.array(sct.grab(monitor))
            
            # 2. Pre-processing
            # Convert to grayscale to simplify analysis
            gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
            # Blur to remove minor noise (water ripples)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            if first_frame is None:
                first_frame = gray
                continue

            # 3. Calculate Difference
            frame_delta = cv2.absdiff(first_frame, gray)
            
            # 4. Thresholding
            thresh = cv2.threshold(frame_delta, 30, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)

            # 5. Contour Detection
            contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            event_detected = False
            target_x, target_y = 0, 0

            for contour in contours:
                # Ignore small movements
                if cv2.contourArea(contour) < 1500: 
                    continue
                
                # Valid movement detected
                event_detected = True
                (x, y, w, h) = cv2.boundingRect(contour)
                
                # Calculate the center of the splash for clicking
                # We add 'left' and 'top' to convert relative image coords to absolute screen coords
                target_x = left + x + w // 2
                target_y = top + y + h // 2

                # Visual debug: Draw rectangle on the feed
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                # We break after the first valid contour to avoid double-clicking
                break 

            # Always visualize the full scan region for debugging
            cv2.rectangle(img, (0, 0), (width - 1, height - 1), (0, 0, 255), 2)
            cv2.putText(
                img,
                f"Scan region: top={top}, left={left}, w={width}, h={height}",
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2,
            )

            # Display the monitoring window
            cv2.imshow("Monitor Feed", img)
            
            # 6. Action Logic (The "Bot" part)
            now = time.time()
            if event_detected and (now - last_action_time > 2):
                print(f"Splash detected! Interacting at {target_x}, {target_y}")
                
                # A. Catch the Fish (Shift + Right Click on Bobber)
                pyautogui.keyDown('shift')
                pyautogui.rightClick(target_x, target_y)
                pyautogui.keyUp('shift')
                
                # B. Wait for Looting
                # Randomize slightly to test heuristic detection
                time.sleep(random.uniform(1.0, 1.5)) 
                
                # C. Recast (Press '1')
                print("Recasting...")
                pyautogui.press('1')
                
                # D. Wait for bobber to land
                # This is critical: prevents the splash of the cast from triggering the detector immediately
                time.sleep(5.0)
                
                # E. Reset Reference
                # The bobber might have landed in a slightly different spot, so we reset the reference frame
                first_frame = None
                last_action_time = time.time()
                
                # Clear the event queue to prevent backlog processing
                continue

            # Watchdog: if no casting has been done within 30 seconds, force a recast
            if now - last_action_time > 30:
                print("No cast detected for 30 seconds. Forcing recast...")
                pyautogui.press('1')
                time.sleep(5.0)
                first_frame = None
                last_action_time = time.time()

            # Press 'q' to exit
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cv2.destroyAllWindows()

if __name__ == "__main__":
    # Example coordinates - YOU MUST UPDATE THESE
    # Use a tool like 'PrintScreen' or standard screenshot tool to find the 
    # X, Y, Width, Height of the area where your bobber sits.
    monitor_region(top=180, left=4600, width=2600, height=800)