import gc
from pynput import keyboard, mouse


class Hotkeys:
    ev_create: tuple[int, int] | None = None

    _listener_hotkeys: keyboard.GlobalHotKeys

    def __init__(self) -> None:
        # TODO: let user select one of multiple sets of hotkeys
        self._listener_hotkeys = keyboard.GlobalHotKeys(
            {
                "<alt>+`": lambda: self._handle_trigger(),
            },
        )

        self._listener_hotkeys.start()

    def destroy(self):
        self._listener_hotkeys.stop()

    def _handle_trigger(self):
        temp_c = mouse.Controller()
        x, y = temp_c.position
        self.ev_create = (x, y)
        del temp_c
        gc.collect()
