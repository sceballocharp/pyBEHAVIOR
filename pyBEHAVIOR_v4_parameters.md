# pyBEHAVIOR v4 Parameters

This document describes the `parameters.dat` fields used by the current protocol workflow.

`protocol_generator.py` can generate three protocol families:

- `ClassicGoNoGo`
- `Lever`
- `DMTS`

`pyBEHAVIOR_v4.py` currently imports and runs the Classic Go/No-Go and Lever fields. DMTS fields are documented here because the generator now creates them, but runtime DMTS behavior still needs to be implemented in `pyBEHAVIOR_v4.py`.

## Common Parameters

These are shared by every protocol tab.

| Parameter | GUI label | Meaning |
| --- | --- | --- |
| `UserName` | User | User/session owner name used in the output path. |
| `MouseId` | Mouse ID | Mouse identifier, saved under `M<MouseId>`. |
| `ProjectName` | Project | Project label stored with the session metadata. |
| `NICard_filename` | NI script | Path to the NI setup script. |
| `Sound_filename` | Sound file | Path to the sound `.mat` or `.wav` file. |
| `frec` | Acquisition rate Hz | Acquisition sampling rate in Hz. |
| `bin` | Callback/bin s | Acquisition callback/read chunk duration in seconds. |
| `TriggerTypeDropDown` | Trigger | Response signal source: `IRFork`, `Lick`, or `None`. |
| `OuputformatDropDown` | Output format | Output format selector. Note the historical misspelling is preserved for compatibility. |

## Classic Go/No-Go

Saved with:

```text
TaskType=ClassicGoNoGo
```

### Task

| Parameter | GUI label | Meaning |
| --- | --- | --- |
| `TaskType` | Task type | Protocol identifier, `ClassicGoNoGo`. |
| `MaxTrials` | Max trials | Maximum number of accepted trials. `0` means no limit. |
| `GoWeight` | Go weight | Relative probability weight for GO trials. |
| `NoGoWeight` | No-go weight | Relative probability weight for no-go trials. |
| `GoSoundId` | Go sound ID | Sound ID used for GO trials. |
| `NoGoSoundId` | No-go sound ID | Sound ID used for no-go trials. |
| `SoundLevel` | Sound level | Multiplicative gain for sound playback. |
| `RandomSeed` | Random seed | Seed for reproducible sound/trial sequence generation. |

### Timing

| Parameter | GUI label | Meaning |
| --- | --- | --- |
| `ITI_s` | ITI | Base inter-trial interval. |
| `ITIrandMin_s` | rand min | Minimum random ITI addition. |
| `ITIrandMax_s` | rand max | Maximum random ITI addition. |
| `Sounddelay_s` | Sound delay s | Delay from trial start to sound onset. |
| `SoundDuration_s` | Sound duration s | Duration of the sound stimulus. |
| `TrialDuration_s` | Trial duration s | Computed as sound delay + sound duration + reward delay + response window. |
| `ResponseWindow_s` | Response window s | Window during which behavior is scored. |
| `RewardDelay_s` | Reward delay s | Delay before the response/reward phase. |

### Outcome

| Parameter | GUI label | Used when | Meaning |
| --- | --- | --- | --- |
| `Rewardduration_ms` | Reward duration ms | All response modes | Water valve/trigger pulse duration in ms. |
| `RewardGoProb` | RewardGo Prob | GO HITs | Probability that a GO HIT is rewarded, from `0` to `1`. |
| `PunishNoGoFA` | Timeout false alarms | no-go FA | Timeout duration after a no-go false alarm, in seconds. |
| `HITThreshold_percent` | HIT threshold % | `TriggerTypeDropDown=IRFork` | Percentage of `ResponseWindow_s` that the IR beam signal must remain above threshold to count as HIT/FA. |
| `Minlickcount` | Min lick count | `TriggerTypeDropDown=Lick` | Number of upward crossings over `Lickthreshold` required to count as HIT/FA. |
| `Lickthreshold` | Signal threshold V | `TriggerTypeDropDown=Lick` | Voltage threshold used to detect lick crossings. |

### Response Mode Distinction

For IR beam scoring:

```text
TriggerTypeDropDown=IRFork
HITThreshold_percent=<0-100>
```

`HITThreshold_percent` is converted to seconds:

```text
required_time_above_threshold = ResponseWindow_s * HITThreshold_percent / 100
```

For lick-port scoring:

```text
TriggerTypeDropDown=Lick
Lickthreshold=<volts>
Minlickcount=<count>
```

A response is scored when the signal crosses above `Lickthreshold` at least `Minlickcount` times during the response window.

## Lever

Saved with:

```text
TaskType=Lever
```

| Parameter | GUI label | Meaning |
| --- | --- | --- |
| `TaskType` | Task type | Protocol identifier, `Lever`. |
| `LeverThreshold` | Lever threshold V | Voltage threshold crossed by the lever signal to start a lever response. |
| `GoSoundId` | GO sound ID | Sound ID triggered when the lever threshold is crossed. |
| `SoundLevel` | Sound level | Multiplicative gain for sound playback. |
| `LeverHoldTime_s` | Lever hold time s | Time the lever signal must remain above threshold before reward logic is triggered. |
| `Rewardduration_ms` | Reward duration ms | Water valve/trigger pulse duration in ms. |
| `RewardGo` | RewardGo Prob | Probability that a successful lever response is rewarded, from `0` to `1`. |

## DMTS

Saved with:

```text
TaskType=DMTS
```

DMTS means delayed match to sample. The protocol generator can create these parameters and preview the timing. Runtime handling still needs to be added to `pyBEHAVIOR_v4.py`.

### Task

| Parameter | GUI label | Meaning |
| --- | --- | --- |
| `TaskType` | Task type | Protocol identifier, `DMTS`. |
| `MaxTrials` | Max trials | Maximum number of accepted trials. |
| `SampleSoundId` | Sample sound ID | First/sample sound stimulus. |
| `TestSoundId` | Test sound ID | Second/test sound stimulus. |
| `SoundLevel` | Sound level | Multiplicative gain for sound playback. |
| `RandomSeed` | Random seed | Seed for reproducible trial sequence generation. |

### Timing

| Parameter | GUI label | Meaning |
| --- | --- | --- |
| `ITI_s` | ITI | Base inter-trial interval before the sample sound. |
| `ITIrandMin_s` | ITI min | Minimum random ITI addition. |
| `ITIrandMax_s` | ITI max | Maximum random ITI addition. |
| `SoundDuration_s` | Sound duration s | Duration of each sound stimulus. |
| `Delay_s` | Delay s | Delay between the end of sample sound and start of test sound. |
| `ResponseWindow_s` | Response window s | Window after the test sound during which behavior is scored. |
| `RewardDelay_s` | Reward delay s | Delay from response-window end to reward delivery. |

### Outcome

| Parameter | GUI label | Meaning |
| --- | --- | --- |
| `Rewardduration_ms` | Reward duration ms | Water valve/trigger pulse duration in ms. |
| `RewardProb` | Reward prob | Probability that a correct DMTS response is rewarded, from `0` to `1`. |
| `HITThreshold_percent` | Threshold of RW for HIT % | Percentage of the response window required for HIT classification. |

## Import Compatibility

`pyBEHAVIOR_v4.py` still accepts several legacy aliases:

| Legacy key | Current meaning |
| --- | --- |
| `OutputformatDropDown` | Alias for `OuputformatDropDown`. |
| `HIT`, `HIT_s`, `HITThreshold_s` | Legacy names for the HIT threshold field. |
| `RewardGo` | Classic/Lever reward probability; `RewardGoProb` is also accepted for Go/No-Go import. |
| `PunishInterval` | Legacy punishment field; prefer `PunishNoGoFA`. |

## Runtime Status

| Protocol | Generated by `protocol_generator.py` | Imported by `pyBEHAVIOR_v4.py` | Runtime behavior in `pyBEHAVIOR_v4.py` |
| --- | --- | --- | --- |
| Classic Go/No-Go | Yes | Yes | Implemented. |
| Lever | Yes | Yes | Implemented. |
| DMTS | Yes | Not yet complete | Not yet implemented. |
