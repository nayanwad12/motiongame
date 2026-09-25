# One Shape

One element, never cut, morphs through 12 UI states in 7 bars at 120 BPM (14 s, seamless loop).
White components, neon-green accent (`#35FF69`), Geist, warm-gray canvas.

- `motion.html`: the scene as a single self-contained file (Geist inlined). Open it to preview live.
- `motion.mp4`: 1440×1440 at 60 fps, 4-subframe motion blur, placeholder audio (see below).
- `beat-sheet.png`: one frame per beat.

## Beat grid

| Bar | Beat 1 | Beat 2 | Beat 3 | Beat 4 |
|---|---|---|---|---|
| 1 | button, cursor glides in | click | → loader | → check |
| 2 | → dynamic island | click | → player | play ▸ pause morph |
| 3 | grab playhead | scrub | release, → slider | volume slider |
| 4 | drag to max | drag past max: shape stretches | release, springs back | → toggle |
| 5 | toggle flips | → tabs (knob becomes indicator) | Revenue | Growth |
| 6 | → chart draws | hover tooltip | hover to peak | → ⌘K |
| 7 | type "to" | "toa" | enter → toast | → button |

## How it works

- `seek(t)` computes every style from time. There are no CSS transitions, no timers and no state between frames.
- Springs are closed-form step responses. A value that changes target many times is a sum of one spring per change. The sum is evaluated periodically, so position and velocity at t = 14 match t = 0.
- The toggle knob and the tab indicator are one element with two edges on two springs: a stiff one for the leading edge and a soft one for the trailing edge.
- The playhead and volume knob are direct manipulation: while the cursor is held, the value comes from the cursor position. Past max, the shape rubber-bands, and on release it springs back from wherever it was, keeping its velocity.
- The knob carries through from playhead to volume knob to toggle knob to tab indicator. All content is clipped to the shape's outline.

## Pipeline

```sh
npm install && pip install numpy scipy pillow imageio-ffmpeg
npm run stills                    # one frame per beat → out/sheet.png (also exports out/cues.json)
npm run song                      # synthesize the placeholder groove
npm run audio -- ../path/to/song  # beat analysis, 7-bar cut from a downbeat, UI sounds placed by measured peak
npm run render                    # 840 frames × 4 subframes → ffmpeg tmix → out/motion.mp4
```

`tools/audio.py` finds tempo with autocorrelation, finds phase with a comb filter and a least-squares grid fit, and snaps the grid to transients in the time domain. It picks the downbeat from harmonic change, and time-stretches to exactly 120 BPM if the song is off. Its report (`out/audio_report.json`) includes the grid error measured on the final cut.

**Audio note:** the current `motion.mp4` uses a synthesized placeholder groove. This environment's network policy blocks mixkit.co, so the licensed track still needs to be downloaded, and the mix is one `npm run audio -- <song>` + `npm run render` away.
