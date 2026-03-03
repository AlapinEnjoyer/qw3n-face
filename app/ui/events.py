from nicegui import Event

# Fired whenever a persona is created, updated or deleted.
# Subscribers (e.g. custom_voice persona_actions) should refresh their UI.
personas_changed: Event = Event()

# Fired whenever a TTS model is loaded or unloaded.
# Payload is the model key (str), e.g. "custom_voice".
# Subscribers (e.g. batch content) should re-check engine state.
model_changed: Event[str] = Event()
