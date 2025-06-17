import logging
import time


class EpochFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        return str(int(time.time() * 1000))
