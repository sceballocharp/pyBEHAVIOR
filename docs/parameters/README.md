# Parameters

This document describes how parameters are represented, imported, saved, and mirrored into trial/session metadata.

## Sources Of Parameters

Parameters can come from:

- GUI defaults in `_build_ui()` in `pyBEHAVIOR_v8.py`.
- Imported `.dat` files through `import_parameters_file()`.
- Generated protocol files from `protocol_generator.py`.
- Live GUI edits made before or during acquisition.

The compact user-facing parameter table is in `pyBEHAVIOR_v8_parameters.md`.

## Runtime Parameter Pipeline

| Function | Role |
| --- | --- |
| `read_parameters_file(path)` | Parses `key=value`, tab-separated, or whitespace-separated parameter files. |
| `apply_imported_parameters(params)` | Maps imported keys and aliases onto Tk variables. |
| `get_current_parameters()` | Collects the current GUI/runtime parameter state into a dictionary. |
| `write_parameters_dat()` | Writes the session-level `parameters.dat` file at session start. |
| `create_trial()` | Captures trial and parameter rows for `TrialLog.csv` and `Parameters.csv`. |
| `build_nwb_contract_parameters()` | Adds parameters to NWB/HDF5 export metadata. |

## Protocol Generator Pipeline

`protocol_generator.py` owns the `.dat` authoring GUI.

| Object or function | Role |
| --- | --- |
| `Parameter` | Dataclass describing one GUI field. |
| `PARAMETERS` | Full field registry for Classic Go/No-Go, Lever, DMTS, tAC, and shared session fields. |
| `BEHAVIOR_TABS` | Which sections appear for each protocol family. |
| `load_dat()` | Imports an existing `.dat` into generator variables, including behavior-specific aliases. |
| `validate()` | Checks numeric types and probability/range constraints. |
| `write_dat()` | Writes canonical runtime keys to disk, translating generator-specific keys. |

## Important Compatibility Rules

Some names are historical and should not be casually renamed:

- `OuputformatDropDown` is misspelled but preserved for compatibility.
- `RewardGoProb` is accepted as an alias for runtime `RewardGo`.
- `RewardProb` is used by DMTS but runtime currently maps it to the same GUI field as `RewardGo`.
- `HIT`, `HIT_s`, and `HITThreshold_s` are accepted as aliases for the HIT threshold field.
- `PunishInterval` is retained but `PunishNoGoFA` is the active false-alarm timeout.

## Adding A New Parameter

When adding a new saved parameter, update all relevant places:

1. Add the Tk variable and GUI entry in `_build_ui()`.
2. Add import mapping in `apply_imported_parameters()`.
3. Add the value to `get_current_parameters()`.
4. Add the key to `write_parameters_dat()` if it should appear in `parameters.dat`.
5. Add the value to `create_trial()` `parameter_row` if it should appear in `Parameters.csv`.
6. Add it to `build_nwb_contract_parameters()` if it should appear in NWB metadata.
7. Add it to `protocol_generator.py` `PARAMETERS` and `validate()` if protocol files should generate it.
8. Add or update example files under `protocols/`.
9. Update `pyBEHAVIOR_v8_parameters.md` and this documentation if behavior changes.

The recent `Pavlov` parameter follows this pattern.

## Parameter Blocks

`Parameters.csv` contains one row per accepted trial. The `Block` field groups consecutive trials with the same settings.

`get_parameter_block_label()` builds the block signature from the stable `get_current_parameters()` snapshot. Trial stimulus fields such as `LightCode`, `SoundId`, per-trial sample/test IDs, timestamps, trigger times, and the drawn per-trial `iti_s` do not create new blocks.

This means a newly drawn random ITI or a different Braincodec trial stimulus does not create a new block, but changing ITI settings such as `ITI_s`, `ITIrandMin_s`, or `ITIrandMax_s` does.

## Protocol Families

Runtime `TaskType` determines which behavior path is active:

- `ClassicGoNoGo`
- `Lever`
- `DMTS`
- `tAC`
- `tACPretraining`

The protocol generator uses behavior-specific UI keys such as `LeverRewardGo`, `DMTSRewardProb`, and `TACPreRewardGo`, then writes canonical runtime keys such as `RewardGo` and `RewardProb`.

## Pitfalls

- A parameter shown in the GUI but not added to `get_current_parameters()` will not be saved.
- A parameter saved in `parameters.dat` but not added to `apply_imported_parameters()` will not reload.
- A parameter used by analysis should be present in `Parameters.csv` and NWB metadata, not only in `parameters.dat`.
- Protocol generator validation must match runtime expectations. For probabilities, validate `0 <= value <= 1`.



`LeverReqRelBonus` is the canonical lever release/bonus parameter. The runtime and protocol generator still accept `LeverRequireRelease` as an import alias; when both are present, `LeverReqRelBonus` takes precedence. New exports use `LeverReqRelBonus`. The internal variable and trial-log field `lever_require_release` are unchanged.

`LeverReqRelWindow` defaults to `0`, including when absent on import. It is saved in session parameters, Parameters.csv, and NWB parameter metadata, and mirrored as `lever_req_rel_window` in TrialLog.csv. If both release flags are enabled on import, window-only wins with a message.

## DMTS sound/light selection in v8

In **Closed Loop Sequence**, **Sound / Light probabilities** takes two space-separated probabilities, in that order. Each must be finite and between 0 and 1, and their sum must be 1 (decimal tolerance 1e-9). Default: `1 0`. Use `0.5 0.5` for equal probability or `0 1` for lights only. Invalid inputs block sequence regeneration and session startup.

The existing Match / Non-match / Blank weights choose the trial type first. Nonblank trials then select one modality for both sample and test. Blanks present neither modality. Sound trials do not prepare LED stimuli or send LED triggers; sample/test light IDs are zero. Light trials suppress audio and save sound, sample sound, and test sound IDs as zero. Shared response and reward rules are unchanged.

A positive light probability requires DMTS patterns configured in Braincodec and the remote driver running. A positive sound probability requires the usual audio setup. The field is saved/imported as `DMTSModalityProbabilities`. Modality is drawn per trial; the existing sequence seed controls trial types.

**NonMatch Only Sounds** (default unchecked) overrides modality selection for non-match trials: both sample and test are sounds, regardless of Sound / Light probabilities. Match and blank selection is unchanged, as are the overall trial-type weights. The option is saved/imported as `DMTSNonMatchOnlySounds`. With this option enabled, an audio file is required even when Sound / Light probabilities are `0 1`.

During acquisition, incomplete or invalid edits to Sound / Light probabilities keep the last valid pair active. A new valid pair is used at the next trial preparation; a trial already prepared keeps its selected modality. Session startup still requires valid probabilities.

**NonMatch FA noise (110)** enables one white-noise cue when a DMTS non-match trial is scored FA at the reward decision time. It uses sound ID 110 in the selected sound bank (select `Sounds/DMTS/AllSounds_from_wav.mat`) at 1.25 times the current Sound level (25% higher waveform amplitude). Sample/test sound levels are unchanged. Default: off. Existing timeout punishment remains active. It applies to sound and light non-match trials; light sample/test sound IDs remain zero and the extra cue is logged separately as `punishment_sound_id` and in the recorded sound outputs. The sound bank is required even for light-only sessions when this option is on. Protocol key: `DMTSNonMatchFANoise`.
