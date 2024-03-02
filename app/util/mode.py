import platform, os, sys
from enum import Enum


_FLAG_DEV: bool = False


class PlatformMode(Enum):
    LINUX = 1
    WINDOWS = 2
    DARWIN = 3


def mode_platform():
    match platform.system():
        case "Windows":
            return PlatformMode.WINDOWS
        case "Linux":
            return PlatformMode.LINUX
        case "Darwin":
            return PlatformMode.DARWIN


def app_is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def mode_is_dev() -> bool:
    return _FLAG_DEV


def exec_path():
    if app_is_frozen():
        return os.path.dirname(sys.executable)
    return os.getcwd()
