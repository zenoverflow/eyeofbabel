import os

from app.util.mode import exec_path


def read_asset(name: str) -> str | None:
    path = os.path.join(exec_path(), "assets", name)

    if not os.path.isfile(path):
        raise Exception("Could not find asset " + name)

    with open(path, "r") as f:
        result = f.read()

    return result
