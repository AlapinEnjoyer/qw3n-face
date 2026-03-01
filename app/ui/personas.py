from nicegui import ui

from app.audio.personas import Persona, now_iso, persona_store
from app.audio.tts import DEFAULT_LANGUAGE, DEFAULT_SPEAKER, LANGUAGES, SPEAKERS
from app.ui.layout import empty_state


def _chip(icon: str, text: str) -> None:
    with ui.row().classes("items-center gap-1"):
        ui.icon(icon).classes("text-xs text-primary")
        ui.label(text).classes("text-xs text-stone-500")


def personas_tab():
    @ui.refreshable
    def persona_list():
        personas = persona_store.all()

        if not personas:
            empty_state("No saved personas yet.")
            return

        ui.label(f"Saved ({len(personas)})").classes("text-xs font-semibold text-stone-500 uppercase tracking-wide")

        for p in personas:
            with ui.card().classes("w-full").props("flat bordered").style("background: rgba(100, 76, 210, 0.04)"):
                with ui.row().classes("w-full items-start justify-between gap-2"):
                    with ui.column().classes("gap-1 flex-1"):
                        ui.label(p.name).classes("font-semibold text-stone-700 dark:text-stone-200")
                        with ui.row().classes("items-center gap-3 flex-wrap"):
                            _chip("person", p.speaker)
                            _chip("language", p.language)
                        if p.instruct:
                            ui.label(f'"{p.instruct}"').classes("text-xs text-stone-400 italic")
                        ui.label(p.created_at).classes("text-xs text-stone-300 dark:text-stone-600")

                    def _delete(name=p.name):
                        persona_store.delete(name)
                        ui.notify(f"Deleted '{name}'", type="info")
                        persona_list.refresh()

                    ui.button(icon="delete", on_click=_delete).props("flat round dense color=negative size=sm")

    with ui.card().classes("w-full").props("flat bordered").style("background: rgba(100, 76, 210, 0.06)"):
        ui.label("New Persona").classes("text-sm font-semibold text-stone-600 dark:text-stone-300")

        name_input = ui.input(label="Name", placeholder="e.g. Ryan Energetic").classes("w-full").props("filled")

        with ui.row().classes("w-full gap-3"):
            speaker_sel = ui.select(SPEAKERS, value=DEFAULT_SPEAKER, label="Speaker").classes("flex-1").props("filled")
            language_sel = (
                ui.select(LANGUAGES, value=DEFAULT_LANGUAGE, label="Language").classes("flex-1").props("filled")
            )

        instruct_input = (
            ui.input(
                label="Instruction (optional)",
                placeholder="e.g. Speak with excitement and joy",
            )
            .classes("w-full")
            .props("filled")
        )

        def save_persona():
            name = name_input.value.strip()
            if not name:
                ui.notify("Enter a name for this persona", type="warning")
                return
            persona_store.save(
                Persona(
                    name=name,
                    speaker=speaker_sel.value or DEFAULT_SPEAKER,
                    language=language_sel.value or DEFAULT_LANGUAGE,
                    instruct=instruct_input.value or "",
                    created_at=now_iso(),
                )
            )
            ui.notify(f"Saved '{name}'", type="positive")
            name_input.set_value("")
            instruct_input.set_value("")
            persona_list.refresh()

        ui.button("Save Persona", icon="save", on_click=save_persona).props("color=primary unelevated")

    ui.separator().classes("my-1")

    persona_list()
