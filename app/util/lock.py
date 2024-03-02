import os, time, sys

from app.constants import KEY_FILE_LOCK_MAIN


def _read_data() -> tuple[int, int] | None:
    if os.path.isfile(KEY_FILE_LOCK_MAIN):
        with open(KEY_FILE_LOCK_MAIN) as f:
            content = f.read()
        owner, last_beat = [int(l) for l in content.splitlines()]

        return owner, last_beat

    return None


def _heartbeat(own_id: int):
    with open(KEY_FILE_LOCK_MAIN, "w") as f:
        f.write(f"{own_id}\n{int(time.time())}")


def ensure_app_lock(own_id: int) -> bool:
    data = _read_data()

    if data is None:
        _heartbeat(own_id)
        return True

    owner, last_beat = data

    if owner == own_id:
        _heartbeat(own_id)
        return True
    else:
        difference = int(time.time()) - last_beat  # seconds

        if difference > 4:
            _heartbeat(own_id)
            return True

    print("\n\nAnother instance is still active. Closing this in 5s.\n\n")

    time.sleep(5)
    sys.exit(0)
