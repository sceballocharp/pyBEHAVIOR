"""Small, atomically saved history of acquisition sessions."""

import json
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4


class SessionHistory:
    def __init__(self, path):
        self.path = Path(path)
        self.session_id = None

    def start(self, user, animal_id, project, simulation=False, sound_ids=None):
        self.session_id = str(uuid4())
        self.entry = {
            'session_id': self.session_id,
            'user': user,
            'animal_id': animal_id,
            'project': project,
            'sound_ids': sorted(set(int(value) for value in (sound_ids or []) if int(value) > 0)),
            'started_at': datetime.now().astimezone().isoformat(timespec='seconds'),
            'stopped_at': None,
            'status': 'running',
            'simulation': bool(simulation),
            'trials': 0,
            'rewards': 0,
        }
        self.update(0, 0)

    def update(self, trials, rewards, stopped=False, weights=None):
        if self.session_id is None:
            return
        entries = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else []
        if not isinstance(entries, list) or any(not isinstance(row, dict) for row in entries):
            raise ValueError('Session history must contain a JSON list of session objects')
        self.entry.update(trials=int(trials), rewards=int(rewards))
        if stopped:
            if weights is not None:
                self.entry['weights'] = weights
            self.entry.update(status='stopped', stopped_at=datetime.now().astimezone().isoformat(timespec='seconds'))
        entries = [row for row in entries if row.get('session_id') != self.session_id]
        entries.append(dict(self.entry))
        temporary = self.path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        os.replace(temporary, self.path)
        if stopped:
            self.session_id = None
