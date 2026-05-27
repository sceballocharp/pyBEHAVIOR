# pyBEHAVIOR_v3 parameters

This document describes the parameters loaded from `parameters.dat` by `pyBEHAVIOR_v3.py`, where they map in the GUI/code, when they are used, and their meaning.

## Main Code Sections

### Import From `parameters.dat`

```python
def apply_imported_parameters(self, params):
    mapping = {
        "UserName": self.user_name,
        "MouseId": self.mouse_id,
        "ProjectName": self.project_name,
        "NICard_filename": self.ni_script,
        "Sound_filename": self.sound_file,
        "frec": self.rate_hz,
        "bin": self.callback_s,
        "TriggerTypeDropDown": self.trigger_type,
        "OuputformatDropDown": self.output_format,
        "OutputformatDropDown": self.output_format,
        "TaskType": self.task_type,
        "MaxTrials": self.max_trials,
        "SoundLevel": self.sound_level,
        "RandomSeed": self.random_seed,
        "ITI_s": self.iti_s,
        "ITIrandMin_s": self.iti_rand_min_s,
        "ITIrandMax_s": self.iti_rand_max_s,
        "Sounddelay_s": self.sound_delay_s,
        "SoundDuration_s": self.sound_duration_s,
        "TrialDuration_s": self.trial_duration_s,
        "ResponseWindow_s": self.response_window_s,
        "RewardDelay_s": self.reward_delay_s,
        "Rewardduration_ms": self.pulse_ms,
        "HIT": self.hit_threshold_s,
        "HITThreshold_percent": self.hit_threshold_s,
        "HITThreshold_s": self.hit_threshold_s,
        "HIT_s": self.hit_threshold_s,
        "PunishInterval": self.punish_interval,
        "RewardGo": self.reward_go,
        "RewardGoProb": self.reward_go,
        "PunishNoGoFA": self.punish_no_go_fa,
        "Minlickcount": self.min_lick_count,
        "Lickthreshold": self.lick_threshold,
        "LeverThreshold": self.threshold_v,
        "LeverHoldTime_s": self.lever_hold_time_s,
    }
```

`GoSoundId`, `NoGoSoundId`, `GoWeight`, and `NoGoWeight` are handled just after this mapping because they update the closed-loop sequence fields together.

### Save To Session `parameters.dat`

```python
def write_parameters_dat(self):
    f.write(f"UserName={self.user_name.get()}\n")
    f.write(f"MouseId={self.mouse_id.get()}\n")
    f.write(f"ProjectName={self.project_name.get()}\n")
    f.write(f"NICard_filename={self.ni_script.get().replace(os.sep, '/')}\n")
    f.write(f"Sound_filename={self.sound_file.get().replace(os.sep, '/')}\n")
    f.write(f"SimulationMode={int(self.simulation_mode.get())}\n")
    f.write(f"frec={self.rate_hz.get()}\n")
    f.write(f"bin={self.callback_s.get()}\n")
    f.write(f"TriggerTypeDropDown={self.trigger_type.get()}\n")
    f.write(f"OuputformatDropDown={self.output_format.get()}\n")
    f.write(f"TaskType={self.task_type.get()}\n")
    f.write(f"GoWeight=...\n")
    f.write(f"NoGoWeight=...\n")
    f.write(f"GoSoundId=...\n")
    f.write(f"NoGoSoundId=...\n")
    f.write(f"SoundLevel={self.sound_level.get()}\n")
    f.write(f"RandomSeed={self.random_seed.get()}\n")
    f.write(f"ITI_s={self.iti_s.get()}\n")
    f.write(f"ITIrandMin_s={self.iti_rand_min_s.get()}\n")
    f.write(f"ITIrandMax_s={self.iti_rand_max_s.get()}\n")
    f.write(f"Sounddelay_s={self.sound_delay_s.get()}\n")
    f.write(f"SoundDuration_s={self.sound_duration_s.get()}\n")
    f.write(f"TrialDuration_s={self.trial_duration_s.get()}\n")
    f.write(f"ResponseWindow_s={self.response_window_s.get()}\n")
    f.write(f"RewardDelay_s={self.reward_delay_s.get()}\n")
    f.write(f"Rewardduration_ms={self.pulse_ms.get()}\n")
    f.write(f"HIT={self.hit_threshold_s.get()}\n")
    f.write(f"HITThreshold_percent={self.hit_threshold_s.get()}\n")
    f.write(f"PunishInterval={self.punish_interval.get()}\n")
    f.write(f"RewardGo={self.reward_go.get()}\n")
    f.write(f"PunishNoGoFA={self.punish_no_go_fa.get()}\n")
    f.write(f"Minlickcount={self.min_lick_count.get()}\n")
    f.write(f"Lickthreshold={self.lick_threshold.get()}\n")
    f.write(f"LeverThreshold={self.threshold_v.get()}\n")
    f.write(f"LeverHoldTime_s={self.lever_hold_time_s.get()}\n")
    f.write(f"MaxTrials={self.max_trials.get()}\n")
```

### Main Behavior Use

```python
def check_trigger(self, times, ir_values):
    threshold = self.get_current_trigger_threshold()
    if self.is_lever_task():
        self.check_lever_trigger_sample(...)
```

```python
def get_current_trigger_threshold(self):
    if self.is_lick_trigger():
        return self.parse_float(self.lick_threshold, self.parse_float(self.threshold_v, 1))
    return self.parse_float(self.threshold_v, 1)
```

```python
def draw_trial_iti_s(self):
    return ITI_s + random.uniform(ITIrandMin_s, ITIrandMax_s)
```

```python
def generate_sequence(self):
    values = sequence_values      # GoSoundId / NoGoSoundId
    weights = sequence_weights    # GoWeight / NoGoWeight
    seed = RandomSeed
```

## Parameter Table

| Parameter | GUI field | Code section | Used when | Meaning |
| --- | --- | --- | --- | --- |
| `UserName` | Session `User` | `apply_imported_parameters`, `prepare_session_folder`, `write_parameters_dat` | Session setup and file saving | User folder/name used in the output path. |
| `MouseId` | Session `Mouse` | `prepare_session_folder`, `write_parameters_dat` | Session setup and file saving | Mouse identifier, saved under `M<MouseId>`. |
| `ProjectName` | Session `Project` | `write_parameters_dat`, NWB session description | Saving and NWB export | Project label stored with the session metadata. |
| `NICard_filename` | Control `NI script` | `apply_imported_parameters`, `write_parameters_dat` | Import/save only in Python | Path to the NI setup script; retained for compatibility. |
| `Sound_filename` | Control `Sound .mat` | `load_sound_file`, `get_sound_by_id` | Sound playback | Path to the MATLAB sound file containing `Sound`. |
| `SimulationMode` | Control `Simulation` | `write_parameters_dat`, `start_live` | Saved sessions; GUI checkbox controls runtime | Whether acquisition uses simulated input instead of NI hardware. |
| `frec` | Acquisition `Rate Hz` | `acquisition_loop`, NI timing, `.bin`/NWB reading | Acquisition and export | Sampling rate in Hz. |
| `bin` | Acquisition `Callback s` | `acquisition_loop` | Acquisition | Chunk duration in seconds for each acquisition loop read. |
| `TriggerTypeDropDown` | Trigger `Trigger` | `check_trigger`, `is_lick_trigger`, `get_current_trigger_threshold` | Behavior scoring | Chooses whether trigger scoring is IRFork-style or lick-count-style. |
| `OuputformatDropDown` | Session `Output` | `stop_live`, `save_nwb` | End of session | Output format selector; `NWB` triggers NWB export on stop. |
| `OutputformatDropDown` | Session `Output` | Import alias only | Import compatibility | Corrected spelling alias for `OuputformatDropDown`. |
| `TaskType` | Trial Structure `Task type` | `is_lever_task`, GUI visibility, behavior branch | All behavior modes | Selects Classic Go/No-Go versus Lever task behavior. |
| `MaxTrials` | Closed Loop Sequence `Max trials` | `check_trigger`, `check_lever_trigger_sample` | During acquisition | Stops accepting new trials after this count; `0` means no limit. |
| `GoWeight` | Sequence `Weights`, first value | `generate_sequence` | Go/No-Go sequence generation | Relative probability weight for the GO sound ID. |
| `NoGoWeight` | Sequence `Weights`, second value | `generate_sequence` | Go/No-Go sequence generation | Relative probability weight for the noGo sound ID. |
| `GoSoundId` | Sequence `Values`, first value; Trigger `Sound id` | `classify_trial_sound`, `consume_next_sound_id`, Lever sound start | Sound playback and trial classification | Sound ID used for GO trials and the starting sound ID for Lever sound ladders. |
| `NoGoSoundId` | Sequence `Values`, second value | `classify_trial_sound`, `generate_sequence` | Go/No-Go sequence generation | Sound ID classified as noGo. |
| `SoundLevel` | Trigger `Level` | `get_sound_by_id` | Sound playback | Multiplicative gain applied to the selected sound waveform. |
| `RandomSeed` | Closed Loop Sequence `Seed` | `generate_sequence` | Sequence generation | Seed for reproducible random GO/noGo sound order. |
| `ITI_s` | Trial Structure `ITI s` | `draw_trial_iti_s`, `start_active_trial`, `start_active_lever_trial` | Trial spacing | Base inter-trial interval added after each trial start. |
| `ITIrandMin_s` | Trial Structure `ITI min` | `draw_trial_iti_s` | Trial spacing | Minimum random ITI addition. |
| `ITIrandMax_s` | Trial Structure `ITI max` | `draw_trial_iti_s` | Trial spacing | Maximum random ITI addition. |
| `Sounddelay_s` | Trial Structure `Sound delay s` when visible | `update_trial_duration`, trial parameter log | Currently display/log timing only | Delay parameter retained for protocol compatibility and trial-duration calculation. |
| `SoundDuration_s` | Hidden in GUI | `update_trial_duration`, trial parameter log | Import/save/log compatibility | Sound duration parameter retained even though it is not currently displayed. |
| `TrialDuration_s` | Trial Structure `Trial s`, readonly | `update_trial_duration`, trial parameter log | Display/log | Calculated total from sound delay, sound duration, response window, and reward delay. |
| `ResponseWindow_s` | Trial Structure `Response s` | `start_active_trial`, `get_hit_threshold_s`, `finish_active_trial` | Go/No-Go trials | Time window during which responses are scored. |
| `RewardDelay_s` | Trial Structure `Reward delay s` | `update_trial_duration`, trial parameter log | Display/log currently | Reward delay parameter is logged and contributes to displayed trial duration. |
| `Rewardduration_ms` | Trigger `Pulse ms` | `send_output_pulse`, trial parameter log | Reward/output pulse | Duration of the reward/trigger digital pulse. |
| `HIT`, `HIT_s`, `HITThreshold_s`, `HITThreshold_percent` | Trial Structure `Resp. hold %` when visible | `get_hit_threshold_s`, `evaluate_active_trial`, `finish_active_trial` | Non-lick Go/No-Go scoring | Required percentage of the response window spent above trigger threshold. |
| `RewardGo` | Trial Structure `RewardGo` | `maybe_send_go_reward` | GO HITs and Lever HITs | Reward probability after a successful GO or Lever response. |
| `RewardGoProb` | Trial Structure `RewardGo` | Import alias only | Import compatibility | Alternate name for `RewardGo`. |
| `PunishNoGoFA` | Trial Structure `Punish FA` | `get_punish_no_go_fa_s`, `apply_trial_timeout` | noGo false alarms | Extra timeout after a noGo false alarm, capped at 10 seconds. |
| `PunishInterval` | Hidden from GUI | Import/save/trial parameter log only | Compatibility only | Legacy punishment interval field; not currently active in behavior logic. |
| `Minlickcount` | Trial Structure `Min licks` when visible | `get_min_lick_count`, lick scoring | Lick-trigger Go/No-Go | Number of upward lick crossings required for HIT or FA. |
| `Lickthreshold` | Trial Structure `Lick thresh` when Trigger is Lick | `get_current_trigger_threshold`, `check_trigger` | Lick-trigger Go/No-Go | Voltage threshold for counting lick upward crossings. |
| `LeverThreshold` | Trigger `Threshold V` | `get_current_trigger_threshold`, `check_lever_trigger_sample` | Lever task | Lever voltage threshold for starting and maintaining a lever trial. |
| `LeverHoldTime_s` | Trial Structure `Lever hold s` in Lever mode | `get_lever_hold_time_s`, `evaluate_active_lever_trial` | Lever task | Continuous hold duration required to mark the Lever trial as HIT and trigger reward logic. |

## Behavior-Specific Notes

### Classic Go/No-Go With IRFork

Uses `TriggerTypeDropDown=IRFork` and `TaskType` not equal to `Lever`.

Scoring uses:

```python
hit_threshold_s = self.get_hit_threshold_s()
total_s = self.get_active_crossing_total(sample_time_s)
```

A GO trial becomes `HIT` when cumulative time above threshold reaches `Resp. hold %` converted to seconds. A noGo trial becomes `FA` when the same threshold is reached.

### Classic Go/No-Go With Lick Trigger

Uses `TriggerTypeDropDown=Lick` and `TaskType` not equal to `Lever`.

Scoring uses:

```python
if crossed_up:
    self.add_active_lick()
...
if self.active_lick_count >= min_lick_count:
```

A GO trial becomes `HIT` when lick upward crossings above `Lickthreshold` reach `Minlickcount`. A noGo trial becomes `FA` with the same count threshold.

### Lever Task

Uses `TaskType=Lever`.

Scoring uses:

```python
hold_s = sample_time_s - self.active_high_start_s
if hold_s >= self.get_lever_hold_time_s():
    row["ResultType"] = "HIT"
    self.maybe_send_go_reward(row, hold_s)
```

The lever trial starts when the signal crosses `LeverThreshold`, sound playback follows the ladder from `GoSoundId`, and reward logic is triggered once continuous hold time reaches `LeverHoldTime_s`.
