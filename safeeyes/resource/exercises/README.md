# SafeEyes Exercise Animations (Issue #439)

Original CC0 1.0 Universal illustrations for SafeEyes break exercises.

- **License:** CC0 1.0 Universal (public domain) - no attribution required, but appreciated.
- **Source:** Original stick-figure outline illustrations generated for SafeEyes. See `*.svg` source files.
- **Format:** Animated GIF, 512x512, 12fps, 36 frames (3s loop), optimized with Pillow. SVG source included.
- **Usage:** Referenced via `safeeyes/config/safeeyes.json` `image: "exercises/<slug>.gif"` and resolved via `safeeyes/utility.py:get_resource_path()` (checks `~/.config/safeeyes/resource/` then `safeeyes/resource/`). Break screen `safeeyes/ui/break_screen.py:__set_break_image()` supports animated GIF via `GdkPixbuf.PixbufAnimation` (issue #439).

## Exercises

### Short breaks (13)
- gently-close-eyes.gif - Gently close your eyes
- take-five-breaths.gif - Take five slow, deep breaths
- rotate-clockwise.gif - Rotate your eyes in clockwise direction
- relax-shoulders.gif - Relax your shoulders and drop them away from your ears
- blink-eyes.gif - Blink your eyes
- stretch-neck-side.gif - Stretch your neck gently from side to side
- roll-eyes.gif - Roll your eyes a few times to each side
- check-posture.gif - Check your posture and sit back comfortably
- rotate-counterclockwise.gif - Rotate your eyes in counterclockwise direction
- unclench-jaw.gif - Unclench your jaw and relax your face
- focus-far-distance.gif - Focus on a point in the far distance
- stretch-wrists-fingers.gif - Stretch your wrists and fingers
- have-water.gif - Have some water

### Long breaks (6 + 7 Workrave deduped)
- stand-stretch-back-legs.gif, lean-back-relax.gif, walk-refill-water.gif, walk-while.gif, step-away-mobility.gif, rest-eyes-distant.gif
- shoulder-arm-stretch.gif - Workrave Shoulder-arm stretch (deduped, original)
- finger-stretch.gif - Workrave Finger stretch (distinct from Stretch wrists)
- backward-shoulder-stretch.gif - Workrave Backward shoulder stretch
- look-into-darkness.gif - Workrave Look into the darkness (palming, distinct from Gently close)
- move-shoulders.gif - Workrave Move the shoulders (propeller)
- move-shoulders-up-down.gif - Workrave Move shoulders up/down (chair pushup)
- turn-head.gif - Workrave Turn your head

### Skipped Workrave duplicates (semantic dedup)
- Move the eyes (duplicate Rotate/Roll eyes)
- Train focusing the eyes (duplicate Focus far distance / Rest eyes distant)
- Neck tilt stretch (duplicate Stretch neck side to side)

Disabled Workrave (6) not included: Wrist/lower arm desk stretch, Relax the eyes, Fist roll, Move shoulder blades, Stretch your back, Neck stretch

## Generation

See `/tmp/generate_exercises.py` (Pillow-based procedural outline animation, CC0). Regenerate:

```bash
python3 /tmp/generate_exercises.py
```

Total 26 GIFs ~3.0M, 52 files (gif+svg).

## Migration

- `safeeyes/config/safeeyes.json` bumped `meta.config_version` 6.0.5→6.0.6, added `image` to all breaks.
- `safeeyes/configuration.py` `force_upgrade_keys = ["long_breaks", "short_breaks"]` forces user config upgrade on next `Config.load()` (see `configuration.py:48`).

References:
- Issue #439: https://github.com/slgobinath/SafeEyes/issues/439
- Workrave exercises: https://github.com/rcaelers/workrave/blob/main/ui/data/exercises/exercises.xml.in
- EyeLeo theme approach: https://github.com/binhtddev/safeeyes-eyeleo-theme (copyrighted, not reused)
