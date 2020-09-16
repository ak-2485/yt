import logging
import sys

from yt.config import ytcfg

# This next bit is grabbed from:
# http://stackoverflow.com/questions/384076/how-can-i-make-the-python-logging-output-to-be-colored


def add_coloring_to_emit_ansi(fn):
    # add methods we need to the class
    def new(*args):
        levelno = args[0].levelno
        if levelno >= 50:
            color = "\x1b[31m"  # red
        elif levelno >= 40:
            color = "\x1b[31m"  # red
        elif levelno >= 30:
            color = "\x1b[33m"  # yellow
        elif levelno >= 20:
            color = "\x1b[32m"  # green
        elif levelno >= 10:
            color = "\x1b[35m"  # pink
        else:
            color = "\x1b[0m"  # normal
        ln = color + args[0].levelname + "\x1b[0m"
        args[0].levelname = ln
        return fn(*args)

    return new


def set_log_level(level):
    """
    Select which minimal logging level should be displayed.

    Parameters
    ----------
    level: int or str
        Possible values by increasing level:
        0 or "notset"
        1 or "all"
        10 or "debug"
        20 or "info"
        30 or "warning"
        40 or "error"
        50 or "critical"
    """
    # this is a user-facing interface to avoid importing from yt.utilities in user code.

    if isinstance(level, str):
        level = level.upper()

    if level == "ALL":  # non-standard alias
        level = 1
    ytLogger.setLevel(level)
    ytLogger.debug("Set log level to %d", level)


ufstring = "%(name)-3s: [%(levelname)-9s] %(asctime)s %(message)s"
cfstring = "%(name)-3s: [%(levelname)-18s] %(asctime)s %(message)s"

if ytcfg.getboolean("yt", "stdoutStreamLogging"):
    stream = sys.stdout
else:
    stream = sys.stderr

ytLogger = logging.getLogger("yt")


class DuplicateFilter(logging.Filter):
    """A filter that removes duplicated successive log entries."""

    # source
    # https://stackoverflow.com/questions/44691558/suppress-multiple-messages-with-same-content-in-python-logging-module-aka-log-co  # noqa
    def filter(self, record):
        current_log = (record.module, record.levelno, record.msg)
        if current_log != getattr(self, "last_log", None):
            self.last_log = current_log
            return True
        return False


ytLogger.addFilter(DuplicateFilter())


def disable_stream_logging():
    if len(ytLogger.handlers) > 0:
        ytLogger.removeHandler(ytLogger.handlers[0])
    h = logging.NullHandler()
    ytLogger.addHandler(h)


def colorize_logging():
    f = logging.Formatter(cfstring)
    ytLogger.handlers[0].setFormatter(f)
    yt_sh.emit = add_coloring_to_emit_ansi(yt_sh.emit)


def uncolorize_logging():
    try:
        f = logging.Formatter(ufstring)
        ytLogger.handlers[0].setFormatter(f)
        yt_sh.emit = original_emitter
    except NameError:
        # yt_sh and original_emitter are not defined because
        # suppressStreamLogging is True, so we continue since there is nothing
        # to uncolorize
        pass


_level = min(max(ytcfg.getint("yt", "loglevel"), 0), 50)

if ytcfg.getboolean("yt", "suppressStreamLogging"):
    disable_stream_logging()
else:
    yt_sh = logging.StreamHandler(stream=stream)
    # create formatter and add it to the handlers
    formatter = logging.Formatter(ufstring)
    yt_sh.setFormatter(formatter)
    # add the handler to the logger
    ytLogger.addHandler(yt_sh)
    set_log_level(_level)
    ytLogger.propagate = False

    original_emitter = yt_sh.emit

    if ytcfg.getboolean("yt", "coloredlogs"):
        colorize_logging()
