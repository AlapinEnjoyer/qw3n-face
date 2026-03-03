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

Models are loaded on demand and can be unloaded individually to free memory. All three models are separate 1.7B checkpoints downloaded from Hugging Face.

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- A machine with MPS (Apple Silicon), CUDA, or enough RAM for CPU inference (~4 GB per model)

## Installation

```bash
git clone https://github.com/AlapinEnjoyer/qw3n-face.git
cd qw3n-face
uv sync
```

## Running

```bash
uv run python main.py
```

Then app should auto open itself on [http://localhost:8080](http://localhost:8080).

## Models

Models are downloaded automatically from Hugging Face on first load:

| Key | Checkpoint |
|---|---|
| Custom Voice | `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` |
| Voice Design | `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign` |
| Voice Clone | `Qwen/Qwen3-TTS-12Hz-1.7B-Base` |

Each model is ~3.4 GB. They are cached locally by Hugging Face after the first download.

## TODOs
- [x] Add automatic transcription of uploaded audio
- [ ] Add audio visualisation (waveform, spectrogram?)

## Roadmap
- [ ] Add support for fine tuning
