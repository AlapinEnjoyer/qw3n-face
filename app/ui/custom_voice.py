from nicegui import run, ui

from app.audio.personas import Persona, now_iso, persona_store
from app.audio.tts import DEFAULT_LANGUAGE, DEFAULT_SPEAKER, LANGUAGES, SPEAKER_INFO, SPEAKERS, engine
from app.ui.events import personas_changed
from app.ui.layout import generation_error, generation_result, generation_spinner, model_gate, model_status_bar


def custom_voice_tab():
    @ui.refreshable
    def content():
        if not engine.is_loaded("custom_voice"):
            model_gate("custom_voice", on_done=content.refresh)
            return

        model_status_bar("custom_voice", on_unload=content.refresh)

        text = (
            ui.textarea(
                label="Text to speak",
                value="Hello! I am so excited to meet you today. This is going to be amazing!",
            )
            .classes("w-full")
            .props("autogrow rows=3 filled")
        )

        with ui.row().classes("w-full gap-4 flex-wrap"):
            with ui.column().classes("flex-1 min-w-48 gap-2"):
                with (
                    ui.select(
                        SPEAKERS,
                        value=DEFAULT_SPEAKER,
                        label="Speaker",
                    )
                    .classes("w-full")
                    .props("filled") as speaker
                ):
                    speaker_tooltip = ui.tooltip(
                        f"{SPEAKER_INFO[DEFAULT_SPEAKER]['desc']} — {SPEAKER_INFO[DEFAULT_SPEAKER]['lang']}"
                    )

                def _update_info(e):
                    info = SPEAKER_INFO.get(e.value, {})
                    speaker_tooltip.set_text(f"{info.get('desc', '')} — {info.get('lang', '')}")

                speaker.on_value_change(_update_info)

            with ui.column().classes("flex-1 min-w-48 gap-2"):
                language = (
                    ui.select(
                        LANGUAGES,
                        value=DEFAULT_LANGUAGE,
                        label="Language",
                    )
                    .classes("w-full")
                    .props("filled")
                )

        instruct = (
            ui.input(
                label="Instruction (optional)",
                placeholder="e.g. Speak with excitement and joy",
            )
            .classes("w-full")
            .props("filled")
        )

        result_area = ui.column().classes("w-full")

        async def generate():
            if not text.value or not text.value.strip():
                ui.notify("Please enter some text", type="warning")
                return
            generation_spinner(result_area, "Generating speech...")
            try:
                filename, duration = await run.io_bound(
                    engine.generate_custom_voice,
                    text=text.value,
                    language=language.value or DEFAULT_LANGUAGE,
                    speaker=speaker.value or DEFAULT_SPEAKER,
                    instruct=instruct.value or "",
                )
                result_area.clear()
                with result_area:
                    generation_result(filename, duration)
                ui.notify("Speech generated", type="positive")
            except Exception as e:
                generation_error(result_area, e)

        async def _save_as_persona_dialog():
            with ui.dialog() as dlg, ui.card().classes("px-6 py-5 gap-4 min-w-72"):
                ui.label("Save as Persona").classes("text-lg font-semibold text-stone-700 dark:text-stone-200")
                name_input = ui.input(label="Name", placeholder="e.g. Ryan Energetic").classes("w-full").props("filled")
                with ui.row().classes("justify-end gap-2 w-full"):
                    ui.button("Cancel", on_click=dlg.close).props("flat")

                    def _save():
                        name = name_input.value.strip()
                        if not name:
                            ui.notify("Enter a name", type="warning")
                            return
                        persona_store.save(
                            Persona(
                                name=name,
                                speaker=speaker.value or DEFAULT_SPEAKER,
                                language=language.value or DEFAULT_LANGUAGE,
                                instruct=instruct.value or "",
                                created_at=now_iso(),
                            )
                        )
                        ui.notify(f"Saved '{name}'", type="positive")
                        dlg.close()
                        persona_actions.refresh()
                        personas_changed.emit()

                    ui.button("Save", icon="save", on_click=_save).props("color=primary unelevated")
            dlg.open()

        @ui.refreshable
        def persona_actions():
            personas = persona_store.all()
            if personas:
                persona_sel = (
                    ui.select(
                        [p.name for p in personas],
                        label="Load persona",
                    )
                    .classes("w-40")
                    .props("dense filled")
                )

                def _load_persona():
                    p = persona_store.get(persona_sel.value or "")
                    if p:
                        speaker.set_value(p.speaker)
                        language.set_value(p.language)
                        instruct.set_value(p.instruct)
                        ui.notify(f"Loaded '{p.name}'", type="positive")

                ui.button(icon="file_upload", on_click=_load_persona).props("flat dense color=primary").tooltip(
                    "Load persona"
                )

            ui.button(icon="bookmarks", on_click=_save_as_persona_dialog).props("flat dense color=primary").tooltip(
                "Save as persona"
            )

        with ui.row().classes("w-full items-center gap-2 mt-2"):
            ui.button("Generate Speech", icon="play_arrow", on_click=generate).classes("flex-1").props(
                "color=primary size=md unelevated"
            )
            persona_actions()

        # Refresh persona selector when personas change in the personas tab
        personas_changed.subscribe(persona_actions.refresh)

    content()
