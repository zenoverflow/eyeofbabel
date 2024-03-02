import gc, warnings, torch
from abc import ABC, abstractmethod
import mss, mss.tools
from mss.screenshot import ScreenShot
import easyocr, manga_ocr
from PIL import Image

import app.util.mode as appmode


class ImageReader(ABC):
    @abstractmethod
    def read(self, shot: ScreenShot) -> str | None:
        pass

    @abstractmethod
    def destroy(self) -> None:
        pass


class EasyOCR(ImageReader):
    _reader: easyocr.Reader

    def __init__(self, lang: str) -> None:
        self._reader = easyocr.Reader(
            [lang],
            quantize=False,
            gpu=False,
            verbose=appmode.mode_is_dev(),
        )

    def read(self, shot: ScreenShot) -> str | None:
        try:
            result: list[str] = self._reader.readtext(
                mss.tools.to_png(shot.rgb, shot.size),
                detail=0,
                paragraph=True,
            )
            if not result or not len(result):
                return None
            return result[0]
        except Exception as e:
            print(str(e))
            return None

    def destroy(self):
        self._reader = None
        gc.collect()
        torch.cuda.empty_cache()


class MangaOCR(ImageReader):
    _reader: manga_ocr.MangaOcr

    def __init__(self) -> None:
        if not appmode.mode_is_dev():
            # Gets rid of MangaOCR's warnings.
            warnings.filterwarnings("ignore", category=UserWarning)
            warnings.filterwarnings("ignore", category=FutureWarning)
        self._reader = manga_ocr.MangaOcr(force_cpu=True)

    def read(self, shot: ScreenShot) -> str | None:
        try:
            shot_pil = Image.frombytes(
                "RGB",
                shot.size,
                shot.bgra,
                "raw",
                "BGRX",
            )
            text = self._reader(shot_pil)
            if not text or not len(text):
                return None
            return text
        except Exception as e:
            print(str(e))
            return None

    def destroy(self):
        self._reader = None
        gc.collect()
        torch.cuda.empty_cache()
