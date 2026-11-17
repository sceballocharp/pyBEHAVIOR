"""Inline entry validation with separate editable and active values."""

import math
import re
import tkinter as tk
from tkinter import ttk


OPTIONAL = {'random_seed', 'task_type', 'iti_rand_min_s', 'iti_rand_max_s',
            'reward_go', 'punish_no_go_fa', 'min_lick_count', 'lick_threshold'}
TEXT = {'user_name', 'mouse_id', 'project_name', 'device', 'random_seed',
        'save_root', 'ni_script', 'sound_file'}
INTEGER = {'sound_id', 'classic_go_sound_id', 'classic_nogo_sound_id',
           'sample_sound_id', 'test_sound_id', 'lever_go_sound_id', 'lever_test_sound_id',
           'sequence_length', 'max_trials', 'min_lick_count', 'tac_min_lick_count',
           'dmts_misses_before_reminder', 'dmts_reminder_trials'}
POSITIVE = {'sequence_length', 'min_lick_count', 'tac_min_lick_count',
            'dmts_misses_before_reminder', 'dmts_reminder_trials',
            'rate_hz', 'callback_s', 'window_s'}
SIGNED = {'threshold_v', 'lick_threshold', 'tac_left_threshold', 'tac_right_threshold',
          'left_y_min', 'left_y_max', 'right_y_min', 'right_y_max'}
GROUPS = [('sequence_values', 'sequence_weights'), ('iti_rand_min_s', 'iti_rand_max_s'),
          ('left_y_min', 'left_y_max'), ('right_y_min', 'right_y_max'),
          ('tac_left_channel', 'tac_right_channel'),
          ('classic_go_sound_id', 'classic_nogo_sound_id')]


def numbers(text, integer=False):
    tokens = text.replace(',', ' ').replace(';', ' ').split()
    if not tokens:
        raise ValueError
    values = [float(token) for token in tokens]
    if any(not math.isfinite(v) or (integer and not v.is_integer()) for v in values):
        raise ValueError
    return values


def validate_setting(name, text, context):
    """Return a short error, or an empty string for a valid editable value."""
    text = text.strip()
    if not text:
        return '' if name in OPTIONAL else 'Enter a value'
    if name == 'task_type':
        allowed = {'classicgonogo', 'gonogo', 'go/nogo', 'go nogo', 'lever', 'dmts',
                   'tac', '2ac', 'twoalternatechoice', 'twoalternativechoice',
                   'tacpretraining', 'tac_pretraining', 'tac-pretraining', 'tacshaping'}
        return '' if text.lower() in allowed else 'Use ClassicGoNoGo, DMTS, Lever or tAC'
    if name in TEXT:
        if '\n' in text or '\r' in text:
            return 'Use a single line'
        if name in {'save_root', 'ni_script', 'sound_file'} and any(c in text for c in '*?"<>|'):
            return 'Enter a valid path'
        if name == 'sound_file' and not text.lower().endswith('.mat'):
            return 'Select a .mat sound bank'
        if name == 'ni_script' and not text.lower().endswith('.m'):
            return 'Select a .m setup script'
        return ''
    if name in {'tac_left_channel', 'tac_right_channel', 'channels'}:
        channel = r'ai\d+'
        pattern = rf'{channel}(?::{channel})?' if name == 'channels' else channel
        tokens = text.replace(';', ',').replace(' ', '').split(',')
        if name != 'channels' and len(tokens) != 1:
            return 'Use one channel, e.g. ai0'
        if not all(re.fullmatch(pattern, token, re.IGNORECASE) for token in tokens):
            return 'Use ai0,ai1 or ai0:ai3' if name == 'channels' else 'Use a channel, e.g. ai0'
        if name == 'channels' and ':' in text and len(tokens) != 1:
            return 'Use one range or a channel list'
        if name == 'channels' and ':' in text:
            lo, hi = text.replace(' ', '').lower().split(':')
            if int(lo[2:]) > int(hi[2:]):
                return 'Channel range must increase'
        other = {'tac_left_channel': 'tac_right_channel', 'tac_right_channel': 'tac_left_channel'}.get(name)
        if other and context.get(other, '').strip().lower() == text.lower():
            return 'Left and right must differ'
        return ''
    if name == 'dmts_sound_ids':
        for token in text.replace(',', ' ').replace(';', ' ').split():
            if not re.fullmatch(r'\d+(?:[:-]\d+)?', token):
                return 'Use IDs or ranges, e.g. 1:16'
            if any(int(v) < 1 for v in re.split('[:-]', token)):
                return 'Sound IDs must be positive'
        return ''
    if name in {'sequence_values', 'sequence_weights', 'dmts_modality_probabilities'}:
        try:
            values = numbers(text, integer=name == 'sequence_values')
        except ValueError:
            return 'Enter whole-number IDs' if name == 'sequence_values' else 'Enter finite numbers'
        if any(v < 0 for v in values):
            return 'Values must be nonnegative'
        if name == 'dmts_modality_probabilities':
            if len(values) != 2 or any(v > 1 for v in values) or not math.isclose(sum(values), 1, abs_tol=1e-9, rel_tol=0):
                return 'Two probabilities; sum must be 1'
        elif name == 'sequence_weights':
            try:
                ids = numbers(context.get('sequence_values', ''), integer=True)
            except ValueError:
                return 'Finish the sequence IDs first'
            if len(values) != len(ids):
                return 'One weight per sequence value'
            if sum(values) <= 0:
                return 'At least one weight must be positive'
        elif context.get('task_type', '').strip().lower() == 'dmts' and any(v not in (0, 1, 2) for v in values):
            return 'DMTS codes are 1, 2 and 0'
        return ''
    try:
        value = float(text)
    except ValueError:
        return 'Enter a number'
    if not math.isfinite(value):
        return 'Enter a finite number'
    if name in INTEGER and not value.is_integer():
        return 'Enter a whole number'
    if name in POSITIVE and value <= 0:
        return 'Must be greater than 0'
    if name not in SIGNED and value < 0:
        return 'Must be 0 or greater'
    if name in {'reward_go', 'pavlov'} and value > 1:
        return 'Probability must be 0 to 1'
    if name in {'classic_go_sound_id', 'classic_nogo_sound_id'}:
        other = 'classic_nogo_sound_id' if name == 'classic_go_sound_id' else 'classic_go_sound_id'
        try:
            if value == float(context.get(other, '')):
                return 'GO and NoGo IDs must differ'
        except ValueError:
            pass
    if name == 'hit_threshold_s' and value > 100:
        return 'Percentage must be 0 to 100'
    for low, high in [('iti_rand_min_s', 'iti_rand_max_s'),
                      ('left_y_min', 'left_y_max'), ('right_y_min', 'right_y_max')]:
        if name not in (low, high):
            continue
        try:
            lo, hi = float(context.get(low, '')), float(context.get(high, ''))
        except ValueError:
            continue
        if lo > hi or (low != 'iti_rand_min_s' and lo == hi):
            return 'Minimum must be below maximum' if low != 'iti_rand_min_s' else 'ITI min must not exceed max'
    return ''


class ValidatedSettings:
    """Pure state model: invalid drafts never replace active values."""
    def __init__(self):
        self.drafts = {}
        self.active = {}
        self.errors = {}

    def external(self, name, value):
        # Runtime-generated values/protocol defaults remain the source of truth.
        self.drafts[name] = self.active[name] = str(value)

    def edit(self, name, text):
        self.drafts[name] = text
        self.errors = {key: validate_setting(key, value, self.drafts)
                       for key, value in self.drafts.items()}
        for group in GROUPS:
            members = [key for key in group if key in self.drafts]
            if any(self.errors[key] for key in members):
                for key in members:
                    if not self.errors[key] and self.drafts[key] != self.active[key]:
                        self.errors[key] = 'Finish the paired field first'
        for key, value in self.drafts.items():
            if not self.errors[key]:
                self.active[key] = (' '.join(value.replace(',', ' ').replace(';', ' ').split())
                                    if key in {'sequence_values', 'sequence_weights', 'dmts_modality_probabilities'}
                                    else str(int(float(value))) if key in INTEGER and value.strip()
                                    else value)


class EntryValidation:
    def __init__(self):
        self.model = ValidatedSettings()
        self.fields = {}
        self.updating = False

    def add(self, parent, name, source, width=10):
        field = ValidatedEntry(parent, self, name, source, width)
        self.fields[name] = field
        self.model.external(name, source.get())
        self.refresh(name, field.draft.get())
        return field

    def reload_sources(self):
        """Publish an imported batch without writing any old UI values back."""
        self.updating = True
        try:
            for name, field in self.fields.items():
                self.model.external(name, field.source.get())
            for name, field in self.fields.items():
                field.draft.set(self.model.active[name])
            self.model.errors = {
                name: validate_setting(name, value, self.model.drafts)
                for name, value in self.model.drafts.items()
            }
            for name, field in self.fields.items():
                field.show_error(self.model.errors.get(name, ''))
        finally:
            self.updating = False

    def refresh(self, name, text, external=False):
        if self.updating:
            return
        self.updating = True
        try:
            if external:
                # A runtime trace can update a linked field before the original
                # source variable's own validation trace runs. Capture *all*
                # source changes first, rather than writing stale model values
                # back over the outer change (e.g. imported NoGo sound ID).
                for key, field in self.fields.items():
                    current = field.source.get()
                    if key == name or current != self.model.active[key]:
                        self.model.external(key, current)
                        field.draft.set(current)
            self.model.edit(name, text)
            for key, field in self.fields.items():
                value = self.model.active[key]
                if field.source.get() != value:
                    field.source.set(value)
            # Variable traces may update linked controls (GO IDs, task presets).
            for key, field in self.fields.items():
                current = field.source.get()
                if current != self.model.active[key]:
                    self.model.external(key, current)
                    field.draft.set(current)
            for key, field in self.fields.items():
                field.show_error(self.model.errors.get(key, ''))
        finally:
            self.updating = False


class ValidatedEntry(ttk.Frame):
    def __init__(self, parent, manager, name, source, width):
        super().__init__(parent)
        self.manager, self.name, self.source = manager, name, source
        self.draft = tk.StringVar(master=self, value=source.get())
        style = ttk.Style(self)
        style.map('Validated.TEntry', foreground=[('invalid', '#a00000')],
                  fieldbackground=[('invalid', '#ffe5e5')])
        self.entry = ttk.Entry(self, textvariable=self.draft, width=width, style='Validated.TEntry')
        self.entry.grid(row=0, column=0, sticky='ew')
        self.columnconfigure(0, weight=1)
        self.message = ttk.Label(self, foreground='#a00000', wraplength=145, font=('Segoe UI', 8))
        self.draft.trace_add('write', lambda *_: manager.refresh(name, self.draft.get()))
        source.trace_add('write', lambda *_: manager.refresh(name, source.get(), external=True))

    def show_error(self, error):
        self.entry.state(['invalid'] if error else ['!invalid'])
        if error:
            self.message.configure(text=error + '\nLast valid value stays active')
            self.message.grid(row=0, column=1, padx=(5, 0), sticky='w')
        else:
            self.message.grid_remove()
