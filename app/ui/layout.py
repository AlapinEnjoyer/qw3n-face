from collections.abc import Callable
from typing import Any

from nicegui import app as nicegui_app
from nicegui import run, ui

from app.audio.tts import MODEL_IDS, MODEL_LABELS, engine, is_model_cached
from app.config import OUTPUT_DIR
from app.ui.events import model_changed


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
                model_changed.emit(model_key)
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
            model_changed.emit(model_key)
            on_unload()

        btn = ui.button("Unload", icon="eject", on_click=unload).props("flat dense color=negative size=sm")


##########################################################################
# Sampling parameter defaults (same as _merge_generate_kwargs of qwen-tts)
##########################################################################

SAMPLING_DEFAULTS: dict[str, Any] = {
    "temperature": 0.9,
    "top_p": 1.0,
    "top_k": 50,
    "max_new_tokens": 2048,
    "repetition_penalty": 1.05,
    "subtalker_temperature": 0.9,
    "subtalker_top_p": 1.0,
    "subtalker_top_k": 50,
}


def sampling_controls() -> Callable[[], dict[str, Any]]:
    """Render a collapsible sampling-parameters panel.

    Returns a callable that produces the current parameter values as a
    ``dict`` suitable for ``**kwargs`` forwarding to the TTS engine.
    """

    # Main parameters
    with ui.row().classes("w-full gap-3 flex-wrap"):
        temperature = (
            ui.number(
                label="Temperature",
                value=SAMPLING_DEFAULTS["temperature"],
                min=0.01,
                max=2.0,
                step=0.01,
                format="%.2f",
            )
            .classes("flex-1 min-w-36")
            .props("filled dense")
        )
        temperature.tooltip("Sampling temperature — higher values produce more varied speech")

        top_p = (
            ui.number(
                label="Top P",
                value=SAMPLING_DEFAULTS["top_p"],
                min=0.0,
                max=1.0,
                step=0.01,
                format="%.2f",
            )
            .classes("flex-1 min-w-36")
            .props("filled dense")
        )
        top_p.tooltip("Nucleus sampling — cumulative probability cutoff")

        top_k = (
            ui.number(
                label="Top K",
                value=SAMPLING_DEFAULTS["top_k"],
                min=0,
                max=500,
                step=1,
            )
            .classes("flex-1 min-w-36")
            .props("filled dense")
        )
        top_k.tooltip("Top-K sampling — number of highest-probability tokens to keep")

    with ui.row().classes("w-full gap-3 flex-wrap"):
        max_new_tokens = (
            ui.number(
                label="Max New Tokens",
                value=SAMPLING_DEFAULTS["max_new_tokens"],
                min=128,
                max=8192,
                step=128,
            )
            .classes("flex-1 min-w-36")
            .props("filled dense")
        )
        max_new_tokens.tooltip("Maximum number of codec tokens to generate")

        repetition_penalty = (
            ui.number(
                label="Repetition Penalty",
                value=SAMPLING_DEFAULTS["repetition_penalty"],
                min=1.0,
                max=2.0,
                step=0.01,
                format="%.2f",
            )
            .classes("flex-1 min-w-36")
            .props("filled dense")
        )
        repetition_penalty.tooltip("Penalty applied to repeated tokens — higher reduces repetition")

    # Subtalker parameters (nested expansion)
    with ui.expansion("Subtalker Parameters").classes("w-full").props("dense header-class=text-xs"):
        ui.label(
            "Controls the sub-codec generation stage of the 12 Hz tokenizer. "
            "Only change these if you know what you are doing."
        ).classes("text-xs text-stone-400 mb-2")

        with ui.row().classes("w-full gap-3 flex-wrap"):
            sub_temperature = (
                ui.number(
                    label="Subtalker Temperature",
                    value=SAMPLING_DEFAULTS["subtalker_temperature"],
                    min=0.01,
                    max=2.0,
                    step=0.01,
                    format="%.2f",
                )
                .classes("flex-1 min-w-36")
                .props("filled dense")
            )

            sub_top_p = (
                ui.number(
                    label="Subtalker Top P",
                    value=SAMPLING_DEFAULTS["subtalker_top_p"],
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    format="%.2f",
                )
                .classes("flex-1 min-w-36")
                .props("filled dense")
            )

            sub_top_k = (
                ui.number(
                    label="Subtalker Top K",
                    value=SAMPLING_DEFAULTS["subtalker_top_k"],
                    min=0,
                    max=500,
                    step=1,
                )
                .classes("flex-1 min-w-36")
                .props("filled dense")
            )

    # Reset button
    all_controls = {
        "temperature": temperature,
        "top_p": top_p,
        "top_k": top_k,
        "max_new_tokens": max_new_tokens,
        "repetition_penalty": repetition_penalty,
        "subtalker_temperature": sub_temperature,
        "subtalker_top_p": sub_top_p,
        "subtalker_top_k": sub_top_k,
    }

    def _reset():
        for key, ctrl in all_controls.items():
            ctrl.value = SAMPLING_DEFAULTS[key]
        ui.notify("Reset to defaults", type="info")

    with ui.row().classes("w-full justify-end"):
        ui.button("Reset to defaults", icon="restart_alt", on_click=_reset).props("flat dense color=primary size=sm")

    def get_kwargs() -> dict[str, Any]:
        return {key: ctrl.value for key, ctrl in all_controls.items()}

    return get_kwargs
