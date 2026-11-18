"""Logging setup shared by the CLI and the library code."""

import logging

_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once, with one consistent format."""
    logging.basicConfig(level=level.upper(), format=_FORMAT)
