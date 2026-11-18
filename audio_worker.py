"""Single-owner, cancellable audio playback without Tk or acquisition calls."""
from dataclasses import dataclass, field
import queue
import threading
import time
from uuid import uuid4


class AudioBusyError(RuntimeError):
    pass


@dataclass(frozen=True)
class AudioJob:
    signal: object
    rate: int
    device: str = 'Dev1'
    simulation: bool = False
    token: str = field(default_factory=lambda: str(uuid4()))


def play_audio(job, cancel, started):
    """Only the audio thread creates, polls, stops and closes its output task."""
    if job.simulation:
        started(time.perf_counter())
        cancel.wait(len(job.signal) / job.rate)
        return
    try:
        import nidaqmx
    except ImportError:
        nidaqmx = None
    if nidaqmx is not None:
        from nidaqmx.constants import AcquisitionType
        task = nidaqmx.Task()
        was_started = False
        try:
            task.ao_channels.add_ao_voltage_chan(f'{job.device}/ao0')
            task.timing.cfg_samp_clk_timing(job.rate, sample_mode=AcquisitionType.FINITE,
                                           samps_per_chan=len(job.signal))
            task.write(job.signal.tolist(), auto_start=False)
            if cancel.is_set():
                return
            task.start()
            was_started = True
            started(time.perf_counter())
            deadline = time.perf_counter() + max(2.0, len(job.signal) / job.rate + 1.0)
            while not cancel.is_set() and not task.is_task_done():
                if time.perf_counter() >= deadline:
                    raise TimeoutError('Audio output did not finish')
                cancel.wait(0.01)
            task.stop()
        finally:
            try:
                task.close()
            finally:
                # AO can retain its last sample after cancellation or a fault.
                if was_started:
                    with nidaqmx.Task() as reset:
                        reset.ao_channels.add_ao_voltage_chan(f'{job.device}/ao0')
                        reset.write(0.0)
        return
    import sounddevice as sd
    try:
        stream = sd.get_stream()
    except RuntimeError:
        stream = None
    if stream is not None and stream.active:
        raise AudioBusyError('Another sound is already playing')
    if cancel.is_set():
        return
    sd.play(job.signal, job.rate, blocking=False)
    started(time.perf_counter())
    try:
        while sd.get_stream().active and not cancel.wait(0.01):
            pass
        if cancel.is_set():
            sd.stop()
        else:
            sd.wait()  # Collect playback/backend errors after the stream ends.
    finally:
        if cancel.is_set():
            sd.stop()


class AudioWorker:
    def __init__(self, player=play_audio, output_lock=None):
        self.events = queue.Queue()
        self._jobs = queue.Queue()
        self._cancel = threading.Event()
        self._idle = threading.Event()
        self._idle.set()
        self._state_lock = threading.Lock()
        self._output_lock = output_lock if output_lock is not None else threading.Lock()
        self._player = player
        self._busy = False
        self._closed = False
        self._thread = threading.Thread(target=self._run, name='pyBEHAVIOR-audio', daemon=True)
        self._thread.start()

    @property
    def busy(self):
        with self._state_lock:
            return self._busy

    @property
    def closed(self):
        with self._state_lock:
            return self._closed

    def is_alive(self):
        return self._thread.is_alive()

    def submit(self, job):
        with self._state_lock:
            if self._closed:
                raise RuntimeError('Audio worker is stopping')
            if self._busy:
                raise AudioBusyError('Audio already pending/playing; request rejected instead of delayed')
            if job.rate <= 0 or not len(job.signal):
                raise ValueError('Audio must have a positive rate and nonempty waveform')
            self._idle.clear()
            self._busy = True
            self._jobs.put(job)
        return job.token

    def wait_idle(self, timeout=None):
        return self._idle.wait(timeout)

    def request_stop(self):
        with self._state_lock:
            if not self._closed:
                self._closed = True
                self._cancel.set()
                self._jobs.put(None)

    def stop(self, timeout=2):
        self.request_stop()
        self._thread.join(timeout)
        return not self.is_alive()

    def _run(self):
        while True:
            job = self._jobs.get()
            if job is None:
                return
            start = None
            acquired = False

            def started(timestamp):
                nonlocal start
                start = timestamp
                self.events.put({'kind': 'started', 'token': job.token, 'started_at': start})

            try:
                if not self._cancel.is_set():
                    acquired = self._output_lock.acquire(blocking=False)
                    if not acquired:
                        raise AudioBusyError('Audio output is occupied; playback was not delayed')
                    self._player(job, self._cancel, started)
                    if start is None and not self._cancel.is_set():
                        raise RuntimeError('Audio backend did not report a playback start')
                event = {'kind': 'finished', 'token': job.token, 'started_at': start,
                         'ended_at': time.perf_counter(),
                         'status': 'cancelled' if self._cancel.is_set() else 'completed'}
            except Exception as exc:
                event = {'kind': 'finished', 'token': job.token, 'started_at': start,
                         'ended_at': time.perf_counter(), 'status': 'error',
                         'error': f'{type(exc).__name__}: {exc}'}
            finally:
                if acquired:
                    self._output_lock.release()
            # Publish completion before releasing busy, so the caller can drain
            # the end timestamp before deciding whether another trial may start.
            self.events.put(event)
            with self._state_lock:
                self._busy = False
                self._idle.set()
