import time

import numpy as np
import sounddevice as sd


def monitor_audio(threshold_factor=3.0, block_duration=0.1, cooldown=2.0):
    """
    Listens to an audio input device and prints when it detects spikes
    relative to a smoothed baseline level.

    This is a first step toward triggering a bobber catch on an audio spike.
    You should fish manually while this runs and watch the console output to
    see if bobber splashes produce clear spikes.
    """

    sample_rate = 44100  # Hz
    block_size = int(sample_rate * block_duration)

    print("=== Audio Monitor ===")
    print("Press Ctrl+C to stop.")
    print(f"Sample rate: {sample_rate} Hz, block: {block_duration:.3f} s")

    # Show which device we are using (default input)
    try:
        default_in = sd.default.device[0]
        devices = sd.query_devices()
        print(f"Using input device index: {default_in}")
        print(f"Device info: {devices[default_in]}")
    except Exception:
        print("Using default audio input device (could not query details).")

    baseline_rms = None
    alpha = 0.98  # smoothing factor for baseline (closer to 1 = slower change)
    last_spike_time = 0.0

    try:
        while True:
            # Record a short block from the default input device
            data = sd.rec(
                frames=block_size,
                samplerate=sample_rate,
                channels=1,
                dtype="float32",
            )
            sd.wait()

            # Compute RMS (volume level) for this block
            rms = float(np.sqrt(np.mean(np.square(data))))

            # Initialize baseline on first non-zero-ish sample
            if baseline_rms is None:
                baseline_rms = max(rms, 1e-6)
                print(f"Initial baseline RMS: {baseline_rms:.6f}")
                continue

            # Exponential moving average baseline
            baseline_rms = alpha * baseline_rms + (1.0 - alpha) * rms

            # Simple spike condition: current RMS much higher than baseline
            now = time.time()
            spike = (
                rms > baseline_rms * threshold_factor
                and now - last_spike_time > cooldown
            )

            # Print a low-rate status line for debugging
            print(
                f"RMS: {rms:.6f}  baseline: {baseline_rms:.6f}  "
                f"ratio: {rms / baseline_rms if baseline_rms > 0 else 0:.2f}"
                + ("  <-- SPIKE" if spike else "")
            )

            if spike:
                last_spike_time = now
                # This is where we would eventually trigger a catch
                # (e.g., Shift+RightClick and recast) once we confirm
                # that bobber splashes reliably cause these spikes.

    except KeyboardInterrupt:
        print("\nStopping audio monitor...")


if __name__ == "__main__":
    # You can tune these numbers once you see how the levels behave.
    monitor_audio(
        threshold_factor=3.0,  # how many times louder than baseline counts as a spike
        block_duration=0.1,    # seconds per analysis block
        cooldown=2.0,          # minimum seconds between spikes
    )
