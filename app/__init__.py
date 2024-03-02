import sys

sys.dont_write_bytecode = True
import os

os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import typing as t
from argparse import ArgumentParser
import atexit, subprocess, socket, signal, asyncio, webbrowser, gc

from brutalpywebui import BrutalPyWebUI
from quart import request, Response

from app.util.support_madlad400 import SUPPORT_MADLAD400
from app.util.support_easyocr import SUPPORT_EASYOCR
from app.util.translator import Madlad400Translator
from app.util.assets import read_asset
from app.constants import (
    MSG_DT_NOT_LOADED,
    MSG_DT_LOADING,
    MSG_DT_LOADED,
)
from app.desktop_reader import reader_run
import app.desktop_reader.pipe as DT
import app.util.mode as appmode
from app.util.lock import ensure_app_lock


SUPPORT_NVIDIA = appmode.mode_platform() == appmode.PlatformMode.LINUX

SUPPORT_TRANSLATION: dict[str, tuple[str, str]] = {
    "zenoverflow/madlad400-3b-mt-int8-float32": (
        "Madlad400 3B MT BT",
        (
            "Best for casual use, lower accuracy,"
            " run on GPU if speed is important to you."
            " Requires only ~3.5GB of RAM (or VRAM on GPU)."
        ),
    ),
    "zenoverflow/madlad400-7b-mt-bt-ct2-int8-float16": (
        "Madlad400 7B MT BT",
        (
            "Balanced, much better accuracy,"
            " run on GPU if speed is important to you."
            " Requires ~8.5GB of RAM (or VRAM on GPU)."
        ),
    ),
    "zenoverflow/madlad400-10b-mt-ct2-int8-float16": (
        "Madlad400 10B MT",
        (
            "Most accurate, best for more serious use cases,"
            " highly recommended to run on GPU."
            " Requires ~10GB of RAM (or VRAM on GPU)."
        ),
    ),
}

TRANSLATION_MODELS: list[str] = [k for k in SUPPORT_TRANSLATION.keys()]


class AppState:
    ui_rendered_once: bool = False

    browser_opened: bool = False

    app_url: str | None = None

    opt_dt_append = False

    opt_dt_auto = False

    opt_dt_reader = "easyocr"

    opt_dt_lang = "ja"

    opt_tr_model_variant = "zenoverflow/madlad400-3b-mt-int8-float32"

    opt_tr_nvidia: bool = False

    translator: Madlad400Translator

    process_desktop: subprocess.Popen | None = None

    last_dt_status: str = MSG_DT_NOT_LOADED

    have_desktop_bbox: bool = False

    def __init__(
        self,
        model: str,
        run_on_nvidia: bool = False,
    ) -> None:
        DT.cleanup()

        self.opt_tr_model_variant = model
        self.opt_tr_nvidia = bool(SUPPORT_NVIDIA and run_on_nvidia)

        # reg cleanup
        atexit.register(lambda: self.destroy())
        # ready. now load translator model.
        print(
            (
                "\n\nChecking if translation model is"
                " downloaded and downloading as necessary.\n\n"
            )
        )
        self.translator = Madlad400Translator(
            variant=model,
            run_on_nvidia=bool(SUPPORT_NVIDIA and run_on_nvidia),
        )

    def destroy(self):
        try:
            self.handler_desktop_stop()
        except Exception as e:
            print(str(e))

    def handler_desktop_stop(self) -> None:
        if self.process_desktop is None:
            return

        try:
            self.process_desktop.send_signal(signal.SIGINT)
            self.process_desktop.wait(timeout=3)
            self.process_desktop = None
        except Exception as e:
            print(str(e))
            try:
                self.process_desktop.kill()
                self.process_desktop = None
                DT.set_status(MSG_DT_NOT_LOADED)
            except Exception as e:
                print(str(e))

    def handler_desktop_run(self) -> None:
        self.handler_desktop_stop()

        DT.set_status(MSG_DT_LOADING)

        base_args: list[str] = [
            "python",
            os.path.join(appmode.exec_path(), "app.py"),
        ]

        if appmode.app_is_frozen():
            match appmode.mode_platform():
                case appmode.PlatformMode.WINDOWS:
                    base_args = [
                        os.path.join(appmode.exec_path(), "app.exe"),
                    ]
                case appmode.PlatformMode.LINUX:
                    base_args = [
                        os.path.join(appmode.exec_path(), "app"),
                    ]
                case appmode.PlatformMode.DARWIN:
                    base_args = [
                        os.path.join(appmode.exec_path(), "app"),
                    ]
                case _:
                    pass

        self.process_desktop = subprocess.Popen(
            [
                *base_args,
                "-a",
                str(os.getpid()),
                "-r",
                STATE.opt_dt_reader,
                "-l",
                STATE.opt_dt_lang,
            ]
        )


STATE: AppState | None = None

WUI: BrutalPyWebUI | None = None


def _bind_to_port(port: int = 7865):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("localhost", port))
        result = s.getsockname()[1]
    return result


def find_free_port(default: int = 7865):
    port = default
    while True:
        try:
            port = _bind_to_port(port)
            break
        except Exception as e:
            if appmode.mode_is_dev():
                print(str(e))
            port = 0
    return port


async def use_disabled_ui(func: t.Awaitable):
    await WUI.el_disable(
        [
            "button, input, select, textarea:not(#txt_result)",
        ]
    )
    await func()
    await WUI.el_enable(
        [
            "button, input, select, textarea:not(#txt_result)",
        ]
    )


async def notification_show(text: str):
    target = ["#bg_process_info"]
    await WUI.el_set_text(target, text)
    await WUI.el_set_style(target, "display", "block")


async def notification_hide():
    target = ["#bg_process_info"]
    await WUI.el_set_style(target, "display", "none")
    await WUI.el_set_text(target, "")


async def update_dt_controls():
    if STATE.process_desktop is None:
        await WUI.el_set_style(["#btn_dt_start"], "display", "inline-block")
        await WUI.el_set_style(["#btn_dt_stop"], "display", "none")
        await WUI.el_set_style(["#btn_dt_restart"], "display", "none")
        DT.set_status(MSG_DT_NOT_LOADED)
    else:
        await WUI.el_set_style(["#btn_dt_start"], "display", "none")
        await WUI.el_set_style(["#btn_dt_stop"], "display", "inline-block")
        await WUI.el_set_style(["#btn_dt_restart"], "display", "inline-block")


async def handler_translate(text: str, lang_to: str = "en"):
    try:
        text = text.strip()

        if len(text) == 0:
            result = ""
        else:
            result = STATE.translator.translate(text, target_lang=lang_to)

        await WUI.el_set_value(["#txt_result"], result)
    except Exception as e:
        print(str(e))


async def update_active_tab(name: str):
    match name:
        case "translate":
            await WUI.el_set_style(["#view_translate"], "display", "flex")
            await WUI.el_set_style(["#view_screen_capture"], "display", "none")

            await WUI.el_class_add(["#nav_tab_translate"], "active")
            await WUI.el_class_remove(["#nav_tab_screen_capture"], "active")

        case "screen_capture":
            await WUI.el_set_style(["#view_screen_capture"], "display", "flex")
            await WUI.el_set_style(["#view_translate"], "display", "none")

            await WUI.el_class_remove(["#nav_tab_translate"], "active")
            await WUI.el_class_add(["#nav_tab_screen_capture"], "active")

        case _:
            pass


async def render_tabs():
    LANGS_EASYOCR_KEYS_SORTED = [k for k in SUPPORT_EASYOCR.keys()]
    LANGS_EASYOCR_KEYS_SORTED.sort()

    LANGS_MADLAD400_KEYS_SORTED = [k for k in SUPPORT_MADLAD400.keys()]
    LANGS_MADLAD400_KEYS_SORTED.sort()

    LANGS_EASYOCR = [(k, SUPPORT_EASYOCR[k]) for k in LANGS_EASYOCR_KEYS_SORTED]
    LANGS_MADLAD400 = [(k, SUPPORT_MADLAD400[k]) for k in LANGS_MADLAD400_KEYS_SORTED]

    await WUI.el_set_html_templ(
        ["#view_translate"],
        read_asset("view_translate.j2"),
        langs_madlad400=LANGS_MADLAD400,
        have_desktop_bbox=STATE.have_desktop_bbox,
        models=TRANSLATION_MODELS,
        models_info=SUPPORT_TRANSLATION,
        opt_tr_model_variant=STATE.opt_tr_model_variant,
        opt_tr_nvidia=STATE.opt_tr_nvidia,
        can_use_nvidia=SUPPORT_NVIDIA,
    )
    await WUI.el_set_html_templ(
        ["#view_screen_capture"],
        read_asset("view_screen_capture.j2"),
        langs_easyocr=LANGS_EASYOCR,
        opt_dt_lang=STATE.opt_dt_lang,
        opt_dt_reader=STATE.opt_dt_reader,
        opt_dt_append=STATE.opt_dt_append,
        opt_dt_auto=STATE.opt_dt_auto,
        stat_dt_module=STATE.last_dt_status,
        dt_running=STATE.process_desktop is not None,
    )
    await update_active_tab("translate")


async def render_init():
    await WUI.el_set_html_templ(["body"], read_asset("base.j2"))
    await render_tabs()
    STATE.ui_rendered_once = True


async def handler_event(event: str, data: list):
    try:
        event = event.strip()
        match event:
            case "set_opt_dt_append":
                STATE.opt_dt_append = data[0]

            case "set_opt_dt_auto":
                STATE.opt_dt_auto = data[0]

            case "set_opt_dt_reader":
                STATE.opt_dt_reader = data[0]

            case "set_opt_dt_lang":
                STATE.opt_dt_lang = data[0]

            case "set_model":

                async def _f():
                    await notification_show(
                        "Ensuring translation model is downloaded and loading."
                    )
                    STATE.translator.destroy()
                    STATE.translator = None
                    gc.collect()
                    STATE.opt_tr_model_variant = data[0]
                    STATE.opt_tr_nvidia = bool(SUPPORT_NVIDIA and data[1])
                    STATE.translator = Madlad400Translator(
                        variant=data[0],
                        run_on_nvidia=bool(SUPPORT_NVIDIA and data[1]),
                    )
                    await notification_hide()

                await use_disabled_ui(_f)

            case "translate":

                async def _f():
                    return await handler_translate(text=data[0], lang_to=data[1])

                await use_disabled_ui(_f)

            case "recapture":

                async def _f():
                    DT.signal_recapture()

                await use_disabled_ui(_f)

            case "select_view":
                await update_active_tab(name=data[0])

            case "dt_run":

                async def _f():
                    STATE.handler_desktop_run()
                    await notification_show(
                        "Ensuring reader model is downloaded and loading."
                    )
                    while (
                        STATE.process_desktop is not None
                        and STATE.process_desktop.poll() is None
                        and STATE.last_dt_status != MSG_DT_LOADED
                    ):
                        await asyncio.sleep(1)
                    await update_dt_controls()
                    await notification_hide()

                await use_disabled_ui(_f)

            case "dt_stop":
                STATE.have_desktop_bbox = False
                await WUI.el_set_style(["#btn_recapture"], "display", "none")

                async def _f():
                    STATE.handler_desktop_stop()
                    await update_dt_controls()

                await use_disabled_ui(_f)

            case _:
                pass
    except Exception as e:
        print(str(e))


async def handler_background():
    try:
        ensure_app_lock(os.getpid())

        if STATE.process_desktop is not None:
            if STATE.process_desktop.poll() is not None:
                STATE.process_desktop = None
                await update_dt_controls()

        if not STATE.browser_opened:
            STATE.browser_opened = True
            await asyncio.sleep(2)
            webbrowser.open(STATE.app_url)

        if not STATE.ui_rendered_once:
            return

        v_status = DT.get_status()
        v_capture = DT.get_capture()

        if v_status is not None and len(v_status) >= 1:
            STATE.last_dt_status = v_status
            await WUI.el_set_text(["#stat_dt_module"], v_status)

        if v_capture is not None and len(v_capture) >= 1:
            if not STATE.have_desktop_bbox:
                STATE.have_desktop_bbox = True
                await WUI.el_set_style(["#btn_recapture"], "display", "block")
            if STATE.opt_dt_append:
                await WUI.el_append_value(["#txt_source"], v_capture)
            else:
                await WUI.el_set_value(["#txt_source"], v_capture)
            if STATE.opt_dt_auto:
                args = (
                    "["  # same args and event as the view template
                    "_wuiVal('#txt_source'),"
                    "_wuiVal('#sel_target_lang')"
                    "]"
                )
                await WUI.pg_eval(f"_wuiEvent('translate', {args})")
    except Exception as e:
        if appmode.mode_is_dev():
            print(e)


def app_run(port: int, model: str, run_on_nvidia: bool = False):
    global WUI
    global STATE

    STATE = AppState(
        model=model,
        run_on_nvidia=bool(SUPPORT_NVIDIA and run_on_nvidia),
    )

    WUI = BrutalPyWebUI(
        page_title="Eye of Babel",
        init_handler=render_init,
        event_handler=handler_event,
        base_css=lambda: read_asset("base.css"),
        background_handler=handler_background,
        background_interval=0.3,
        debug=appmode.mode_is_dev(),
    )

    @WUI._app.route("/api", methods=["POST"])
    async def _api():
        try:
            data: dict = await request.get_json()

            text, lang_to = data.get("text", None), data.get("lang_to", "en")

            if text is None or not len(text):
                return Response("Bad request.", status=400)

            if lang_to not in [k for k in SUPPORT_MADLAD400.keys()]:
                return Response(
                    f"Language {lang_to} is not supported.",
                    status=400,
                )

            result = STATE.translator.translate(text, target_lang=lang_to)

            return Response(result)
        except Exception as e:
            if appmode.mode_is_dev():
                print(e)
            return Response("Bad request.", status=400)

    try:
        STATE.app_url = f"http://localhost:{port}"
        print(f"\n\nStarting on {STATE.app_url}\n\n")
        WUI.run(port=port)
    except Exception as e:
        print(e)
        sys.exit(1)


def entrypoint():
    arg_parser = ArgumentParser()
    arg_parser.add_argument(
        "-p",
        "--port",
        help="port for the core module ui",
        required=False,
        default=int(os.getenv("PORT", 11537)),
        type=int,
    )
    arg_parser.add_argument(
        "-m",
        "--model",
        help="the default translation model size to load",
        required=False,
        default=3,
        type=int,
        choices=[3, 7, 10],
    )
    arg_parser.add_argument(
        "-n",
        "--nvidia",
        help="run the model on an nvidia gpu",
        required=False,
        default=False,
        action="store_true",
    )
    arg_parser.add_argument(
        "-d",
        "--debug",
        help="INTERNAL. DO NOT USE. Run in debug mode.",
        action="store_true",
        required=False,
        default=False,
    )
    arg_parser.add_argument(
        "-a",
        "--parent",
        help="INTERNAL. DO NOT USE. Parent process id for connecting desktop module.",
        required=False,
        default=-1,
        type=int,
    )
    arg_parser.add_argument(
        "-r",
        "--reader",
        help="INTERNAL. DO NOT USE. Reader for processing images",
        required=False,
        default="easyocr",
        choices=["easyocr", "mangaocr"],
    )
    arg_parser.add_argument(
        "-l",
        "--lang",
        help="INTERNAL. DO NOT USE. Language setting for the reader",
        required=False,
        default="ja",
        choices=[k for k in SUPPORT_MADLAD400.keys()],
    )
    args = arg_parser.parse_args(sys.argv[1:])

    appmode._FLAG_DEV = args.debug

    # core entrypoint and lock
    if args.parent == -1:
        ensure_app_lock(os.getpid())
        match args.model:
            case 3:
                model = "zenoverflow/madlad400-3b-mt-int8-float32"
            case 7:
                model = "zenoverflow/madlad400-7b-mt-bt-ct2-int8-float16"
            case 10:
                model = "zenoverflow/madlad400-10b-mt-ct2-int8-float16"
        app_run(
            port=args.port,
            model=model,
            run_on_nvidia=bool(SUPPORT_NVIDIA and args.nvidia),
        )
    # desktop reader entrypoint
    else:
        ensure_app_lock(args.parent)
        reader_run(reader=args.reader, lang=args.lang)
