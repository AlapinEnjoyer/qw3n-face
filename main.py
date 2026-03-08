from nicegui import app, ui

from app.config import OUTPUT_DIR
from app.ui.batch import batch_tab
from app.ui.custom_voice import custom_voice_tab
from app.ui.layout import header
from app.ui.personas import personas_tab
from app.ui.voice_clone import voice_clone_tab
from app.ui.voice_design import voice_design_tab

app.add_media_files("/outputs", str(OUTPUT_DIR))

app.colors(
    primary="#644cd2",
    secondary="#c6b8dc",
    accent="#4b39a1",
    dark="#1a1625",
    dark_page="#0f0d14",
    positive="#4caf50",
    negative="#f44336",
    info="#2196f3",
    warning="#ff9800",
)


@ui.page("/")
def index():
    ui.add_css("""
        .q-tab-panel { padding: 16px 0 !important; }
        .q-tab__label { text-transform: none !important; font-weight: 600; }
    """)

    header()

    with ui.column().classes("w-full max-w-2xl mx-auto px-4 py-6 gap-0"):
        with (
            ui.tabs()
            .classes("w-full")
            .props("dense active-color=primary indicator-color=primary align=justify") as tabs
        ):
            ui.tab("custom", label="Custom Voice", icon="person")
            ui.tab("design", label="Voice Design", icon="brush")
            ui.tab("clone", label="Voice Clone", icon="content_copy")
            ui.tab("batch", label="Batch", icon="format_list_bulleted")
            ui.tab("personas", label="Personas", icon="bookmarks")

        with ui.tab_panels(tabs, value="custom").classes("w-full"):
            with ui.tab_panel("custom").classes("gap-3"):
                custom_voice_tab()

            with ui.tab_panel("design").classes("gap-3"):
                voice_design_tab()

            with ui.tab_panel("clone").classes("gap-3"):
                voice_clone_tab()

            with ui.tab_panel("batch").classes("gap-3"):
                batch_tab()

            with ui.tab_panel("personas").classes("gap-3"):
                personas_tab()


ui.run(
    title="Qw3n Face",
    dark=False,
    storage_secret="qw3n-face-secret",
    port=8080,
    reload=True,
)
