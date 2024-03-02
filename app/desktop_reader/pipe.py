import os

from app.constants import KEY_FILE_RECAPTURE
import app.util.mode as appmode


def _mk_datafile_path(name: str) -> str:
    return os.path.join(appmode.exec_path(), f"dt_{name}.txt")


def cleanup():
    for data_name in ("status", "capture"):
        fpath = _mk_datafile_path(data_name)
        if os.path.isfile(fpath):
            os.remove(fpath)
    if os.path.isfile(KEY_FILE_RECAPTURE):
        os.remove(KEY_FILE_RECAPTURE)


def _setter(key: str, value: str) -> None:
    try:
        with open(_mk_datafile_path(key), "w") as f:
            f.write(value)
    except Exception as e:
        if appmode.mode_is_dev():
            print(e)


def _getter(key: str) -> str | None:
    try:
        fpath = _mk_datafile_path(key)
        if os.path.isfile(fpath):
            with open(fpath) as f:
                value = f.read()
            os.remove(fpath)
            return value
    except Exception as e:
        if appmode.mode_is_dev():
            print(e)
        return None


def set_status(txt: str) -> None:
    _setter("status", txt)


def set_capture(txt: str) -> None:
    _setter("capture", txt)


def signal_recapture() -> None:
    with open(KEY_FILE_RECAPTURE, "w") as f:
        f.write("")


def get_status() -> str | None:
    return _getter("status")


def get_capture() -> str | None:
    return _getter("capture")


def detect_recapture() -> bool:
    if os.path.isfile(KEY_FILE_RECAPTURE):
        os.remove(KEY_FILE_RECAPTURE)
        return True
    return False
