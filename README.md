# qw3n-face

A local web UI for the [Qwen3-TTS](https://huggingface.co/Qwen) model family, built with [NiceGUI](https://nicegui.io).

## Features

| Tab | Description |
|---|---|
| **Custom Voice** | Generate speech using one of 9 built-in speaker personas with optional style instructions |
| **Voice Design** | Describe a voice in plain text and synthesise speech with it |
| **Voice Clone** | Upload a short reference clip and clone that voice onto new text |
| **Batch** | Queue multiple Custom Voice items and generate them sequentially with per-item progress |
| **Personas** | Save and manage named voice presets (speaker + language + instruction) for quick reuse |

Models are loaded on demand and can be unloaded individually to free memory. Custom Voice and Voice Clone support both 0.6B and 1.7B checkpoints; Voice Design currently uses the 1.7B checkpoint only.

Additional runtime behavior:

- Choose the model size before loading when multiple checkpoints are available
- Choose the backend device before loading (`cuda:0`, `mps`, or `cpu`, depending on your machine)
- CUDA automatically prefers the `faster-qwen3-tts` backend and falls back to `qwen-tts` if the fast path cannot initialize
- Loaded tabs show the active runtime as `device / dtype / backend`
- On Apple Silicon, the app retries once in safer MPS `float32` mode if generation fails with a probability-tensor stability error

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- A machine with MPS (Apple Silicon), CUDA, or enough RAM for CPU inference

## Installation

```bash
git clone https://github.com/AlapinEnjoyer/qw3n-face.git
cd qw3n-face
uv sync
```

## Running

```bash
uv run main.py
```

Then app should auto open itself on [http://localhost:8080](http://localhost:8080).

## Models

Models are downloaded automatically from Hugging Face once requested in the app:

| Key | Checkpoint |
|---|---|
| Custom Voice | `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` or `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` |
| Voice Design | `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign` |
| Voice Clone | `Qwen/Qwen3-TTS-12Hz-1.7B-Base` or `Qwen/Qwen3-TTS-12Hz-0.6B-Base` |

Approximate checkpoint sizes vary by model variant; 0.6B models are substantially smaller than 1.7B models. Downloads are cached locally by Hugging Face after the first load.

## Runtime Notes

- CUDA uses `bfloat16` and automatically attempts the CUDA-graph fast backend (`faster-qwen3-tts`)
- MPS prefers `float16`, but the app can retry a failing model in `float32` for stability
- CPU prefers `bfloat16` and falls back to `float32` if needed during model load
- Fast CUDA mode uses the library's public API; subtalker-specific controls stay available on the normal `qwen-tts` backend and are disabled in the UI when the fast backend is loaded
- If Apple Silicon generation still fails on MPS, switch the backend device to `cpu` before loading the model

## TODOs
- [x] Add automatic transcription of uploaded audio
- [ ] Add audio visualisation (waveform, spectrogram?)

## Roadmap
- [ ] Add support for fine tuning
