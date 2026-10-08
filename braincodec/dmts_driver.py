"""DMTS pair protocol and PYNQ LED driver; protocol imports need no PYNQ hardware."""

import asyncio
import hashlib
import json
import math
import re
import threading
from datetime import datetime
from pathlib import Path


class DMTSLibrary:
    def __init__(self, config, ext_cables_used=True):
        names = config.get("DMTS stimuli", config.get("GO stimuli", []))
        if not isinstance(names, list) or not names:
            raise ValueError("DMTS stimuli (or GO stimuli) must list STIM names")
        self.patterns = {}
        valid = {f"P{p}N{n}" for p in range(1, 11) for n in range(1, 11)}
        for name in names:
            match = re.fullmatch(r"STIM([1-9][0-9]*)", str(name))
            if not match or int(match[1]) in self.patterns:
                raise ValueError("Stimulus names must be unique STIM1, STIM2, etc.")
            labels = str(config.get(name, "")).split()
            if not labels or any(label not in valid for label in labels):
                raise ValueError(f"Invalid or missing LEDs for {name}")
            irradiance = float(config.get(f"{name} irradiance (mW/mm2)",
                                          config.get("GO irradiance (mW/mm2)", 0)))
            if not math.isfinite(irradiance) or irradiance <= 0:
                raise ValueError(f"Invalid irradiance for {name}")
            self.patterns[int(match[1])] = {"name": name, "labels": labels, "irradiance": irradiance}
        self.ids = list(self.patterns)
        self.device_id = str(config["device_id"])
        self.on_s = float(config["Pulse duration (ms)"]) / 1000
        self.frequency = float(config["Pulse frequency (Hz)"])
        pulse_value = float(config["Number of pulses"])
        if not math.isfinite(pulse_value) or not pulse_value.is_integer() or pulse_value < 1:
            raise ValueError("Number of pulses must be a positive integer")
        self.pulses = int(pulse_value)
        if not all(math.isfinite(v) and v > 0 for v in (self.on_s, self.frequency)):
            raise ValueError("Invalid pulse duration or frequency")
        self.off_s = 1 / self.frequency - self.on_s
        if self.off_s < -1e-12:
            raise ValueError("Pulse duration exceeds pulse period")
        self.off_s = max(0, self.off_s)
        if self.on_s < 0.005 or self.off_s < 0.005:
            raise ValueError('DMTS pulse ON and OFF durations must each be at least 5 ms')
        self.duration_s = self.pulses / self.frequency
        canonical = {"patterns": self.patterns, "device": self.device_id,
                     "on": self.on_s, "frequency": self.frequency, "pulses": self.pulses,
                     "extension_cables": bool(ext_cables_used)}
        self.fingerprint = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()


class DMTSPairState:
    """Serialize network preparation and trigger consumption; no hardware dependencies."""
    def __init__(self, library):
        self.library = library
        self.lock = threading.Lock()
        self.generation = 0
        self.pair = None
        self.phase = "idle"
        self.presentations = []
        self.used_trial_ids = set()

    def snapshot(self):
        with self.lock:
            return {"phase": self.phase, "pair": dict(self.pair) if self.pair else None,
                    "presentations": list(self.presentations),
                    "stimulus_ids": self.library.ids,
                    "duration_s": self.library.duration_s,
                    "fingerprint": self.library.fingerprint}

    def prepare(self, trial_id, sample_id, test_id, fingerprint):
        with self.lock:
            if self.phase != "idle":
                raise ValueError("Previous pair is pending; reset before preparing another")
            if fingerprint != self.library.fingerprint:
                raise ValueError("PC and PYNQ stimulus libraries do not match")
            if not isinstance(trial_id, str) or not trial_id or trial_id in self.used_trial_ids:
                raise ValueError("Trial ID is empty or already used")
            for value in (sample_id, test_id):
                if type(value) is not int or (value != 0 and value not in self.library.patterns):
                    raise ValueError(f"Unknown stimulus ID: {value}")
            if (sample_id == 0) != (test_id == 0):
                raise ValueError("Blank pairs require both IDs to be zero")
            self.generation += 1
            self.used_trial_ids.add(trial_id)
            self.pair = {"trial_id": trial_id, "sample_id": sample_id, "test_id": test_id}
            self.presentations = []
            self.phase = "waiting_sample"
        return self.snapshot()

    def claim_trigger(self):
        with self.lock:
            if self.phase not in ("waiting_sample", "waiting_test"):
                return None
            phase = "sample" if self.phase == "waiting_sample" else "test"
            self.phase = "presenting_" + phase
            return (self.generation, self.pair["trial_id"], phase, self.pair[phase + "_id"])

    def complete(self, claim):
        generation, trial_id, phase, stimulus_id = claim
        with self.lock:
            if generation != self.generation or self.phase != 'presenting_' + phase:
                return
            self.presentations.append({"trial_id": trial_id, "phase": phase,
                                       "stimulus_id": stimulus_id,
                                       "completed_at": datetime.now().isoformat(timespec="milliseconds")})
            self.phase = "waiting_test" if phase == "sample" else "idle"

    def reset(self):
        with self.lock:
            self.generation += 1
            self.pair = None
            self.presentations = []
            self.phase = "idle"


class ExpDMTSPatterns:
    """Reuse simple-driver hardware setup; present a prepared pair on two TTL edges."""
    def __init__(self, ol, config_file, simple_driver, log_file,
                 wait_for_trigger=True, ext_cables_used=True):
        if not wait_for_trigger:
            raise ValueError("DMTS patterns require Wait for trigger")
        import yaml
        import numpy as np
        import importlib
        self.np = np
        self.config_file = config_file
        self.log_file = log_file
        self.ext_cables_used = ext_cables_used
        with open(Path("Configurations") / config_file, encoding="utf-8") as handle:
            config = yaml.safe_load(handle)
        self.library = DMTSLibrary(config, ext_cables_used=ext_cables_used)
        self.protocol = DMTSPairState(self.library)
        driver_module = importlib.import_module(simple_driver.__module__)
        self.counts = {}
        for stimulus_id, item in self.library.patterns.items():
            matrix = np.zeros((10, 10), dtype=float)
            for label in item["labels"]:
                p, n = map(int, re.fullmatch(r"P(\d+)N(\d+)", label).groups())
                matrix[n - 1, p - 1] = item["irradiance"]
            frame = driver_module.get_frames_counts(matrix[:, :, np.newaxis], self.library.device_id,
                                                    ext_cables_used=ext_cables_used)[0]
            grid = np.zeros((20, 20), dtype=np.uint16)
            grid[19:9:-1, :10] = frame
            switches = sum(int(any(row)) * 2**bit for bit, row in enumerate(grid))
            currents = np.minimum(np.sum(grid, axis=0), 65535).astype(np.uint16)
            self.counts[stimulus_id] = (currents, switches)
        self.hardware = simple_driver(ol, config_file, "", wait_for_trigger=True,
                                      ext_cables_used=ext_cables_used)
        self.control_panel = self.hardware.control_panel
        self._stop_requested = False
        self.stopped = False
        self._low_seen = False
        self._observed_generation = -1
        self._reset_requested = False
        self._reset_complete = threading.Event()
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        self._log({"event": "library", "config": config, "fingerprint": self.library.fingerprint})

    def _log(self, event):
        event["timestamp"] = datetime.now().isoformat(timespec="milliseconds")
        with open(self.log_file, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event) + "\n")

    def prepare_pair(self, payload):
        if self.stopped or self._stop_requested:
            raise ValueError("Driver is stopped")
        if bool(self.hardware.trig[0]):
            raise ValueError("Trigger must be LOW before preparing a new pair")
        result = self.protocol.prepare(payload["trial_id"], payload["sample_id"],
                                       payload["test_id"], payload["fingerprint"])
        self._observed_generation = self.protocol.generation
        self._low_seen = True
        self._log({"event": "prepared", **result["pair"]})
        return result

    def reset_pair(self):
        self.protocol.reset()
        with self.protocol.lock:
            self.protocol.phase = 'resetting'
        self._reset_complete.clear()
        self._reset_requested = True
        if not self._reset_complete.wait(timeout=1.5):
            raise ValueError('Timed out waiting for LEDs to reset')
        self._log({"event": "reset"})

    async def _apply(self, stimulus_id):
        h = self.hardware
        h.current_dac_counts_buffer.fill(0)
        h.switches_buffer[0] = 0
        if stimulus_id:
            currents, switches = self.counts[stimulus_id]
            h.current_dac_counts_buffer[:] = currents
            h.switches_buffer[0] = switches
        h.trig_in[0] = 1
        await asyncio.sleep(0.005)
        h.trig_in[0] = 0

    async def _wait(self, seconds, generation):
        loop = asyncio.get_running_loop()
        deadline = loop.time() + seconds
        while loop.time() < deadline:
            if self._stop_requested or generation != self.protocol.generation:
                return False
            await asyncio.sleep(min(0.005, max(0, deadline - loop.time())))
        return not self._stop_requested and generation == self.protocol.generation

    async def run(self):
        self.control_panel.set_status("DMTS ready; waiting for pair")
        try:
            while not self._stop_requested:
                if self._reset_requested:
                    await self._apply(0)
                    self.protocol.reset()
                    self._reset_requested = False
                    self._reset_complete.set()
                high = bool(self.hardware.trig[0])
                generation = self.protocol.generation
                if generation != self._observed_generation:
                    self._low_seen = False
                    self._observed_generation = generation
                if not high:
                    self._low_seen = True
                claim = self.protocol.claim_trigger() if high and self._low_seen else None
                if claim is None:
                    await asyncio.sleep(0.001)
                    continue
                self._low_seen = False
                generation, trial_id, phase, stimulus_id = claim
                self.control_panel.set_status(f"DMTS {phase}: STIM{stimulus_id}")
                self._log({"event": "presentation_started", "trial_id": trial_id,
                           "phase": phase, "stimulus_id": stimulus_id})
                completed = True
                for _ in range(self.library.pulses):
                    if self._stop_requested or generation != self.protocol.generation:
                        completed = False
                        break
                    loop = asyncio.get_running_loop()
                    cycle_start = loop.time()
                    await self._apply(stimulus_id)
                    completed = await self._wait(max(0, cycle_start + self.library.on_s - loop.time()), generation)
                    await self._apply(0)
                    if not completed or not await self._wait(
                            max(0, cycle_start + 1 / self.library.frequency - loop.time()), generation):
                        completed = False
                        break
                if completed:
                    self.protocol.complete(claim)
                    self._log({"event": "presentation_completed", "trial_id": trial_id,
                               "phase": phase, "stimulus_id": stimulus_id})
                self.control_panel.set_status("DMTS " + self.protocol.snapshot()["phase"])
        finally:
            self.stop_()

    def stop_(self):
        self._stop_requested = True
        self.stopped = True
        self.protocol.reset()
        self._reset_complete.set()
        self.hardware.stop_()

    def on_stop_clicked(self, _button):
        self.stop_()
