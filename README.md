# WOWFishBot

A small World of Warcraft fishing helper with three different detection modes:

- `motion_detector.py` – pure visual motion detection in a fixed screen region.
- `audio_detector.py` – monitors audio for spikes and logs them (no clicks).
- `audio_bobber_bot.py` – combines audio spikes with color-based bobber detection and actually catches fish.

**Recommended:** Use `audio_bobber_bot.py`. Pure visual methods can glitch on private servers or with unstable frame rates, while audio spikes from the bobber splash tend to be more reliable.

> **Disclaimer:** Use at your own risk. Automation may violate game terms of service.

---

## 1. Requirements

Python 3.9+ is recommended.

Install dependencies (ideally in a virtual environment):

```bash
pip install -r requirements.txt
```

The main packages are:

- `opencv-python` – screen image processing and debug windows.
- `mss` – efficient screen capture.
- `pyautogui` – mouse/keyboard automation.
- `sounddevice` – audio capture (mic or system loopback).
- `numpy` – numeric operations.

---

## 2. General setup notes

- **Run windowed or borderless WoW** so the bobber region is predictable.
- **Turn down all music and ambient sound** in WoW options.
  - Keep only sound effects that include the bobber splash.
  - This improves the signal-to-noise ratio for audio detection.
- **Configure your monitor region** in each script:
  - The `top`, `left`, `width`, `height` parameters define the rectangle where the bot looks.
  - Coordinates are in absolute desktop pixels.
  - You will need to adjust them based on your monitor layout and game window position.
- **Multi-monitor setups:**
  - The region can be on any monitor. Just set `left`/`top` correctly (they may be large if the game is on a right-hand monitor).

---

## 3. `motion_detector.py` – visual motion-based bot

This script watches a rectangular region of the screen for **visual motion** (frame differences) and triggers:

1. Shift+right-click on the detected splash.
2. A short looting delay.
3. Pressing `1` to recast.
4. A delay to let the new bobber land.

### How it works (high level)

- Captures frames from a configured region via `mss`.
- Converts to grayscale, blurs, and computes frame differences from a reference frame.
- Thresholds and finds contours to detect **significant motion**.
- Draws:
  - A **green box** around detected motion.
  - A **red border** around the full scan region in the debug window.
- On a valid motion event (contour large enough and cooldown passed):
  - Moves the mouse to that point, performs Shift+right-click, waits, recasts, and waits again.

### When to use

- Works best on **stable, non-glitchy graphics**.
- Can be affected by:
  - Private server visual glitches.
  - UI overlays or unexpected animation.

Because of these issues, it is **not recommended** as the primary method on private servers. Use it mainly for debugging or as a fallback.

### Running it

```bash
python motion_detector.py
```

Edit the bottom of the file to set your region, for example:

```python
monitor_region(top=180, left=4600, width=2600, height=800)
```

---

## 4. `audio_detector.py` – audio spike monitor (no automation)

This script **only listens to audio** and prints/logs spikes. It does **not** move the mouse or click.

### Purpose

- Helps you verify that the **bobber splash sound** produces a clear audio spike.
- Lets you tune:
  - `threshold_factor` – how much louder than baseline counts as a spike.
  - `block_duration` – how often audio is sampled.
  - `cooldown` – minimum time between spikes.

### How it works

- Uses `sounddevice` to record small blocks from an audio input device.
- Computes RMS (volume) for each block and maintains a smoothed baseline.
- Prints lines like:

  ```
  RMS: 0.0021  baseline: 0.0009  ratio: 2.35  <-- SPIKE
  ```

- You can fish manually and watch whether the splash sound corresponds to those `SPIKE` lines.

### System audio (loopback) hint

If you play with **headphones**, you should:

- Enable a loopback device (e.g. `Stereo Mix`, `What U Hear`, etc.) in Windows **Recording** devices.
- Set that device as the **default input** so `sounddevice` captures the game audio instead of the mic.

### Running it

```bash
python audio_detector.py
```

Edit the call at the bottom if you want to adjust the thresholds:

```python
monitor_audio(
    threshold_factor=2.0,
    block_duration=0.1,
    cooldown=2.0,
)
```

---

## 5. `audio_bobber_bot.py` – recommended audio + visual hybrid bot

This is the **recommended** bot for actual automated catching, especially on private servers where visuals can glitch.

It:

- Uses **color detection** to locate the bobber in the captured region.
  - Assumes the bobber is the only distinct object with **red and dark blue feathers**.
- Uses **audio spikes** (e.g., ratio ~2.3 vs. baseline) to detect the bobber splash.
- Only catches when **both**:
  - A spike is detected.
  - A valid bobber position is found.

### How it works

1. Captures a screen region via `mss`.
2. Converts the frame to HSV and builds masks for red + blue to find the bobber.
   - Draws a green circle where it thinks the bobber is.
3. Simultaneously records short audio blocks using `sounddevice`.
   - Maintains baseline RMS.
   - Computes `ratio = rms / baseline` and compares against `audio_threshold_factor`.
4. On 
   - `ratio > audio_threshold_factor`,
   - bobber located,
   - and cooldown passed:

   It:
   - Performs Shift+right-click at the bobber position.
   - Waits briefly for looting.
   - Presses `1` to recast.
   - Waits a bit (`post_cast_wait`) for the new bobber to land.
   - Resumes detection.

5. A **watchdog** will press `1` to recast if nothing has happened within `watchdog_timeout` seconds.

### Why this is recommended

- Visual-only motion detection can fail when:
  - Private server graphics stutter or glitch.
  - Other on-screen motion confuses the detector.
- The splash **sound** is often much more consistent than the visual animation.
- Combining audio spike detection with bobber color makes it more robust.

### Sound configuration tips

Inside World of Warcraft:

- **Turn down or disable:**
  - Music
  - Ambient sounds
- **Keep:**
  - Sound effects, especially those including the fishing bobber splash.

This ensures that the splash stands out in the audio stream and the ratio spikes are clean.

### Monitor / region configuration

At the bottom of `audio_bobber_bot.py` you’ll see:

```python
monitor_audio_and_bobber(
    top=180,
    left=4600,
    width=2600,
    height=800,
    audio_threshold_factor=2.0,   # splash ratio was ~2.3 in testing
    audio_block_duration=0.1,
    audio_cooldown=2.0,
    post_cast_wait=5.0,
    watchdog_timeout=30.0,
)
```

You **must** adjust `top`, `left`, `width`, and `height` for your own setup:

- Take a screenshot and determine the pixel coordinates of the area where the bobber appears.
- On multi-monitor systems, `left` may be large (e.g. if your game is on a far-right monitor).
- Keep the region as tight as practical around the water + bobber to reduce false positives in color detection.

### Running it

```bash
python audio_bobber_bot.py
```

While running:

- A window titled `Audio Bobber Bot` will show:
  - Red border = scan area.
  - Green circle = detected bobber position.
  - Text line with current `RMS` and `ratio`, and `SPIKE` when a spike is detected.
- Press `q` in that window to stop.

---

## 6. Safety notes

- `pyautogui.FAILSAFE` is enabled:
  - Flinging the mouse to a screen corner should abort the script.
- Always test with the bot in a safe environment first.
- Keep in mind the game’s terms of service and your own risk tolerance when using automation.
