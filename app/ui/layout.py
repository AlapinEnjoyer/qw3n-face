from collections.abc import Callable

from nicegui import app as nicegui_app
from nicegui import run, ui

from app.audio.tts import MODEL_IDS, MODEL_LABELS, engine, is_model_cached
from app.config import OUTPUT_DIR


def header():
    with (
        ui.header()
        .classes("px-6 py-3 items-center")
        .style("background: #644cd2; border-bottom: 1px solid rgba(255, 255, 255, 0.10);")
    ):
        with ui.row().classes("items-center gap-3 w-full"):
            ui.icon("record_voice_over").classes("text-3xl text-white/80")
            ui.label("Qw3n Face").classes("text-2xl font-extrabold tracking-tight text-white")
            ui.space()
            dark = ui.dark_mode(False)
            ui.button(icon="dark_mode", on_click=dark.toggle).props("flat round color=white size=sm")

            async def _confirm_quit():
                with ui.dialog() as dlg, ui.card().classes("px-6 py-5 gap-4"):
                    ui.label("Close application?").classes("text-lg font-semibold text-stone-700 dark:text-stone-200")
                    ui.label("This will stop the server and close the app.").classes("text-sm text-stone-500")
                    cleanup = ui.checkbox("Delete generated output files").props("color=negative")
                    with ui.row().classes("justify-end gap-2 w-full"):
                        ui.button("Cancel", on_click=dlg.close).props("flat")

                        def _shutdown():
                            if cleanup.value:
                                for f in OUTPUT_DIR.iterdir():
                                    if f.is_file():
                                        f.unlink(missing_ok=True)
                            nicegui_app.shutdown()

                        ui.button(
                            "Close",
                            icon="power_settings_new",
                            on_click=_shutdown,
                        ).props("color=negative unelevated")
                dlg.open()

            ui.button(icon="power_settings_new", on_click=_confirm_quit).props(
                "flat round color=white size=sm"
            ).tooltip("Close app")


def empty_state(message: str) -> None:
    with ui.row().classes("w-full justify-center py-8"):
        ui.label(message).classes("text-sm text-stone-400")


def generation_spinner(result_area, message: str) -> None:
    result_area.clear()
    with result_area:
        with ui.row().classes("w-full justify-center py-8"):
            ui.spinner("dots", size="xl", color="primary")
            ui.label(message).classes("text-stone-400 ml-3")


def generation_error(result_area, error: Exception) -> None:
    result_area.clear()
    with result_area:
        ui.label(f"Error: {error}").classes("text-red-500")
    ui.notify(str(error), type="negative")


def generation_result(filename: str, duration: float):
    with ui.column().classes("w-full items-center gap-3 mt-2"):
        ui.audio(f"/outputs/{filename}").classes("w-full max-w-lg")
        with ui.row().classes("items-center gap-4 text-sm text-stone-500"):
            ui.icon("timer").classes("text-base")
            ui.label(f"{duration:.1f}s")
            ui.icon("audio_file").classes("text-base")
            ui.label(filename)
        ui.button(
            "Download",
            icon="download",
            on_click=lambda: ui.download(f"/outputs/{filename}"),
        ).props("flat color=primary size=sm")


def model_gate(model_key: str, on_done: Callable) -> None:
    cached = is_model_cached(model_key)
    label = MODEL_LABELS[model_key]
    model_id = MODEL_IDS[model_key]

    with ui.column().classes("w-full items-center py-10 gap-4"):
        if cached:
            ui.icon("memory").classes("text-5xl text-stone-400")
            ui.label("Model downloaded but not loaded").classes(
                "text-lg font-semibold text-stone-600 dark:text-stone-300"
            )
            ui.label(label).classes("text-sm text-stone-500 font-mono")
            action_text = "Load Model"
            action_icon = "play_arrow"
            status_msg = "Loading model into memory..."
        else:
            ui.icon("cloud_download").classes("text-5xl text-stone-400")
            ui.label("Model not downloaded").classes("text-lg font-semibold text-stone-600 dark:text-stone-300")
            ui.label(label).classes("text-sm text-stone-500 font-mono")
            ui.label(model_id).classes("text-xs text-stone-400 font-mono")
            action_text = "Download & Load"
            action_icon = "download"
            status_msg = "Downloading & loading model..."

        status_row = ui.row().classes("items-center gap-2")
        status_row.set_visibility(False)
        with status_row:
            ui.spinner("dots", size="md", color="primary")
            status_label = ui.label(status_msg).classes("text-sm text-stone-500")

        async def start_load():
            btn.set_visibility(False)
            status_row.set_visibility(True)
            try:
                await run.io_bound(engine.load_model, model_key)
                ui.notify(f"{label} ready", type="positive")
                on_done()
            except Exception as e:
                status_label.text = f"Failed: {e}"
                btn.set_visibility(True)
                status_row.set_visibility(False)
                ui.notify(str(e), type="negative")

        btn = ui.button(action_text, icon=action_icon, on_click=start_load).props("color=primary unelevated")


def model_status_bar(model_key: str, on_unload: Callable) -> None:
    """Thin status bar shown at the top of a tab when its model is loaded."""
    label = MODEL_LABELS[model_key]

    with (
        ui.row()
        .classes("w-full items-center justify-between px-3 py-1 rounded-lg mb-3")
        .style("background: rgba(100, 76, 210, 0.08)")
    ):
        with ui.row().classes("items-center gap-2"):
            ui.icon("memory").classes("text-base text-primary")
            ui.label(f"{label} loaded").classes("text-sm text-stone-500")

        spinner = ui.spinner("dots", size="sm", color="primary")
        spinner.set_visibility(False)

        async def unload():
            btn.set_visibility(False)
            spinner.set_visibility(True)
            await run.io_bound(engine.unload_model, model_key)
            ui.notify(f"{label} unloaded", type="info")
            on_unload()

        btn = ui.button("Unload", icon="eject", on_click=unload).props("flat dense color=negative size=sm")
