import logging

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

DEFAULT_MODEL_SIZE = "small"
DEVICE = "cpu"
COMPUTE_TYPE = "int8"


class Transcriber:
    def __init__(self) -> None:
        self._model: WhisperModel | None = None
        self._model_size: str = DEFAULT_MODEL_SIZE

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def _ensure_loaded(self) -> WhisperModel:
        if self._model is None:
            logger.info("Loading Whisper model '%s' on %s (%s)...", self._model_size, DEVICE, COMPUTE_TYPE)
            self._model = WhisperModel(
                self._model_size,
                device=DEVICE,
                compute_type=COMPUTE_TYPE,
            )
            logger.info("Whisper model loaded.")
        return self._model

    def transcribe(self, audio_path: str) -> tuple[str, str]:
        """Transcribe an audio file and return (text, detected_language).

        The model is loaded on first call and kept in memory for reuse.
        Runs on CPU with int8 quantisation to avoid competing with TTS
        models for GPU/MPS memory.
        """
        model = self._ensure_loaded()
        segments, info = model.transcribe(audio_path, beam_size=5, vad_filter=True)
        text = " ".join(segment.text.strip() for segment in segments)
        return text.strip(), info.language

    def unload(self) -> None:
        if self._model is not None:
            del self._model
            self._model = None
            logger.info("Whisper model unloaded.")


transcriber = Transcriber()
