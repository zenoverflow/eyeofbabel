import sys

sys.dont_write_bytecode = True
import atexit

from app.constants import (
    MSG_DT_LOADING,
    MSG_DT_LOADED,
    MSG_DT_NOT_LOADED,
)
from app.desktop_reader.screen_reader import ScreenReader
import app.desktop_reader.pipe as DT
from app.util.reader import EasyOCR, MangaOCR

# from app.util.mode import mode_is_dev


def reader_run(reader: str, lang: str):
    DT.set_status(MSG_DT_LOADING)

    match reader:
        case "easyocr":
            image_reader = EasyOCR(lang)
        case "mangaocr":
            image_reader = MangaOCR()
        case _:
            raise Exception(f"Invalid reader backend {reader}.")

    module_desktop = ScreenReader(image_reader)

    DT.set_status(MSG_DT_LOADED)

    def cleanup():
        module_desktop.destroy()
        DT.set_status(MSG_DT_NOT_LOADED)

    atexit.register(cleanup)

    try:
        while not module_desktop.destroyed:
            module_desktop.loop()
    except:
        pass
        # if mode_is_dev():
        #     print(e)
