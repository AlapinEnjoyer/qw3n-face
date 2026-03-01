from nicegui import run, ui

from app.audio.tts import DEFAULT_LANGUAGE, LANGUAGES, engine
from app.ui.layout import generation_error, generation_result, generation_spinner, model_gate, model_status_bar


def voice_design_tab():
    @ui.refreshable
    def content():
        if not engine.is_loaded("voice_design"):
            model_gate("voice_design", on_done=content.refresh)
            return

        model_status_bar("voice_design", on_unload=content.refresh)

        text = (
            ui.textarea(
                label="Text to speak",
                value="Hey! You dropped your notebook? I think it's yours? Maybe?",
            )
            .classes("w-full")
            .props("autogrow rows=3 filled")
        )

        instruct = (
            ui.textarea(
                label="Voice description",
                value="Male, 20 years old, energetic and slightly nervous, clear tenor voice with occasional pitch breaks when excited",
            )
            .classes("w-full")
            .props("autogrow rows=3 filled")
        )

        language = (
            ui.select(
                LANGUAGES,
                value=DEFAULT_LANGUAGE,
                label="Language",
            )
            .classes("w-full")
            .props("filled")
        )

        result_area = ui.column().classes("w-full")

        async def generate():
            if not text.value or not text.value.strip():
                ui.notify("Please enter some text", type="warning")
                return
            if not instruct.value or not instruct.value.strip():
                ui.notify("Please describe the voice you want", type="warning")
                return
            generation_spinner(result_area, "Designing voice...")
            try:
                filename, duration = await run.io_bound(
                    engine.generate_voice_design,
                    text=text.value,
                    language=language.value or DEFAULT_LANGUAGE,
                    instruct=instruct.value,
                )
                result_area.clear()
                with result_area:
                    generation_result(filename, duration)
                ui.notify("Voice designed", type="positive")
            except Exception as e:
                generation_error(result_area, e)

        ui.button("Design Voice", icon="brush", on_click=generate).classes("w-full mt-2").props(
            "color=primary size=md unelevated"
        )

    content()
