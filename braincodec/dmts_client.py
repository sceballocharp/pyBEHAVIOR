"""PC-side preparation of DMTS LED pairs, using the existing runner connection."""

import json
import random
import uuid
from urllib import request


class DMTSLightClient:
    def __init__(self, url, library, timeout=2):
        self.url = url.rstrip('/')
        self.library = library
        self.timeout = timeout
        self.session_id = uuid.uuid4().hex
        self.counter = 0
        self.pending = None

    def call(self, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = request.Request(self.url + path, data=data,
                              headers={'Content-Type': 'application/json'})
        with request.urlopen(req, timeout=self.timeout) as response:
            result = json.load(response)
        if not result.get('ok'):
            raise RuntimeError(result.get('error', 'PYNQ request failed'))
        return result['dmts']

    def connect(self):
        status = self.call('/dmts/status')
        if status['fingerprint'] != self.library.fingerprint:
            raise RuntimeError('Uploaded PYNQ YAML differs from the selected local stimulus library')
        self.reset()

    def reset(self):
        self.call('/dmts/reset', {})
        self.pending = None

    def prepare(self, trial_type):
        ids = self.library.ids
        if trial_type == 0:
            sample, test = 0, 0
        else:
            sample = random.choice(ids)
            choices = [value for value in ids if value != sample]
            if trial_type == 2 and not choices:
                raise ValueError('Non-match DMTS requires at least two stimuli')
            test = random.choice(choices) if trial_type == 2 else sample
        self.counter += 1
        pair = {'trial_id': f'{self.session_id}-{self.counter}',
                'sample_id': sample, 'test_id': test,
                'fingerprint': self.library.fingerprint}
        status = self.call('/dmts/prepare', pair)
        if status['phase'] != 'waiting_sample' or status['pair']['trial_id'] != pair['trial_id']:
            raise RuntimeError('PYNQ did not acknowledge the prepared pair')
        self.pending = dict(pair, trial_type=trial_type)
        return self.pending

    def require_phase(self, pair, phase):
        status = self.call('/dmts/status')
        if status['fingerprint'] != self.library.fingerprint or status['pair'] != {
                key: pair[key] for key in ('trial_id', 'sample_id', 'test_id')}:
            raise RuntimeError('PYNQ pair identity changed')
        if status['phase'] != phase:
            raise RuntimeError(f"PYNQ expected {phase}, got {status['phase']}; missing or premature trigger")
        if phase == 'idle' and len(status['presentations']) != 2:
            raise RuntimeError('PYNQ did not complete both presentations')
        return status
