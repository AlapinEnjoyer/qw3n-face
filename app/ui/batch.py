from nicegui import run, ui

from app.audio.personas import persona_store
from app.audio.tts import LANGUAGES, SPEAKERS, BatchItem, engine
from app.ui.events import model_changed, personas_changed
from app.ui.layout import empty_state, generation_result, model_gate, model_status_bar, sampling_controls


def batch_tab():
    # Defined outside the refreshable so items survive model load/unload cycles
    batch_items: list[BatchItem] = []

    @ui.refreshable
    def content():
        if not engine.is_loaded("custom_voice"):
            model_gate("custom_voice", on_done=content.refresh)
            return

        model_status_bar("custom_voice", on_unload=content.refresh)

        @ui.refreshable
        def items_editor():
            if not batch_items:
                empty_state("No items yet — add one below.")
                return

            personas = persona_store.all()
            for idx, item in enumerate(batch_items):
                with ui.card().classes("w-full gap-2").props("flat bordered"):
                    with ui.row().classes("w-full items-center justify-between"):
                        ui.label(f"#{idx + 1}").classes("text-xs font-semibold text-stone-500")
                        with ui.row().classes("items-center gap-1"):
                            if personas:

                                def _load_persona(e, i=idx):
                                    p = persona_store.get(str(e.value))
                                    if p:
                                        batch_items[i].speaker = p.speaker
                                        batch_items[i].language = p.language
                                        batch_items[i].instruct = p.instruct
                                        items_editor.refresh()

                                ui.select(
                                    [p.name for p in personas],
                                    label="Load persona",
                                    on_change=_load_persona,
                                ).classes("w-36").props("dense filled")

                            def _remove(i=idx):
                                batch_items.pop(i)
                                items_editor.refresh()

                            ui.button(icon="delete", on_click=_remove).props("flat round dense color=negative size=sm")

                    ui.textarea(label="Text to speak").classes("w-full").props("autogrow rows=2 filled").bind_value(
                        item, "text"
                    )

                    with ui.row().classes("w-full gap-3"):
                        ui.select(SPEAKERS, label="Speaker").classes("flex-1").props("filled dense").bind_value(
                            item, "speaker"
                        )

                        ui.select(LANGUAGES, label="Language").classes("flex-1").props("filled dense").bind_value(
                            item, "language"
                        )

                    ui.input(
                        label="Instruction (optional)",
                        placeholder="e.g. Speak with excitement",
                    ).classes("w-full").props("filled dense").bind_value(item, "instruct")

        items_editor()

        with ui.expansion("Sampling Parameters", icon="tune").classes("w-full").props("dense header-class=text-sm"):
            get_sampling_kwargs = sampling_controls("custom_voice")

        async def generate_all():
            sampling_kwargs = get_sampling_kwargs()
            snapshot = [
                BatchItem(
                    text=i.text,
                    speaker=i.speaker,
                    language=i.language,
                    instruct=i.instruct,
                )
                for i in batch_items
            ]
            valid = [(idx, item) for idx, item in enumerate(snapshot) if item.text.strip()]

            if not valid:
                ui.notify("Add items with text to generate", type="warning")
                return

            # generate_btn, add_btn, results_area are defined below in content()
            # and captured here as free variablesm, they exist before first click
            generate_btn.set_visibility(False)
            add_btn.props(add="disabled")

            results_area.clear()
            row_refs: list[dict] = []

            with results_area:
                with ui.row().classes("w-full items-center gap-2 mb-1"):
                    ui.icon("format_list_bulleted").classes("text-primary text-base")
                    progress_label = ui.label(f"0 / {len(valid)} complete").classes(
                        "text-sm font-semibold text-stone-600 dark:text-stone-300"
                    )

                for orig_idx, item in valid:
                    with ui.card().classes("w-full gap-1").props("flat bordered"):
                        with ui.row().classes("w-full items-center gap-2"):
                            icon_pending = ui.icon("radio_button_unchecked").classes("text-stone-300 text-sm flex-none")
                            icon_running = ui.spinner("dots", size="xs", color="primary")
                            icon_success = ui.icon("check_circle").classes("text-positive text-sm flex-none")
                            icon_err = ui.icon("error").classes("text-negative text-sm flex-none")
                            icon_running.set_visibility(False)
                            icon_success.set_visibility(False)
                            icon_err.set_visibility(False)

                            preview = item.text[:60] + "…" if len(item.text) > 60 else item.text
                            ui.label(f"#{orig_idx + 1}  {item.speaker}  —  {preview}").classes(
                                "flex-1 text-xs text-stone-500"
                            )

                        error_label = ui.label("").classes("text-red-500 text-xs")
                        error_label.set_visibility(False)
                        audio_col = ui.column().classes("w-full")

                        row_refs.append(
                            {
                                "pending": icon_pending,
                                "running": icon_running,
                                "success": icon_success,
                                "err_icon": icon_err,
                                "err_label": error_label,
                                "audio": audio_col,
                            }
                        )

            success_count = 0
            for i, (_orig_idx, item) in enumerate(valid):
                ref = row_refs[i]
                ref["pending"].set_visibility(False)
                ref["running"].set_visibility(True)
                progress_label.text = f"{i} / {len(valid)} complete"

                try:
                    filename, duration = await run.io_bound(engine.generate_batch_item, item, **sampling_kwargs)
                    ref["running"].set_visibility(False)
                    ref["success"].set_visibility(True)
                    with ref["audio"]:
                        generation_result(filename, duration)
                    success_count += 1
                except Exception as e:
                    ref["running"].set_visibility(False)
                    ref["err_icon"].set_visibility(True)
                    ref["err_label"].text = str(e)
                    ref["err_label"].set_visibility(True)

                progress_label.text = f"{i + 1} / {len(valid)} complete"

            notify_type = "positive" if success_count == len(valid) else "warning"
            ui.notify(
                f"Batch done: {success_count}/{len(valid)} succeeded",
                type=notify_type,
            )
            generate_btn.set_visibility(True)
            add_btn.props(remove="disabled")

        with ui.row().classes("w-full items-center justify-between mt-1"):
            add_btn = ui.button(
                "Add Item",
                icon="add",
                on_click=lambda: (
                    batch_items.append(BatchItem(text="")),
                    items_editor.refresh(),
                ),
            ).props("flat color=primary size=sm")

            generate_btn = ui.button(
                "Generate All",
                icon="play_arrow",
                on_click=generate_all,
            ).props("color=primary size=md unelevated")

        # Results are updated in place during generation
        results_area = ui.column().classes("w-full gap-2 mt-2")

    # Re render when the custom_voice model is loaded/unloaded in another tab
    model_changed.subscribe(lambda: content.refresh())
    # Re render persona selectors when personas change in the personas tab
    personas_changed.subscribe(content.refresh)

    content()
