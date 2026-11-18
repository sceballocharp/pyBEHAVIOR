"""Run the normal v8 app with persistent Python/native crash diagnostics."""
import contextlib
from datetime import datetime
import faulthandler
import os
from pathlib import Path
import platform
import socket
import sys
import threading
import traceback


def main(check_only=False):
    folder = Path(__file__).resolve().parent / 'diagnostics'
    folder.mkdir(exist_ok=True)
    name = f"pybehavior_{socket.gethostname()}_{datetime.now():%Y%m%d_%H%M%S}_{os.getpid()}.log"
    path = folder / name
    print(f'Diagnostic log: {path}', flush=True)
    with path.open('a', encoding='utf-8', buffering=1) as log:
        # Keep an OS descriptor open until process termination so a Tcl/native
        # crash during interpreter shutdown is captured too.
        native_fd = os.open(path, os.O_WRONLY | os.O_APPEND)
        faulthandler.enable(file=native_fd, all_threads=True)
        try:
            with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                print(f'START {datetime.now().astimezone().isoformat()} pid={os.getpid()}', flush=True)
                print(f'Python {sys.version}\nPlatform {platform.platform()}', flush=True)

                def thread_error(args):
                    print(f'UNCAUGHT THREAD ERROR: {args.thread.name}', flush=True)
                    traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback)
                    log.flush()

                previous_hook = threading.excepthook
                threading.excepthook = thread_error
                try:
                    if check_only:
                        print('DIAGNOSTIC CHECK: logging and native traceback writer', flush=True)
                        faulthandler.dump_traceback(file=native_fd, all_threads=True)
                        print('DIAGNOSTIC CHECK PASSED (no GUI or hardware started)', flush=True)
                        return 0
                    from pyBEHAVIOR_v8 import BehaviorAcquisitionApp

                    class DiagnosticApp(BehaviorAcquisitionApp):
                        def log(self, message):
                            print(f'{datetime.now():%H:%M:%S.%f} [{threading.current_thread().name}] {message}', flush=True)
                            super().log(message)

                        def report_callback_exception(self, exc_type, exc_value, exc_traceback):
                            print('TK CALLBACK ERROR', flush=True)
                            traceback.print_exception(exc_type, exc_value, exc_traceback)
                            log.flush()

                        def update_gonogo_smart_task(self):
                            before = getattr(self, '_smart_gonogo_phase', 'idle')
                            try:
                                super().update_gonogo_smart_task()
                            except BaseException:
                                print(f'SMARTTASK ERROR phase={before} rows={len(self.trial_rows)}', flush=True)
                                traceback.print_exc()
                                raise
                            after = getattr(self, '_smart_gonogo_phase', 'idle')
                            if before != after:
                                print(f'SMARTTASK TRANSITION {before} -> {after}; rows={len(self.trial_rows)}; '
                                      f'target={getattr(self, "_smart_gonogo_target", None)}; '
                                      f'thread={threading.current_thread().name}', flush=True)

                    app = DiagnosticApp()
                    app.protocol('WM_DELETE_WINDOW', app.on_close)
                    app.mainloop()
                    print('NORMAL GUI EXIT', flush=True)
                except BaseException:
                    print('TOP-LEVEL ERROR', flush=True)
                    traceback.print_exc()
                    return 1
                finally:
                    threading.excepthook = previous_hook
        finally:
            log.flush()
    print(f'Diagnostic session finished. Log: {path}', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main(check_only='--check' in sys.argv[1:]))
