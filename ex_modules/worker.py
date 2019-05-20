from PyQt5.QtCore import QObject, pyqtSignal, QRunnable
import traceback
import sys


class WorkerSignals(QObject):
    error = pyqtSignal(tuple)
    progress = pyqtSignal(str)
    result = pyqtSignal(object)
    finished = pyqtSignal()
    progress_bar = pyqtSignal(str, int)


class Worker(QRunnable):
    def __init__(self, func=None, *args, **kwargs):
        super(Worker, self).__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.kwargs['progress_callback'] = self.signals.progress
        self.kwargs['bar_callback'] = self.signals.progress_bar

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
            self.signals.finished.emit()

