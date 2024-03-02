import PySimpleGUI as sg
import mss, mss.tools, mss.screenshot
from pynput import mouse

from app.util.hotkeys import Hotkeys
from app.util.mode import mode_is_dev

from app.util.reader import (
    ImageReader,
    EasyOCR,
)


class ScreenCapture:
    _image_reader: ImageReader

    _trigger_listener: Hotkeys

    _mouse_listener: mouse.Listener | None = None

    _rect_reader: sg.Window | None = None

    _rect_overlay: sg.Window | None = None

    _last_bbox: tuple[int, int, int, int] | None = None

    _last_mouse: tuple[int, int] | None = None

    _ev_take: tuple[int, int] | None = None

    _ev_close: bool = False

    def __init__(
        self,
        image_reader: ImageReader | None = None,
    ) -> None:
        self._image_reader = image_reader if image_reader is not None else EasyOCR("ja")
        self._trigger_listener = Hotkeys()

    def destroy(self):
        if self is None:
            return
        self._reader_cleanup()
        self._trigger_listener.destroy()
        self._image_reader.destroy()

    def _attempt_reader_init(self) -> None:
        if self._trigger_listener.ev_create is None:
            return

        # Prevent flow overlap
        if self._rect_overlay is not None or self._rect_reader is not None:
            self._trigger_listener.ev_create = None
            return

        x, y = self._trigger_listener.ev_create
        self._trigger_listener.ev_create = None

        def on_mouse_move(x: int, y: int):
            self._last_mouse = (x, y)

        def on_mouse_click(x: int, y: int, button: mouse.Button, pressed: bool):
            if not pressed:
                match button.name:
                    case "left":
                        self._ev_take = (x, y)
                        return False  # stop listener
                    case "right":
                        self._ev_take = None
                        self._ev_close = True
                        return False  # stop listener

        self._mouse_listener = mouse.Listener(
            on_move=on_mouse_move,
            on_click=on_mouse_click,
        )
        self._mouse_listener.start()

        self._rect_overlay = sg.Window(
            "",
            [[]],
            finalize=True,
            alpha_channel=0.1,
            background_color="black",
            keep_on_top=True,
            resizable=True,
            no_titlebar=True,
            disable_close=True,
        )
        self._rect_overlay.maximize()

        self._rect_reader = sg.Window(
            "",
            [[]],
            finalize=True,
            alpha_channel=0.4,
            size=(1, 1),
            background_color="yellow",
            keep_on_top=True,
            resizable=True,
            no_titlebar=True,
            location=(x, y),
            disable_close=True,
        )

    def _reader_cleanup(self) -> None:
        if self is None:
            return

        if self._mouse_listener is not None:
            try:
                self._mouse_listener.stop()
            except Exception as e:
                if mode_is_dev():
                    print(str(e))

        self._mouse_listener = None
        self._last_mouse = None
        self._ev_take = None
        self._ev_close = False

        if self._rect_overlay is not None:
            self._rect_overlay.size = (0, 0)
            self._rect_overlay.move(0, 0)
            self._rect_overlay.refresh()
            self._rect_overlay.close()
            self._rect_overlay = None

        if self._rect_reader is not None:
            self._rect_reader.size = (0, 0)
            self._rect_reader.move(0, 0)
            self._rect_reader.refresh()
            self._rect_reader.close()
            self._rect_reader = None

    def _capture_move(self) -> None:
        try:
            if self._last_mouse is None:
                return

            x, y = self._last_mouse

            reader_x, reader_y = self._rect_reader.current_location()

            width = x - reader_x
            height = y - reader_y

            if width < 1:
                width = 1
            if height < 1:
                height = 1

            self._rect_reader.size = (width + 1, height + 1)
            self._rect_reader.refresh()
        except Exception as e:
            print(str(e))

    def _capture_take(self) -> str | None:
        try:
            if self._ev_take is None:
                return

            x, y = self._ev_take

            reader_x, reader_y = self._rect_reader.current_location()

            self._reader_cleanup()

            self._last_bbox = (reader_x, reader_y, x, y)

            return self.read_last_bbox()
        except Exception as e:
            print(str(e))
            return None

    def read_last_bbox(self) -> str | None:
        try:
            if not self._last_bbox:
                return None

            top_x, top_y, bot_x, bot_y = self._last_bbox

            # if mode_is_dev():
            #     print(f"BBOX {self._last_bbox}")

            if (bot_x <= top_x) or (bot_y <= top_y):
                return None

            with mss.mss() as sct:
                result_img = sct.grab(self._last_bbox)

            return self._image_reader.read(result_img)
        except Exception as e:
            print(e)
            return None

    def loop(self):
        if self is None:
            return None

        self._attempt_reader_init()

        if not (self._rect_overlay and self._rect_reader and self._mouse_listener):
            return None

        self._capture_move()

        if self._ev_close:
            self._reader_cleanup()
            return None

        if self._ev_take is not None:
            return self._capture_take()

        return None
