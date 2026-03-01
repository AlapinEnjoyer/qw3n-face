import gc
import platform
import time
import uuid
from dataclasses import dataclass
from typing import Any

import soundfile as sf
import torch
from huggingface_hub import snapshot_download

from app.config import OUTPUT_DIR

SPEAKERS = [
    "Vivian",
    "Serena",
    "Uncle_Fu",
    "Dylan",
    "Eric",
    "Ryan",
    "Aiden",
    "Ono_Anna",
    "Sohee",
]

LANGUAGES = [
    "Auto",
    "Chinese",
    "English",
    "Japanese",
    "Korean",
    "German",
    "French",
    "Russian",
    "Portuguese",
    "Spanish",
    "Italian",
]

SPEAKER_INFO = {
    "Vivian": {"desc": "Bright, slightly edgy young female", "lang": "Chinese"},
    "Serena": {"desc": "Warm, gentle young female", "lang": "Chinese"},
    "Uncle_Fu": {"desc": "Seasoned male, low mellow timbre", "lang": "Chinese"},
    "Dylan": {
        "desc": "Youthful Beijing male, clear natural",
        "lang": "Chinese (Beijing)",
    },
    "Eric": {
        "desc": "Lively Chengdu male, slightly husky",
        "lang": "Chinese (Sichuan)",
    },
    "Ryan": {"desc": "Dynamic male, strong rhythmic drive", "lang": "English"},
    "Aiden": {"desc": "Sunny American male, clear midrange", "lang": "English"},
    "Ono_Anna": {"desc": "Playful Japanese female, light nimble", "lang": "Japanese"},
    "Sohee": {"desc": "Warm Korean female, rich emotion", "lang": "Korean"},
}

MODEL_IDS = {
    "custom_voice": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "voice_design": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
    "voice_clone": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
}

MODEL_LABELS = {
    "custom_voice": "Custom Voice (1.7B)",
    "voice_design": "Voice Design (1.7B)",
    "voice_clone": "Voice Clone / Base (1.7B)",
}

DEFAULT_SPEAKER = "Ryan"
DEFAULT_LANGUAGE = "Auto"

MAX_RETRIES = 3
RETRY_BACKOFF: tuple[int, int, int] = (5, 10, 20)


@dataclass
class BatchItem:
    text: str
    speaker: str = DEFAULT_SPEAKER
    language: str = DEFAULT_LANGUAGE
    instruct: str = ""


def _detect_device() -> str:
    if torch.cuda.is_available():
        return "cuda:0"
    if platform.system() == "Darwin" and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


DEVICE = _detect_device()


def _empty_device_cache() -> None:
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        torch.mps.empty_cache()


def is_model_cached(key: str) -> bool:
    model_id = MODEL_IDS.get(key)
    if not model_id:
        return False
    try:
        snapshot_download(model_id, local_files_only=True)
        return True
    except Exception:
        return False


class TTSEngine:
    def __init__(self) -> None:
        self._models: dict[str, Any] = {}

    def is_loaded(self, key: str) -> bool:
        return key in self._models

    def load_model(self, key: str) -> None:
        if key in self._models:
            return
        from qwen_tts import Qwen3TTSModel

        model_id = MODEL_IDS[key]
        model = Qwen3TTSModel.from_pretrained(
            model_id,
            device_map=DEVICE,
            dtype=torch.bfloat16,
        )
        self._models[key] = model

    def unload_model(self, key: str) -> None:
        model = self._models.pop(key, None)
        if model is None:
            return
        try:
            model.to("cpu")
        except Exception:
            pass
        del model
        _empty_device_cache()

    def generate_batch_item(self, item: BatchItem) -> tuple[str, float]:
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                result = self.generate_custom_voice(
                    text=item.text,
                    language=item.language,
                    speaker=item.speaker,
                    instruct=item.instruct,
                )
                gc.collect()
                _empty_device_cache()
                return result
            except (TimeoutError, RuntimeError) as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF[attempt])
        raise RuntimeError(f"Failed after {MAX_RETRIES + 1} attempts: {last_error}") from last_error

    def generate_custom_voice(
        self,
        text: str,
        language: str = DEFAULT_LANGUAGE,
        speaker: str = DEFAULT_SPEAKER,
        instruct: str = "",
    ) -> tuple[str, float]:
        model = self._models["custom_voice"]
        wavs, sr = model.generate_custom_voice(
            text=text,
            language=language,
            speaker=speaker,
            instruct=instruct or None,
        )
        return self._save(wavs[0], sr)

    def generate_voice_design(
        self,
        text: str,
        language: str = DEFAULT_LANGUAGE,
        instruct: str = "",
    ) -> tuple[str, float]:
        model = self._models["voice_design"]
        wavs, sr = model.generate_voice_design(
            text=text,
            language=language,
            instruct=instruct,
        )
        return self._save(wavs[0], sr)

    def generate_voice_clone(
        self,
        text: str,
        language: str = DEFAULT_LANGUAGE,
        ref_audio: str = "",
        ref_text: str = "",
    ) -> tuple[str, float]:
        model = self._models["voice_clone"]
        wavs, sr = model.generate_voice_clone(
            text=text,
            language=language,
            ref_audio=ref_audio,
            ref_text=ref_text,
        )
        return self._save(wavs[0], sr)

    @staticmethod
    def _save(wav, sr: int) -> tuple[str, float]:
        filename = f"{uuid.uuid4().hex[:12]}.wav"
        path = OUTPUT_DIR / filename
        sf.write(str(path), wav, sr)
        duration = len(wav) / sr
        return filename, duration


engine = TTSEngine()
