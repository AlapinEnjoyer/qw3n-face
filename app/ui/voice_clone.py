from nicegui import events, run, ui

from app.audio.transcribe import transcriber
from app.audio.tts import DEFAULT_LANGUAGE, LANGUAGES, engine
from app.config import UPLOAD_DIR
from app.ui.layout import generation_error, generation_result, generation_spinner, model_gate, model_status_bar


def voice_clone_tab():
    @ui.refreshable
    def content():
        if not engine.is_loaded("voice_clone"):
            model_gate("voice_clone", on_done=content.refresh)
            return

        model_status_bar("voice_clone", on_unload=content.refresh)

        ref_audio_path: dict[str, str] = {"value": ""}

        with (
            ui.card()
            .classes("w-full border border-dashed border-stone-400 dark:border-stone-600")
            .props("flat")
            .style("background: rgba(100, 76, 210, 0.05)")
        ):
            with ui.column().classes("w-full items-center gap-2 py-2"):
                ui.icon("mic").classes("text-3xl text-primary")
                ui.label("Reference Audio").classes("font-medium text-stone-700 dark:text-stone-300")
                upload_label = ui.label("Upload a short audio clip (3-10s recommended)").classes(
                    "text-xs text-stone-500"
                )

                async def handle_upload(e: events.UploadEventArguments):
                    save_path = UPLOAD_DIR / e.file.name
                    await e.file.save(save_path)
                    ref_audio_path["value"] = str(save_path)
                    upload_label.text = f"Uploaded: {e.file.name}"
                    ui.notify(f"Uploaded {e.file.name}", type="positive")

                ui.upload(
                    on_upload=handle_upload,
                    auto_upload=True,
                    max_file_size=50_000_000,
                ).classes("max-w-sm").props("accept=audio/* flat bordered color=primary")

        with ui.row().classes("w-full items-end gap-2"):
            ref_text = (
                ui.input(
                    label="Reference transcript",
                    placeholder="Transcript of the reference audio",
                )
                .classes("flex-grow")
                .props("filled")
            )

            async def auto_transcribe():
                if not ref_audio_path["value"]:
                    ui.notify("Upload a reference audio clip first", type="warning")
                    return
                transcribe_btn.props("loading")
                try:
                    text_result, lang = await run.io_bound(
                        transcriber.transcribe,
                        ref_audio_path["value"],
                    )
                    ref_text.value = text_result
                    ui.notify(f"Transcribed ({lang})", type="positive")
                except Exception as exc:
                    ui.notify(f"Transcription failed: {exc}", type="negative")
                finally:
                    transcribe_btn.props(remove="loading")

            transcribe_btn = (
                ui.button(icon="auto_fix_high", on_click=auto_transcribe)
                .props("flat round color=primary")
                .tooltip("Auto-transcribe uploaded audio")
            )

        ui.separator().classes("my-1")

        text = (
            ui.textarea(
                label="Text to synthesize",
                value="I am solving the equation: what is the meaning of life? Nobody can answer that.",
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
            if not ref_audio_path["value"]:
                ui.notify("Please upload a reference audio clip", type="warning")
                return
            if not ref_text.value or not ref_text.value.strip():
                ui.notify("Please provide a transcript for the reference audio", type="warning")
                return
            if not text.value or not text.value.strip():
                ui.notify("Please enter text to synthesize", type="warning")
                return
            generation_spinner(result_area, "Cloning voice...")
            try:
                filename, duration = await run.io_bound(
                    engine.generate_voice_clone,
                    text=text.value,
                    language=language.value or DEFAULT_LANGUAGE,
                    ref_audio=ref_audio_path["value"],
                    ref_text=ref_text.value,
                )
                result_area.clear()
                with result_area:
                    generation_result(filename, duration)
                ui.notify("Voice cloned", type="positive")
            except Exception as e:
                generation_error(result_area, e)

        ui.button("Clone Voice", icon="content_copy", on_click=generate).classes("w-full mt-2").props(
            "color=primary size=md unelevated"
        )

    content()
