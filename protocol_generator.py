import os
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox, ttk


APP_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_NI_SCRIPT = os.path.join(APP_DIR, "setup_valves_IRFork.m")


@dataclass(frozen=True)
class Parameter:
    key: str
    label: str
    default: str
    section: str
    kind: str = "text"
    choices: tuple[str, ...] = ()


PARAMETERS = [
    Parameter("UserName", "User", "username", "Session"),
    Parameter("MouseId", "Mouse ID", "1", "Session", "int"),
    Parameter("ProjectName", "Project", "ProjectName", "Session"),
    Parameter("NICard_filename", "NI script", DEFAULT_NI_SCRIPT.replace(os.sep, "/"), "Session"),
    Parameter("Sound_filename", "Sound file", "", "Session"),
    Parameter("frec", "Acquisition rate Hz", "1000", "Session", "float"),
    Parameter("bin", "Callback/bin s", "0.1", "Session", "float"),
    Parameter("TriggerTypeDropDown", "Trigger", "IRFork", "Session", "choice", ("IRFork", "Lick", "None")),
    Parameter("OuputformatDropDown", "Output format", "NWB", "Session", "choice", ("NWB", "BIDS", "No standard")),
    Parameter("TaskType", "Task type", "ClassicGoNoGo", "Task"),
    Parameter("MaxTrials", "Max trials", "300", "Task", "int"),
    Parameter("GoWeight", "Go weight", "0.5", "Task", "float"),
    Parameter("NoGoWeight", "No-go weight", "0.5", "Task", "float"),
    Parameter("GoSoundId", "Go sound ID", "1", "Task", "int"),
    Parameter("NoGoSoundId", "No-go sound ID", "10", "Task", "int"),
    Parameter("SoundLevel", "Sound level", "1", "Task", "float"),
    Parameter("RandomSeed", "Random seed", "0", "Task", "int"),
    Parameter("ITI_s", "ITI s", "2", "Timing", "float"),
    Parameter("ITIrandMin_s", "ITI rand min s", "0", "Timing", "float"),
    Parameter("ITIrandMax_s", "ITI rand max s", "0", "Timing", "float"),
    Parameter("Sounddelay_s", "Sound delay s", "0", "Timing", "float"),
    Parameter("SoundDuration_s", "Sound duration s", "0.2", "Timing", "float"),
    Parameter("TrialDuration_s", "Trial duration s", "5", "Timing", "float"),
    Parameter("ResponseWindow_s", "Response window s", "2", "Timing", "float"),
    Parameter("RewardDelay_s", "Reward delay s", "0", "Timing", "float"),
    Parameter("Rewardduration_ms", "Reward duration ms", "40", "Outcome", "float"),
    Parameter("RewardGoProb", "RewardGo Prob", "1", "Outcome", "float"),
    Parameter("PunishNoGoFA", "Timeout false alarms", "1", "Outcome", "float"),
    Parameter("HITThreshold_s", "HIT threshold time s", "1", "Outcome", "int"),
    Parameter("Minlickcount", "Min lick count", "1", "Outcome", "int"),
    Parameter("Lickthreshold", "Signal threshold V", "1", "Outcome", "float"),
    Parameter("LeverTaskType", "Task type", "Lever", "Lever"),
    Parameter("LeverThreshold", "Lever threshold V", "1", "Lever", "float"),
    Parameter("LeverGoSoundId", "GO sound ID", "1", "Lever", "int"),
    Parameter("LeverSoundLevel", "Sound level", "1", "Lever", "float"),
    Parameter("LeverHoldTime_s", "Time above threshold s", "0.5", "LeverTiming", "float"),
    Parameter("LeverRewardduration_ms", "Reward duration ms", "40", "LeverOutcome", "float"),
    Parameter("LeverRewardGo", "Reward go trials", "1", "LeverOutcome", "float"),
]

COMMON_SECTIONS = ("Session",)
BEHAVIOR_TABS = [
    ("Classic Go/No-go", ("Task", "Timing", "Outcome")),
    ("Lever", ("Lever", "LeverTiming", "LeverOutcome")),
]


class GoNoGoDatGenerator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Go/No-go .dat Generator")
        self.geometry("1180x720")
        self.minsize(980, 620)

        self.variables: dict[str, tk.StringVar] = {}
        self.status_var = tk.StringVar(value="Ready.")
        self.current_path = tk.StringVar(value=os.path.join(APP_DIR, "go_nogo_parameters.dat"))
        self._pending_redraw = None
        self._syncing_weight = False
        self._syncing_trial_duration = False
        self._hit_row_widgets = []
        self._min_lick_row_widgets = []
        self._lick_threshold_row_widgets = []

        self._build_ui()
        self._bind_live_updates()
        self.update_response_visibility()
        self.redraw_timeline()

    def _build_ui(self):
        root = ttk.Frame(self, padding=10)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=0, minsize=440)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        left = ttk.Frame(root)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)

        right = ttk.Frame(root)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        self._build_parameter_panel(left)
        self._build_plot_panel(right)
        self._build_actions(root)

    def _build_parameter_panel(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        common = ttk.Frame(parent)
        common.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        common.columnconfigure(0, weight=1)
        self._populate_parameter_sections(common, COMMON_SECTIONS)

        self.behavior_notebook = ttk.Notebook(parent)
        self.behavior_notebook.grid(row=1, column=0, sticky="nsew")
        for tab_name, sections in BEHAVIOR_TABS:
            tab = ttk.Frame(self.behavior_notebook)
            tab.columnconfigure(0, weight=1)
            tab.rowconfigure(0, weight=1)
            self.behavior_notebook.add(tab, text=tab_name)
            inner = self._add_scrollable_area(tab)
            self._populate_parameter_sections(inner, sections)
        self.behavior_notebook.bind("<<NotebookTabChanged>>", lambda _event: self.schedule_redraw())

    def _add_scrollable_area(self, parent):
        canvas = tk.Canvas(parent, width=430, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        inner_window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(inner_window, width=event.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        inner.columnconfigure(0, weight=1)
        return inner

    def _populate_parameter_sections(self, parent, sections):
        parent.columnconfigure(0, weight=1)
        row = 0
        for section in sections:
            frame = ttk.LabelFrame(parent, text=section)
            frame.grid(row=row, column=0, sticky="ew", padx=2, pady=(0, 8))
            frame.columnconfigure(1, weight=1)
            row += 1
            field_row = 0
            for parameter in [item for item in PARAMETERS if item.section == section]:
                if parameter.key in {"ITIrandMin_s", "ITIrandMax_s"}:
                    continue
                if parameter.key == "ITI_s":
                    self._add_iti_fields(frame, field_row)
                    field_row += 1
                    continue
                self._add_parameter_field(frame, parameter, field_row)
                field_row += 1

    def _add_iti_fields(self, parent, row):
        ttk.Label(parent, text="ITI").grid(row=row, column=0, sticky="w", padx=6, pady=3)
        field_frame = ttk.Frame(parent)
        field_frame.grid(row=row, column=1, columnspan=2, sticky="ew", padx=(4, 6), pady=3)
        for column in range(6):
            field_frame.columnconfigure(column, weight=1 if column in {1, 3, 5} else 0)

        for column, key, label in (
            (0, "ITI_s", "base"),
            (2, "ITIrandMin_s", "rand min"),
            (4, "ITIrandMax_s", "rand max"),
        ):
            parameter = next(item for item in PARAMETERS if item.key == key)
            variable = tk.StringVar(value=parameter.default)
            self.variables[key] = variable
            ttk.Label(field_frame, text=label).grid(row=0, column=column, sticky="w", padx=(0, 3))
            ttk.Entry(field_frame, textvariable=variable, width=7).grid(
                row=0,
                column=column + 1,
                sticky="ew",
                padx=(0, 8 if column < 4 else 0),
            )

    def _add_parameter_field(self, parent, parameter, row):
        label = ttk.Label(parent, text=parameter.label)
        label.grid(row=row, column=0, sticky="w", padx=6, pady=3)
        variable = tk.StringVar(value=parameter.default)
        self.variables[parameter.key] = variable

        if parameter.kind == "choice":
            widget = ttk.Combobox(parent, textvariable=variable, values=parameter.choices, state="readonly", width=22)
        elif parameter.kind == "bool":
            widget = ttk.Combobox(parent, textvariable=variable, values=("1", "0"), state="readonly", width=22)
        else:
            state = "readonly" if parameter.key == "TrialDuration_s" else "normal"
            widget = ttk.Entry(parent, textvariable=variable, width=25, state=state)
        widget.grid(row=row, column=1, sticky="ew", padx=(4, 6), pady=3)
        if parameter.key == "HITThreshold_s":
            self._hit_row_widgets = [label, widget]
        elif parameter.key == "Minlickcount":
            self._min_lick_row_widgets = [label, widget]
        elif parameter.key == "Lickthreshold":
            self._lick_threshold_row_widgets = [label, widget]

        if parameter.key == "NICard_filename":
            ttk.Button(parent, text="Browse", command=self.choose_ni_script).grid(row=row, column=2, padx=(0, 6), pady=3)
        elif parameter.key == "Sound_filename":
            ttk.Button(parent, text="Browse", command=self.choose_sound_file).grid(row=row, column=2, padx=(0, 6), pady=3)

    def _build_plot_panel(self, parent):
        plot_frame = ttk.LabelFrame(parent, text="Trial Timeline Preview")
        plot_frame.grid(row=0, column=0, sticky="nsew")
        plot_frame.rowconfigure(0, weight=1)
        plot_frame.columnconfigure(0, weight=1)

        self.timeline = tk.Canvas(plot_frame, bg="white", highlightthickness=0)
        self.timeline.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.timeline.bind("<Configure>", lambda _event: self.schedule_redraw())

        summary = ttk.Frame(parent)
        summary.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        summary.columnconfigure(0, weight=1)
        self.summary_var = tk.StringVar(value="")
        ttk.Label(summary, textvariable=self.summary_var).grid(row=0, column=0, sticky="w")

    def _build_actions(self, root):
        actions = ttk.Frame(root)
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        actions.columnconfigure(1, weight=1)

        ttk.Button(actions, text="New Defaults", command=self.reset_defaults).grid(row=0, column=0, padx=(0, 6))
        ttk.Entry(actions, textvariable=self.current_path).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(actions, text="Load .dat", command=self.load_dat).grid(row=0, column=2, padx=6)
        ttk.Button(actions, text="Save .dat", command=self.save_dat).grid(row=0, column=3, padx=(6, 0))
        ttk.Label(actions, textvariable=self.status_var).grid(row=1, column=0, columnspan=4, sticky="w", pady=(6, 0))

    def _bind_live_updates(self):
        for variable in self.variables.values():
            variable.trace_add("write", lambda *_args: self.schedule_redraw())
        self.variables["GoWeight"].trace_add("write", lambda *_args: self.sync_weight("GoWeight"))
        self.variables["NoGoWeight"].trace_add("write", lambda *_args: self.sync_weight("NoGoWeight"))
        for key in ("Sounddelay_s", "SoundDuration_s", "RewardDelay_s", "ResponseWindow_s"):
            self.variables[key].trace_add("write", lambda *_args: self.sync_trial_duration())
        self.variables["TriggerTypeDropDown"].trace_add("write", lambda *_args: self.update_response_visibility())
        self.sync_trial_duration()

    def sync_weight(self, changed_key):
        if self._syncing_weight:
            return
        value = self._parse_float(changed_key, None)
        if value is None or value < 0 or value > 1:
            return

        paired_key = "NoGoWeight" if changed_key == "GoWeight" else "GoWeight"
        paired_value = 1.0 - value
        self._syncing_weight = True
        self.variables[paired_key].set(f"{paired_value:.6g}")
        self._syncing_weight = False

    def sync_trial_duration(self):
        if self._syncing_trial_duration:
            return
        values = [
            self._parse_float("Sounddelay_s", None),
            self._parse_float("SoundDuration_s", None),
            self._parse_float("RewardDelay_s", None),
            self._parse_float("ResponseWindow_s", None),
        ]
        if any(value is None or value < 0 for value in values):
            return

        self._syncing_trial_duration = True
        self.variables["TrialDuration_s"].set(f"{sum(values):.6g}")
        self._syncing_trial_duration = False

    def update_response_visibility(self):
        trigger_type = self.variables["TriggerTypeDropDown"].get()
        show_hit = trigger_type == "IRFork"
        show_lick = trigger_type == "Lick"
        for widget in self._hit_row_widgets:
            if show_hit:
                widget.grid()
            else:
                widget.grid_remove()
        for widget in self._min_lick_row_widgets:
            if show_lick:
                widget.grid()
            else:
                widget.grid_remove()
        for widget in self._lick_threshold_row_widgets:
            if show_lick:
                widget.grid()
            else:
                widget.grid_remove()

    def choose_ni_script(self):
        path = filedialog.askopenfilename(
            title="Select NI script",
            initialdir=APP_DIR,
            filetypes=[("MATLAB files", "*.m"), ("All files", "*.*")],
        )
        if path:
            self.variables["NICard_filename"].set(path.replace(os.sep, "/"))

    def choose_sound_file(self):
        path = filedialog.askopenfilename(
            title="Select sound file",
            initialdir=APP_DIR,
            filetypes=[
                ("Sound and MAT files", "*.mat *.wav"),
                ("MAT files", "*.mat"),
                ("WAV files", "*.wav"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.variables["Sound_filename"].set(path.replace(os.sep, "/"))

    def schedule_redraw(self):
        if self._pending_redraw is not None:
            self.after_cancel(self._pending_redraw)
        self._pending_redraw = self.after(40, self.redraw_timeline)

    def reset_defaults(self):
        for parameter in self.get_active_parameters():
            self.variables[parameter.key].set(parameter.default)
        default_name = "lever_parameters.dat" if self.get_active_behavior() == "Lever" else "go_nogo_parameters.dat"
        self.current_path.set(os.path.join(APP_DIR, default_name))
        self.status_var.set("Defaults restored.")

    def load_dat(self):
        path = filedialog.askopenfilename(
            title="Load go/no-go parameters",
            initialdir=APP_DIR,
            filetypes=[("DAT files", "*.dat"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            values = read_dat(path)
        except OSError as exc:
            messagebox.showerror("Load failed", str(exc))
            return

        for key, value in values.items():
            if self.loaded_values_are_lever(values) and key == "TaskType":
                self.variables["LeverTaskType"].set(value)
            elif self.loaded_values_are_lever(values) and key == "GoSoundId":
                self.variables["LeverGoSoundId"].set(value)
            elif self.loaded_values_are_lever(values) and key == "SoundLevel":
                self.variables["LeverSoundLevel"].set(value)
            elif self.loaded_values_are_lever(values) and key == "Rewardduration_ms":
                self.variables["LeverRewardduration_ms"].set(value)
            elif self.loaded_values_are_lever(values) and key in {"RewardGo", "RewardGoProb"}:
                self.variables["LeverRewardGo"].set(value)
            elif key == "RewardGo":
                self.variables["RewardGoProb"].set(value)
            elif key == "HIT_s":
                self.variables["HITThreshold_s"].set(value)
            elif key in self.variables:
                self.variables[key].set(value)
            elif key == "GoProbability":
                self.variables["GoWeight"].set(value)
            elif key == "NoGoProbability":
                self.variables["NoGoWeight"].set(value)
            elif key == "ITIrand_s":
                self.variables["ITIrandMin_s"].set(value)
                self.variables["ITIrandMax_s"].set(value)
            elif key == "PunishInterval":
                self.variables["PunishNoGoFA"].set(value)
        self.select_behavior_for_loaded_values(values)
        self.sync_trial_duration()
        self.current_path.set(path)
        self.status_var.set(f"Loaded {os.path.basename(path)}.")

    def select_behavior_for_loaded_values(self, values):
        behavior = None
        if self.loaded_values_are_lever(values):
            behavior = "Lever"
        elif values.get("TaskType") == "ClassicGoNoGo" or "GoWeight" in values or "NoGoWeight" in values:
            behavior = "Classic Go/No-go"
        if behavior is None or not hasattr(self, "behavior_notebook"):
            return
        for index in range(self.behavior_notebook.index("end")):
            if self.behavior_notebook.tab(index, "text") == behavior:
                self.behavior_notebook.select(index)
                break

    def loaded_values_are_lever(self, values):
        return values.get("TaskType") == "Lever" or values.get("LeverTaskType") == "Lever" or "LeverThreshold" in values

    def save_dat(self):
        path = self.current_path.get().strip()
        if not path:
            path = os.path.join(APP_DIR, "go_nogo_parameters.dat")
        path = filedialog.asksaveasfilename(
            title="Save go/no-go parameters",
            initialdir=os.path.dirname(path) or APP_DIR,
            initialfile=os.path.basename(path) or "go_nogo_parameters.dat",
            defaultextension=".dat",
            filetypes=[("DAT files", "*.dat"), ("All files", "*.*")],
        )
        if not path:
            return

        errors = self.validate_parameters()
        if errors:
            messagebox.showerror("Check parameters", "\n".join(errors[:8]))
            return

        values = {parameter.key: self.variables[parameter.key].get().strip() for parameter in self.get_active_parameters()}
        try:
            write_dat(path, values, self.get_active_parameters())
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc))
            return
        self.current_path.set(path)
        self.status_var.set(f"Saved {os.path.basename(path)}.")

    def validate_parameters(self):
        errors = []
        active_behavior = self.get_active_behavior()
        trigger_type = self.variables["TriggerTypeDropDown"].get()
        for parameter in self.get_active_parameters():
            if parameter.key == "HITThreshold_s" and trigger_type != "IRFork":
                continue
            if parameter.key in {"Minlickcount", "Lickthreshold"} and trigger_type != "Lick":
                continue
            value = self.variables[parameter.key].get().strip()
            if parameter.kind == "float" and self._parse_float(parameter.key, None) is None:
                errors.append(f"{parameter.label} must be numeric.")
            elif parameter.kind == "int" and self._parse_int(parameter.key, None) is None:
                errors.append(f"{parameter.label} must be an integer.")

        if active_behavior == "Lever":
            lever_threshold = self._parse_float("LeverThreshold", None)
            if lever_threshold is None or lever_threshold <= 0:
                errors.append("Lever threshold V must be greater than 0.")
            lever_sound = self._parse_int("LeverGoSoundId", None)
            if lever_sound is None or lever_sound < 1:
                errors.append("GO sound ID must be a positive integer.")
            lever_hold_time = self._parse_float("LeverHoldTime_s", None)
            if lever_hold_time is None or lever_hold_time <= 0:
                errors.append("Time above threshold s must be greater than 0.")
            reward_duration = self._parse_float("LeverRewardduration_ms", None)
            if reward_duration is None or reward_duration < 0:
                errors.append("Reward duration ms must be positive or 0.")
            reward_go = self._parse_float("LeverRewardGo", None)
            if reward_go is None or not 0 <= reward_go <= 1:
                errors.append("Reward go trials must be a fraction between 0 and 1.")
            return errors

        trial_duration = self._parse_float("TrialDuration_s", 0)
        response_start, response_end = self._response_window()
        if trial_duration <= 0:
            errors.append("Trial duration must be greater than 0.")
        if response_end > trial_duration:
            errors.append("Response window extends past the trial duration.")
        iti_rand_min = self._parse_float("ITIrandMin_s", None)
        iti_rand_max = self._parse_float("ITIrandMax_s", None)
        if iti_rand_min is None or iti_rand_min < 0:
            errors.append("ITI rand min must be a positive number or 0.")
        if iti_rand_max is None or iti_rand_max < 0:
            errors.append("ITI rand max must be a positive number or 0.")
        if iti_rand_min is not None and iti_rand_max is not None and iti_rand_min > iti_rand_max:
            errors.append("ITI rand min must be smaller than or equal to ITI rand max.")
        go_weight = self._parse_float("GoWeight", None)
        nogo_weight = self._parse_float("NoGoWeight", None)
        if go_weight is None or not 0 <= go_weight <= 1:
            errors.append("Go weight must be between 0 and 1.")
        if nogo_weight is None or not 0 <= nogo_weight <= 1:
            errors.append("No-go weight must be between 0 and 1.")
        if go_weight is not None and nogo_weight is not None:
            if abs((go_weight + nogo_weight) - 1.0) > 1e-6:
                errors.append("Go and no-go weights must sum to 1.")
        reward_go = self._parse_float("RewardGoProb", None)
        if reward_go is None or not 0 <= reward_go <= 1:
            errors.append("RewardGo Prob must be a fraction between 0 and 1.")
        punish_no_go_fa = self._parse_float("PunishNoGoFA", None)
        if punish_no_go_fa is None or not 0 <= punish_no_go_fa <= 25:
            errors.append("Timeout false alarms must be between 0 and 25 seconds.")
        if trigger_type == "IRFork":
            hit_s = self._parse_int("HITThreshold_s", None)
            if hit_s is None or not 1 <= hit_s <= 100:
                errors.append("HIT threshold time s must be an integer from 1 to 100.")
        elif trigger_type == "Lick":
            min_lick_count = self._parse_int("Minlickcount", None)
            if min_lick_count is None or min_lick_count < 1:
                errors.append("Min lick count must be a positive integer.")
            lick_threshold = self._parse_float("Lickthreshold", None)
            if lick_threshold is None or lick_threshold <= 0:
                errors.append("Lickthreshold must be greater than 0.")
        return errors

    def get_active_behavior(self):
        if not hasattr(self, "behavior_notebook"):
            return "Classic Go/No-go"
        selected = self.behavior_notebook.select()
        if not selected:
            return "Classic Go/No-go"
        return self.behavior_notebook.tab(selected, "text")

    def get_active_parameters(self):
        active_behavior = self.get_active_behavior()
        active_sections = set(COMMON_SECTIONS)
        for tab_name, sections in BEHAVIOR_TABS:
            if tab_name == active_behavior:
                active_sections.update(sections)
                break
        return [parameter for parameter in PARAMETERS if parameter.section in active_sections]

    def redraw_timeline(self):
        self._pending_redraw = None
        canvas = self.timeline
        canvas.delete("all")
        if self.get_active_behavior() == "Lever":
            self.redraw_lever_timeline(canvas)
            return
        self.redraw_go_nogo_timeline(canvas)

    def redraw_go_nogo_timeline(self, canvas):
        width = max(500, canvas.winfo_width())
        height = max(320, canvas.winfo_height())

        margin_left = 128
        margin_right = 28
        margin_top = 36
        row_gap = 46
        axis_y = margin_top + row_gap * 5 + 34

        timing = self._timeline_values()
        total_s = max(timing["trial_duration"], timing["cycle_duration"], 0.1)
        scale = (width - margin_left - margin_right) / total_s

        self._draw_axis(canvas, margin_left, axis_y, width - margin_right, total_s, scale)

        rows = [
            ("ITI", margin_top, "#6c757d", [(0, timing["iti_base"], "ITI")]),
            ("Sound onset", margin_top + row_gap, "#1f77b4", [(timing["sound_start"], timing["sound_end"], "sound")]),
            ("Response window", margin_top + row_gap * 2, "#2ca02c", [(timing["response_start"], timing["response_end"], "response window")]),
            ("Reward (HIT)", margin_top + row_gap * 3, "#17a589", [(timing["reward_start"], timing["reward_end"], "reward")]),
            ("Timeout (FA)", margin_top + row_gap * 4, "#d62728", [(timing["timeout_start"], timing["timeout_end"], "timeout")]),
            ("Trial", margin_top + row_gap * 5, "#9467bd", [(timing["trial_start"], timing["trial_end"], "trial")]),
        ]

        for label, y, color, spans in rows:
            canvas.create_text(margin_left - 12, y, text=label, anchor="e", fill="#222")
            canvas.create_line(margin_left, y, width - margin_right, y, fill="#dddddd")
            for start, end, text in spans:
                self._draw_span(canvas, margin_left, y, scale, start, end, color, text)

        self._draw_double_arrow(
            canvas,
            margin_left,
            margin_top + 22,
            scale,
            timing["iti_rand_min_end"],
            timing["iti_rand_max_end"],
            "#6c757d",
            "rand range",
        )
        trigger_x = margin_left + timing["trigger"] * scale
        canvas.create_line(trigger_x, margin_top - 20, trigger_x, axis_y + 16, fill="#333333", dash=(4, 3))
        canvas.create_text(trigger_x, margin_top - 24, text="trigger", anchor="s", fill="#333333")

        self.summary_var.set(
            "Cycle: "
            f"{timing['cycle_duration']:.3g} s | Sound: {timing['sound_start']:.3g}-{timing['sound_end']:.3g} s | "
            f"Response: {timing['response_start']:.3g}-{timing['response_end']:.3g} s | "
            f"ITI rand range: {timing['iti_rand_min_end']:.3g}-{timing['iti_rand_max_end']:.3g} s | "
            f"Punish interval: {timing['timeout_start']:.3g}-{timing['timeout_end']:.3g} s"
        )

    def redraw_lever_timeline(self, canvas):
        width = max(500, canvas.winfo_width())
        height = max(320, canvas.winfo_height())
        margin_left = 132
        margin_right = 28
        margin_top = 46
        row_gap = 62
        axis_y = margin_top + row_gap * 3 + 42

        hold_time = max(0.0, self._parse_float("LeverHoldTime_s", 0.5))
        reward_duration_s = max(0.0, self._parse_float("LeverRewardduration_ms", 40.0) / 1000.0)
        threshold = self._parse_float("LeverThreshold", 1.0)
        crossing_time = 1.0
        sound_start = crossing_time
        sound_duration = 0.05
        reward_start = crossing_time + hold_time
        reward_end = reward_start + reward_duration_s
        total_s = max(crossing_time + hold_time + sound_duration, reward_end, 2.0)
        scale = (width - margin_left - margin_right) / total_s

        self._draw_axis(canvas, margin_left, axis_y, width - margin_right, total_s, scale)

        signal_y = margin_top
        hold_y = margin_top + row_gap
        sound_y = margin_top + row_gap * 2
        reward_y = margin_top + row_gap * 3

        for label, y in (
            ("Lever signal", signal_y),
            ("Above threshold", hold_y),
            ("Sound trigger", sound_y),
            ("Reward valve", reward_y),
        ):
            canvas.create_text(margin_left - 12, y, text=label, anchor="e", fill="#222")
            canvas.create_line(margin_left, y, width - margin_right, y, fill="#dddddd")

        signal_points = [
            (0.0, signal_y + 22),
            (0.75, signal_y + 22),
            (crossing_time, signal_y - 18),
            (reward_start, signal_y - 18),
            (min(total_s, reward_start + max(0.05, total_s * 0.08)), signal_y + 22),
            (total_s, signal_y + 22),
        ]
        coords = []
        for t, y in signal_points:
            coords.extend((margin_left + t * scale, y))
        canvas.create_line(*coords, fill="#555555", width=3)
        threshold_y = signal_y
        canvas.create_line(margin_left, threshold_y, width - margin_right, threshold_y, fill="#d62728", dash=(4, 3))
        canvas.create_text(width - margin_right, threshold_y - 8, text=f"threshold {threshold:g} V", anchor="e", fill="#d62728")

        self._draw_double_arrow(canvas, margin_left, hold_y + 18, scale, crossing_time, reward_start, "#9467bd", "required time")
        self._draw_span(canvas, margin_left, hold_y, scale, crossing_time, reward_start, "#9467bd", "above threshold")
        self._draw_span(canvas, margin_left, sound_y, scale, sound_start, sound_start + sound_duration, "#1f77b4", "sound")
        self._draw_span(canvas, margin_left, reward_y, scale, reward_start, reward_end, "#2ca02c", "reward")

        crossing_x = margin_left + crossing_time * scale
        canvas.create_line(crossing_x, margin_top - 24, crossing_x, axis_y + 16, fill="#333333", dash=(4, 3))
        canvas.create_text(crossing_x, margin_top - 28, text="threshold crossed", anchor="s", fill="#333333")

        trigger_x = margin_left + reward_start * scale
        canvas.create_line(trigger_x, margin_top - 24, trigger_x, axis_y + 16, fill="#333333", dash=(4, 3))
        canvas.create_text(trigger_x, margin_top - 28, text="reward trigger", anchor="s", fill="#333333")

        self.summary_var.set(
            "Lever: "
            f"threshold {threshold:g} V | above threshold {hold_time:.3g} s | "
            f"sound id {self.variables['LeverGoSoundId'].get()} | "
            f"reward {reward_duration_s:.3g} s | reward fraction {self.variables['LeverRewardGo'].get()}"
        )

    def _draw_axis(self, canvas, x0, y, x1, total_s, scale):
        canvas.create_line(x0, y, x1, y, fill="#333333")
        tick_count = min(10, max(2, int(total_s) + 1))
        step = nice_step(total_s / tick_count)
        tick = 0.0
        while tick <= total_s + step * 0.25:
            x = x0 + tick * scale
            canvas.create_line(x, y - 5, x, y + 5, fill="#333333")
            canvas.create_text(x, y + 20, text=f"{tick:g}", anchor="n", fill="#333333")
            tick += step
        canvas.create_text(x1, y + 36, text="time (s)", anchor="e", fill="#333333")

    def _draw_span(self, canvas, x0, y, scale, start, end, color, text):
        start = max(0.0, start)
        end = max(start, end)
        x_start = x0 + start * scale
        x_end = x0 + end * scale
        if end == start:
            canvas.create_line(x_start, y - 15, x_start, y + 15, fill=color, width=3)
            canvas.create_text(x_start + 6, y - 18, text=text, anchor="sw", fill=color)
            return

        min_width = 4
        if x_end - x_start < min_width:
            x_end = x_start + min_width
        canvas.create_rectangle(x_start, y - 13, x_end, y + 13, fill=color, outline="")
        canvas.create_text((x_start + x_end) / 2, y, text=text, fill="white")

    def _draw_double_arrow(self, canvas, x0, y, scale, start, end, color, text):
        start = max(0.0, start)
        end = max(start, end)
        x_start = x0 + start * scale
        x_end = x0 + end * scale
        if x_end - x_start < 8:
            x_end = x_start + 8

        canvas.create_line(x_start, y, x_end, y, fill=color, width=2, arrow=tk.BOTH)
        canvas.create_line(x_start, y - 8, x_start, y + 8, fill=color)
        canvas.create_line(x_end, y - 8, x_end, y + 8, fill=color)
        canvas.create_text((x_start + x_end) / 2, y + 10, text=text, anchor="n", fill=color)

    def _timeline_values(self):
        iti = max(0.0, self._parse_float("ITI_s", 2.0))
        iti_rand_min = max(0.0, self._parse_float("ITIrandMin_s", 0.0))
        iti_rand_max = max(iti_rand_min, self._parse_float("ITIrandMax_s", iti_rand_min))
        trial_start = iti + iti_rand_max
        pre_trigger = 0.0
        sound_delay = max(0.0, self._parse_float("Sounddelay_s", 0.0))
        sound_duration = max(0.0, self._parse_float("SoundDuration_s", 0.2))
        trial_duration = max(0.01, self._parse_float("TrialDuration_s", 5.0))
        response_start_relative, response_end_relative = self._response_window()
        punish_interval = max(0.0, self._parse_float("PunishNoGoFA", 3.0))
        reward_duration_s = max(0.0, self._parse_float("Rewardduration_ms", 40.0) / 1000.0)

        trigger = trial_start + pre_trigger
        sound_start = trial_start + pre_trigger + sound_delay
        sound_end = sound_start + sound_duration
        response_start = trial_start + response_start_relative
        response_end = trial_start + response_end_relative
        reward_start = response_end
        reward_end = reward_start + reward_duration_s
        timeout_start = response_end
        timeout_end = timeout_start + punish_interval
        trial_end = trial_start + trial_duration
        cycle_duration = max(trial_end, timeout_end)

        return {
            "iti_base": iti,
            "iti_rand_min_end": iti + iti_rand_min,
            "iti_rand_max_end": iti + iti_rand_max,
            "trial_start": trial_start,
            "trigger": trigger,
            "sound_start": sound_start,
            "sound_end": sound_end,
            "response_start": response_start,
            "response_end": response_end,
            "reward_start": reward_start,
            "reward_end": reward_end,
            "timeout_start": timeout_start,
            "timeout_end": timeout_end,
            "trial_duration": trial_duration,
            "trial_end": trial_end,
            "cycle_duration": cycle_duration,
        }

    def _response_window(self):
        pre_trigger = 0.0
        sound_delay = max(0.0, self._parse_float("Sounddelay_s", 0.0))
        sound_duration = max(0.0, self._parse_float("SoundDuration_s", 0.2))
        reward_delay = max(0.0, self._parse_float("RewardDelay_s", 0.0))
        response_duration = max(0.0, self._parse_float("ResponseWindow_s", 2.0))
        response_start = pre_trigger + sound_delay + sound_duration + reward_delay
        return response_start, response_start + response_duration

    def _parse_float(self, key, default):
        try:
            return float(self.variables[key].get())
        except (KeyError, TypeError, ValueError):
            return default

    def _parse_int(self, key, default):
        try:
            value = float(self.variables[key].get())
        except (KeyError, TypeError, ValueError):
            return default
        if not value.is_integer():
            return default
        return int(value)


def nice_step(raw_step):
    if raw_step <= 0:
        return 1.0
    magnitude = 10 ** (len(str(int(raw_step))) - 1) if raw_step >= 1 else 10 ** int(f"{raw_step:e}".split("e")[1])
    normalized = raw_step / magnitude
    if normalized <= 1:
        nice = 1
    elif normalized <= 2:
        nice = 2
    elif normalized <= 5:
        nice = 5
    else:
        nice = 10
    return nice * magnitude


def read_dat(path):
    values = {}
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def write_dat(path, values, parameters):
    key_aliases = {
        "LeverTaskType": "TaskType",
        "LeverGoSoundId": "GoSoundId",
        "LeverSoundLevel": "SoundLevel",
        "LeverRewardduration_ms": "Rewardduration_ms",
        "LeverRewardGo": "RewardGoProb",
    }
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        for parameter in parameters:
            if parameter.key == "HITThreshold_s" and values.get("TriggerTypeDropDown") != "IRFork":
                continue
            if parameter.key in {"Minlickcount", "Lickthreshold"} and values.get("TriggerTypeDropDown") != "Lick":
                continue
            value = values.get(parameter.key, parameter.default)
            if parameter.key in {"NICard_filename", "Sound_filename"}:
                value = value.replace("\\", "/")
            key = key_aliases.get(parameter.key, parameter.key)
            handle.write(f"{key}={value}\n")


if __name__ == "__main__":
    app = GoNoGoDatGenerator()
    app.mainloop()
