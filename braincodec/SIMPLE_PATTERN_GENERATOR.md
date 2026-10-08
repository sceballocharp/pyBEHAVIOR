# Multiple GO patches

Double-click `run_simple_pattern_generator.bat` in the repository root, or run
`python braincodec/simple_pattern_generator.py`. The generator uses only Python's
standard library, including Tkinter.

Choose the lowest P and N coordinates of each 3x3 patch (1 through 8), then click
**Add GO patch**. The first patch is P1–P3 / N8–N10. Click the logical grid or use
the coordinate controls to choose another patch. All GO patches share the entered
irradiance. Configure the fixed NO-GO patch and pulse settings, then save the YAML.
The grid shows logical P/N coordinates; physical orientation depends on the
array and extension cables.

The file contains `STIM1`, `STIM2`, etc. and a `GO stimuli` list. With the default
`GO stimulus selection: random`, each GO trial (light code 1) independently picks
one listed stimulus with equal probability. Consecutive repeats are possible;
the counts per stimulus are not guaranteed to match. Choose `cycle` to present
them in list order instead, restarting at STIM1 for each new run. NO-GO (2) and
blank (0) trials do not advance the cycle. Stimulus names and their
LEDs/irradiances are recorded in the PYNQ log; the NI trial code remains 1 for all
GO variants. The pyBEHAVIOR preview displays the first GO patch only.

Before running, update the actual PYNQ `led_driver/driver.py` with the updated
local `braincodec/driver.pyw` code. Restart the remote runner so it imports the
new driver. Config upload does not update the driver. An older driver will ignore
the named variants and present only the first patch through the legacy `GO` key.
Existing single-GO YAML files remain supported by the updated driver.

For light-based DMTS, choose `dmts_patterns` as the generator's experiment mode.
The named STIM patterns become a sample/test library rather than fixed GO types.
See [DMTS_LED_SETUP.md](DMTS_LED_SETUP.md) for PYNQ installation and session setup.

Load the saved YAML in the Braincodec tab using **Simple patterns**, generate
and upload the trial sequence and config, then use Remote Start and Behavior
Start Live as usual. Test the new patterns on the hardware before a session.
