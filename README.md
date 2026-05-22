# pyBASIL_v2

`pyBASIL_v2` is a Python/Tkinter acquisition interface for BASIL behavioral experiments. It is designed to run closed-loop mouse behavior sessions with NI-DAQ acquisition, IR-fork or lick-triggered trial detection, calibrated sound playback, reward pulses, live plotting, trial logging, and NWB export.

The app is a Python counterpart to the local MATLAB BASIL acquisition tools, while keeping the session workflow visible and editable from a single GUI.

## What It Does

- Runs live analog acquisition from a National Instruments device.
- Monitors behavioral input channels such as IR-fork, lick, sound copy, and sound TTL.
- Detects threshold crossings and starts trials in real time.
- Supports classic Go/No-go and lever-style tasks.
- Plays sounds from MATLAB `.mat` sound banks.
- Sends reward or trigger pulses through NI digital output.
- Records raw IR-fork data to `IRFork.bin`.
- Logs session parameters to `parameters.dat` and `Parameters.csv`.
- Logs trial outcomes to `TrialLog.csv`.
- Saves sessions as NWB files when `pynwb` is installed.
- Includes simulation mode for testing without hardware.
- Provides a results figure window for quick online trial summaries.

## Main Files

| File | Purpose |
| --- | --- |
| `pyBASIL_v2.py` | Main acquisition GUI and runtime logic. |
| `protocol_generator.py` | GUI tool for creating parameter `.dat` files. |
| `requirements.txt` | Python dependencies. |
| `run_pyBASIL_v2.bat` | Windows launcher for the main app using the local `.venv`. |
| `run_protocol_generator.bat` | Windows launcher for the protocol generator. |
| `setup_python_env.bat` | Creates the local Python virtual environment and installs dependencies. |
| `setup_valves_IRFork.m` | Reference NI hardware setup used by the Python app defaults. |
| `BASIL_acquisition_flow.md` | Detailed acquisition-flow notes and signal diagrams. |

## Quick Start

On a Windows acquisition computer:

```bat
setup_python_env.bat
run_pyBASIL_v2.bat
```

Or launch directly:

```bat
.venv\Scripts\python.exe pyBASIL_v2.py
```

To create or edit a protocol file:

```bat
run_protocol_generator.bat
```

## Dependencies

The core dependencies are listed in `requirements.txt`:

- `numpy`
- `scipy`
- `nidaqmx`
- `sounddevice`
- `pynwb`

The app can still open in a reduced mode if some optional packages are missing. For example, missing `nidaqmx` disables hardware acquisition/output, missing `scipy` disables MATLAB sound loading, and missing `pynwb` disables NWB export.

## Typical Session Workflow

1. Launch `pyBASIL_v2`.
2. Set the user, mouse, project, save root, NI device, channels, and acquisition rate.
3. Select or import a protocol `.dat` file if needed.
4. Choose the NI setup script and sound `.mat` file.
5. Configure task parameters:
   - Go/No-go sound IDs, weights, ITI, response window, reward probability, and false-alarm timeout.
   - Lever threshold, hold time, sound ID, and reward settings.
6. Use **Generate sequence** to prepare the closed-loop sound sequence.
7. Press **Start Live** to begin acquisition.
8. Monitor the live trace, event overlays, trial state, logs, and results window.
9. Press **Stop** to end acquisition and close NI/file handles.
10. Use **Save NWB** if the session should be exported to NWB.

## Data Output

Each session is saved under the configured save root using the session metadata and timestamp. A typical session folder contains:

| Output | Description |
| --- | --- |
| `IRFork.bin` | Raw binary IR-fork signal samples written as doubles. |
| `parameters.dat` | Human-readable session and task parameters. |
| `Parameters.csv` | Parameter blocks for analysis and provenance. |
| `TrialLog.csv` | Trial-by-trial outcomes, timing, sound IDs, hits, misses, false alarms, and rewards. |
| `*_Data.nwb` | NWB export containing acquisition and event time series, when enabled. |

## Hardware Defaults

The default NI layout follows `setup_valves_IRFork.m`:

| Signal | Default channel/line | Direction | Role |
| --- | --- | --- | --- |
| IRFork | `Dev1/ai6` | Input | Beam-crossing or lever signal. |
| SoundCopy | `Dev1/ai5` | Input | Recorded sound waveform copy. |
| TTLtrigsounds | `Dev1/ai1` | Input | Sound TTL/input trace. |
| TTLReward | `Dev1/port2/line6` | Output | Reward or trigger pulse. |
| Speaker | `Dev1/ao0` | Output | NI analog sound playback. |

These defaults can be edited in the GUI before starting a session.

## Simulation Mode

Simulation mode lets the app generate synthetic acquisition data without NI hardware. This is useful for checking the GUI, trigger logic, trial logging, plotting, and NWB export paths before running on the rig.

## Protocol Generation

`protocol_generator.py` creates compatible `.dat` parameter files for:

- Classic Go/No-go tasks.
- Lever tasks.
- Shared session settings such as user, mouse ID, project, sound file, NI setup, acquisition rate, and output format.

Generated protocols can be imported into `pyBASIL_v2` with **Import parameters**.

## Notes

- Use `BASIL_acquisition_flow.md` for a more detailed view of the acquisition loop and signal routing.
- Keep large raw data folders out of version control unless they are deliberate examples.
- Check hardware channel names before running on a new rig.
- If the app opens but hardware controls do not work, verify the NI-DAQmx driver, the `nidaqmx` Python package, and the selected device name.
