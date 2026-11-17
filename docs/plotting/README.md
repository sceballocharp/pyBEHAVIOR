# Plotting

This document describes live plotting and result visualization in `pyBEHAVIOR_v8.py`.

## Responsibilities

Plotting provides:

- Live signal display for the primary behavior signal.
- Extra task-specific signal traces, such as Lever licks on `ai0` and tAC-family left/right licks.
- Separate overlay traces for reward output, sound epoch timing, and trial state.
- ITI shading after trial end.
- A results window with recent trial outcomes, rates, conditions, and crossing durations.
- A simple `.bin` viewer through `open_bin()`.

## Threading Contract

Plotting happens on the Tkinter main thread. Acquisition code queues drawing work:

```python
self.plot_queue.put(("plot", (times, values)))
self.plot_queue.put(("results", None))
self.plot_queue.put(("log", message))
```

`_drain_plot_queue()` consumes those messages on a 50 ms GUI timer. If multiple plot messages are waiting, it keeps only the newest plot payload and discards older plot frames. Log/status messages are still processed, and multiple pending results refreshes are collapsed into one redraw. This prevents the GUI from falling behind and showing delayed live traces.

## Live Plot Data Sources

| Data | State or function |
| --- | --- |
| Primary behavior trace | `time_buffer`, `data_buffer` |
| Lever lick trace | `lever_lick_buffer`, sampled from `ai0` for live plotting |
| tAC-family lick traces | `tac_left_buffer`, `tac_right_buffer` |
| Trigger/reward pulses | `trigger_pulses`, `record_trigger_pulse()` |
| Sound epoch bars | `sound_outputs`, `record_sound_output()` |
| Trial state | `trial_state_intervals`, `get_trial_state_values()` |
| ITI shading | `last_trial_end_time_s`, `next_trial_allowed_time_s` |

## Live Plot Functions

| Function | Role |
| --- | --- |
| `draw_plot(times, values)` | Redraws the live acquisition canvas with full and fast redraw paths. |
| `draw_iti_shading(...)` | Shades the current ITI interval. |
| `draw_trial_state_trace(...)` | Draws trial-state overlay. |
| `draw_trigger_trace(...)` | Draws reward/trigger pulse overlay. |
| `draw_sound_trace(...)` | Draws sound output as a lightweight epoch bar. |
| `draw_since_last_trial_timer(...)` | Shows elapsed time since last trial when idle. |
| `_draw_polyline(...)` | Helper for polyline traces. |

## Axis Model

The live plot uses:

- The left axis for the primary behavior signal.
- The right-side scale for overlay traces.

Relevant GUI fields:

- `Window s`
- `Ymin1`
- `Ymax1`
- `Ymin2`
- `Ymax2`

Overlay traces are rendered into the second y-axis range. This keeps digital-style event traces visually separate from the analog behavior signal.

## Redraw Model

`draw_plot()` uses two redraw levels:

- A full redraw clears the canvas and rebuilds axes, tick labels, legends, scale labels, and dynamic traces.
- A fast redraw deletes only canvas items tagged `plot_dynamic`, then redraws ITI shading, trial state, trigger pulses, sound epoch bars, timer text, and signal traces.

The static canvas elements are refreshed periodically and whenever plot geometry or trace labels change. This reduces canvas work during live acquisition while keeping the moving traces responsive.

## ITI Shading

`draw_iti_shading()` uses:

```text
last_trial_end_time_s -> next_trial_allowed_time_s
```

The shaded region marks ITI, not the active trial. It appears only after a trial has ended and while `next_trial_allowed_time_s` is later than `last_trial_end_time_s`.

## Results Window

Functions:

- `open_results_window()`
- `close_results_window()`
- `redraw_results_window()`
- `_draw_recent_trial_strip()`
- `_draw_recent_trial_column()`
- `_draw_condition_panel()`
- `_draw_crossing_duration_panel()`
- `_draw_rate_panel()`

The results window reads `trial_rows` and `dict_across_trials`. It should not mutate behavioral state.

## Event Recording For Plotting

Reward pulses are recorded by:

```python
record_trigger_pulse(pulse_s, start_s=None)
```

Sound outputs are recorded by:

```python
record_sound_output(signal, fs, sound_id=None, start_s=None)
```

Both keep full-session lists for export and windowed lists for plotting. The live plot intentionally draws sound as a green onset-to-offset rectangle instead of a waveform so sound timing remains visible without adding heavy canvas work.

## `.bin` Viewer

`open_bin()` lets the user choose a binary file and plot it using the acquisition rate from the neighboring `parameters.dat`. It is a viewer path, not part of live acquisition.

## Extension Notes

- Keep all canvas drawing in main-thread functions.
- If adding a new overlay, add both live state recording and rendering.
- If adding a new plot axis or trace class, update legend text and y-axis tick labels together.
- Avoid expensive per-sample work inside `draw_plot()`; it runs repeatedly during acquisition.



## Upcoming Go/No-Go trials

Session Overview includes a bottom-left preview of the next 10 planned Go/No-Go trials, with GO at y=0 (green), NoGo at y=1 (blue), and labels T, T+1, etc. T is the next trial to start; a currently active trial has already been consumed. Previewing does not advance the sequence or draw random numbers. Sequence wrap and Max trials are respected. Blank entries display B. The preview refreshes with sequence changes and trial advancement, is visible before the first result, and is hidden for other tasks or windows shorter than 400 pixels. SmartTask or manual regeneration can change the future plan.

## Moving performance

The performance panel uses the latest 25 completed trials of each type independently (all available trials until 25). GO HIT and NoGo CR are updated at each session trial; the other type carries its previous rate forward, so both curves remain continuous after their first observation. No value is drawn before a type has any data. Blank/uncompleted trials do not enter the denominators. DMTS uses match/non-match categories, with wrong-choice match FA counted against match performance. Rates and window counts are shown above the panel. Session totals and SmartTask calculations remain unchanged.

Moving performance curves begin only at the tenth completed trial of each type; before that the legend displays waiting (n/10). The maximum window remains 25 trials per type.

Recent outcomes retain the SmartTask phase recorded when each Go/No-Go trial started: pale orange columns mark NoGo emphasis and pale purple columns mark Balanced protected trials. Outcome marker colors are unchanged. Old trials without phase metadata remain unshaded.

Session Overview labels header rates as Session-wide and the curve panel as Moving rates: last 25 per type (min 10). Both the recent outcomes and moving-rate panel show recorded session trial-number ticks and dashed SmartTask phase boundaries, with orange for NoGo emphasis, purple for Balanced protected, and gray for return to ordinary trials. The recent strip fits all four outcome rows in compact windows. Upcoming preview is hidden below 480 pixels tall to preserve space for the rate panel. The launch button is named Session Overview.

Session Overview header now shows trial and outcome totals only; the session-wide percentage line has been removed. Moving-rate plots and SmartTask calculations are unchanged.
