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

MODEL_VARIANTS: dict[str, dict[str, str]] = {
    "custom_voice": {
        "1.7B": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        "0.6B": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
    },
    "voice_design": {
        "1.7B": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
    },
    "voice_clone": {
        "1.7B": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "0.6B": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
    },
}

MODEL_LABELS = {
    "custom_voice": "Custom Voice",
    "voice_design": "Voice Design",
    "voice_clone": "Voice Clone / Base",
}


def get_available_model_sizes(key: str) -> list[str]:
    return list(MODEL_VARIANTS.get(key, {}).keys())


def get_model_id(key: str, size: str) -> str:
    return MODEL_VARIANTS[key][size]


def get_model_label(key: str, size: str) -> str:
    return f"{MODEL_LABELS[key]} ({size})"


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


def get_available_devices() -> list[str]:
    devices: list[str] = []
    if torch.cuda.is_available():
        devices.append("cuda:0")
    if platform.system() == "Darwin" and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        devices.append("mps")
    devices.append("cpu")
    return devices


DEFAULT_DEVICE = _detect_device()


def _empty_device_cache(device: str) -> None:
    if torch.cuda.is_available():
        if device.startswith("cuda"):
            torch.cuda.empty_cache()
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        if device == "mps":
            torch.mps.empty_cache()


def _load_dtype(device: str, model_key: str, force_mps_fp32: bool = False):
    if device.startswith("cuda"):
        return torch.bfloat16
    if device == "mps":
        if force_mps_fp32:
            return torch.float32
        if model_key == "voice_clone":
            return torch.float32
        return torch.float16
    return torch.bfloat16


def _is_probability_tensor_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "probability tensor contains either" in msg


def is_model_cached(key: str, size: str) -> bool:
    model_ids = MODEL_VARIANTS.get(key)
    if not model_ids:
        return False
    model_id = model_ids.get(size)
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
        self._loaded_sizes: dict[str, str] = {}
        self._loaded_dtypes: dict[str, Any] = {}
        self._device: str = DEFAULT_DEVICE
        self._mps_force_fp32: dict[str, bool] = {}
        self._selected_sizes: dict[str, str] = {
            key: ("1.7B" if "1.7B" in variants else next(iter(variants))) for key, variants in MODEL_VARIANTS.items()
        }

    def get_available_devices(self) -> list[str]:
        return get_available_devices()

    def get_device(self) -> str:
        return self._device

    def set_device(self, device: str) -> None:
        if device not in self.get_available_devices():
            raise ValueError(f"Unsupported device '{device}'")
        if device == self._device:
            return
        for key in list(self._models.keys()):
            self.unload_model(key)
        self._device = device

    def get_loaded_dtype(self, key: str):
        return self._loaded_dtypes.get(key)

    def get_selected_size(self, key: str) -> str:
        return self._selected_sizes[key]

    def set_selected_size(self, key: str, size: str) -> None:
        if size not in MODEL_VARIANTS[key]:
            raise ValueError(f"Unsupported model size '{size}' for {key}")
        self._selected_sizes[key] = size

    def get_loaded_size(self, key: str) -> str | None:
        return self._loaded_sizes.get(key)

    def is_loaded(self, key: str) -> bool:
        return key in self._models and self._loaded_sizes.get(key) == self._selected_sizes.get(key)

    def load_model(self, key: str) -> None:
        target_size = self._selected_sizes[key]
        if key in self._models and self._loaded_sizes.get(key) == target_size:
            return
        if key in self._models:
            self.unload_model(key)
        from qwen_tts import Qwen3TTSModel

        model_id = get_model_id(key, target_size)
        load_dtype = _load_dtype(self._device, key, force_mps_fp32=self._mps_force_fp32.get(key, False))
        try:
            model = Qwen3TTSModel.from_pretrained(
                model_id,
                device_map=self._device,
                dtype=load_dtype,
            )
        except Exception:
            if self._device == "cpu" and load_dtype == torch.bfloat16:
                load_dtype = torch.float32
                model = Qwen3TTSModel.from_pretrained(
                    model_id,
                    device_map=self._device,
                    dtype=load_dtype,
                )
            else:
                raise
        self._models[key] = model
        self._loaded_sizes[key] = target_size
        self._loaded_dtypes[key] = load_dtype

    def unload_model(self, key: str) -> None:
        model = self._models.pop(key, None)
        self._loaded_sizes.pop(key, None)
        self._loaded_dtypes.pop(key, None)
        if model is None:
            return
        try:
            model.to("cpu")
        except Exception:
            pass
        del model
        _empty_device_cache(self._device)

    def _run_with_stability_retry(self, key: str, fn):
        try:
            return fn()
        except RuntimeError as exc:
            if self._device == "mps" and not self._mps_force_fp32.get(key, False) and _is_probability_tensor_error(exc):
                self._mps_force_fp32[key] = True
                self.unload_model(key)
                self.load_model(key)
                return fn()
            raise

    def generate_batch_item(self, item: BatchItem, **kwargs) -> tuple[str, float]:
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                result = self.generate_custom_voice(
                    text=item.text,
                    language=item.language,
                    speaker=item.speaker,
                    instruct=item.instruct,
                    **kwargs,
                )
                gc.collect()
                _empty_device_cache(self._device)
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
        **kwargs,
    ) -> tuple[str, float]:
        wavs, sr = self._run_with_stability_retry(
            "custom_voice",
            lambda: self._models["custom_voice"].generate_custom_voice(
                text=text,
                language=language,
                speaker=speaker,
                instruct=instruct or None,
                **kwargs,
            ),
        )
        return self._save(wavs[0], sr)

    def generate_voice_design(
        self,
        text: str,
        language: str = DEFAULT_LANGUAGE,
        instruct: str = "",
        **kwargs,
    ) -> tuple[str, float]:
        wavs, sr = self._run_with_stability_retry(
            "voice_design",
            lambda: self._models["voice_design"].generate_voice_design(
                text=text,
                language=language,
                instruct=instruct,
                **kwargs,
            ),
        )
        return self._save(wavs[0], sr)

    def generate_voice_clone(
        self,
        text: str,
        language: str = DEFAULT_LANGUAGE,
        ref_audio: str = "",
        ref_text: str = "",
        **kwargs,
    ) -> tuple[str, float]:
        wavs, sr = self._run_with_stability_retry(
            "voice_clone",
            lambda: self._models["voice_clone"].generate_voice_clone(
                text=text,
                language=language,
                ref_audio=ref_audio,
                ref_text=ref_text,
                **kwargs,
            ),
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
