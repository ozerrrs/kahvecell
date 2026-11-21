"""Basit yapılandırılmış (key=value) loglama."""

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        'time=%(asctime)s level=%(levelname)s logger=%(name)s msg="%(message)s"'
    ))
    root = logging.getLogger("kahvecell")
    root.handlers = [handler]
    root.setLevel(level)
    root.propagate = False
