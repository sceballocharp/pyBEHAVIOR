# DMTS LED patterns

The DMTS driver uses the simple driver's LED calibration and current/switch
buffers, with a separate sample/test protocol. pyBEHAVIOR chooses the pair during
ITI; PYNQ waits for two rising edges on the existing light-trigger input. No LED
trials file or `.npy` file is required. Classic simple and Braincodec sessions
retain their existing drivers.

## Install on PYNQ

1. Stop the old remote runner.
2. Copy the updated `braincodec/remote_runner.py` and new
   `braincodec/dmts_driver.py` into the same runner directory on PYNQ.
3. Ensure the existing `led_driver.driver` package and its `driver/driver.c`,
   calibration files and `base.bit` remain accessible as in working simple
   sessions. The new DMTS module reuses `ExpSimplePatterns` and
   `get_frames_counts`; it does not require replacing the C firmware.
4. Start the runner from the same working directory used for ordinary sessions:

   ```bash
   python remote_runner.py --host 0.0.0.0 --port 8000
   ```

The GUI's Upload Files button uploads YAML only in DMTS mode; it does not install
Python drivers. No PYNQ files have been deployed automatically by this change.

## Configure and run

1. Restart pyBEHAVIOR v7 to load the new code.
2. In Braincodec, select **DMTS patterns**, a stimulus YAML, **Wait for trigger**,
   and the correct extension-cable setting. Upload Files, then Remote Start.
3. In Behavior, select task **DMTS**, configure your existing match/non-match/
   blank weights, delay, response window, rewards and trigger type, then Start
   Live. Disable Simulation. The sample and test are selected randomly from the
   YAML library: match uses the same ID; non-match uses distinct IDs; blank uses
   0/0. Sample ID, Test ID, Sound IDs and Random DMTS sounds controls govern sound
   sessions only; in LED mode the YAML library supplies the IDs and no sound is
   played.
4. The program prepares one pair during the idle period before each trial. At
   the first trial, preparation happens before accepting the start event. Sample
   and test IDs are chosen once and retained until that trial starts.
5. The sample TTL presents the sample; the second TTL after the DMTS delay
   presents the test. The trial checks driver state before the test and verifies
   both presentations before allowing response scoring/reward.
6. Stop Live clears the pair and cancels any ongoing stimulus. Remote Stop shuts
   down the DMTS driver. A new Start Live creates a new session identity and
   resets sample/test state; it can reuse a still-running DMTS driver.

The selected local config and PYNQ library must match. A fingerprint compares
LED labels, irradiances, device ID, pulse settings and extension-cable setting.
Changing the local YAML requires uploading it and restarting the remote driver.
Unknown IDs, mismatched libraries and unexpected driver phases stop the Behavior
session with a recorded error. Manually stopping an unscored LED trial records
ABORTED rather than awarding a reward.

## YAML format

Use **Experiment mode: dmts_patterns** in `simple_pattern_generator.py`, or
select DMTS mode manually when using an existing multi-STIM YAML. `DMTS stimuli`
defines the library; `GO stimuli` is accepted as a compatibility fallback.
`STIM7` has numeric ID 7, independent of its position in the list.

```yaml
experiment_mode: "dmts_patterns"
mouse_id: "332"
device_id: "H2-190"
DMTS stimuli: ["STIM1", "STIM2"]
STIM1: "P1N8 P2N8 P3N8 P1N9 P2N9 P3N9 P1N10 P2N10 P3N10"
STIM1 irradiance (mW/mm2): 2
STIM2: "P8N1 P9N1 P10N1 P8N2 P9N2 P10N2 P8N3 P9N3 P10N3"
STIM2 irradiance (mW/mm2): 2
Pulse duration (ms): 25
Pulse frequency (Hz): 20
Number of pulses: 10
```

DMTS does not use GO, NOGO or `GO stimulus selection`. Those legacy fields may
remain in a shared config, or can be omitted for a DMTS-only config. Each STIM
needs its own irradiance, unless `GO irradiance (mW/mm2)` supplies a fallback.

## Timing and saved data

The LED pulse train follows the YAML. The DMTS timeline reuses the existing
SoundDuration_s field as the stimulus-slot duration. At session start the program
raises it, if necessary, to the nominal train duration plus a 50 ms margin.
For 10 pulses at 20 Hz this is 0.55 s. Buffer-update handshakes are included
within the requested pulse periods. DMTS ON and OFF times must each be at least
5 ms. Keep Light TTL ms positive and shorter than this slot; it is a trigger,
not the LED ON duration.

TTL generation and PYNQ edge detection/pulse generation use software timing.
The margin is not a hard timing guarantee. Validate sample/test order, train
duration and delay on the hardware before animal sessions. A completed
presentation is a driver confirmation, not an optical measurement.

Trials CSV and NWB `/intervals/trials` include `sample_light_id`, `test_light_id`,
`dmts_light_trial_id`, `dmts_light_fingerprint`, `dmts_light_confirmed` and
`dmts_light_error`. Actual sound-ID fields are zero in LED trials. The stimulus
library is also saved in parameters. The runner writes a downloadable JSONL log
with config, prepared pairs and presentation start/completion events. Early
fork-aborted trials can have a sample only and confirmation zero, consistent
with the existing DMTS fork rules.

Hardware-free checks:

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"
```
