"""Epistemic enclosure: the experimenter owns every channel the subject can see."""

from importlib.metadata import PackageNotFoundError, version

from enclosure.world import World

__all__ = ["World"]

try:
    __version__ = version("enclosure")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"
