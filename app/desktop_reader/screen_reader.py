import PySimpleGUI as sg

from app.desktop_reader.screen_capture import ScreenCapture
import app.desktop_reader.pipe as DT

from app.util.reader import ImageReader
from app.util.mode import mode_is_dev


class ScreenReader:
    destroyed: bool = False

    _screen_capture: ScreenCapture

    _focus_keeper: sg.Window

    def __init__(
        self,
        image_reader: ImageReader,
    ) -> None:
        self._screen_capture = ScreenCapture(
            image_reader=image_reader,
        )
        self._focus_keeper = sg.Window(
            "",
            [[]],
            finalize=True,
            alpha_channel=0,
            size=(0, 0),
            keep_on_top=True,
            resizable=False,
            no_titlebar=True,
            location=(0, 0),
            disable_close=True,
        )
        self._focus_keeper.force_focus()

    def destroy(self):
        try:
            self.destroyed = True
            self._screen_capture.destroy()
            self._focus_keeper.close()
            self._screen_capture = None
            self._focus_keeper = None
        except Exception as e:
            if mode_is_dev():
                print(e)

    def loop(self):
        try:
            result = self._screen_capture.loop()

            if result is None and DT.detect_recapture():
                result = self._screen_capture.read_last_bbox()

            if result is not None:
                DT.set_capture(result)
        except Exception as e:
            if mode_is_dev():
                print(e)
