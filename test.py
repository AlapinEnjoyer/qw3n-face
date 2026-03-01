import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    device_map="mps",
    dtype=torch.bfloat16,
)

wavs, sr = model.generate_custom_voice(
    text="Ich habe es doch dir gesagt! Du hörst mir nie zu!",
    language="German",
    speaker="Ryan",
    instruct="very angry",
)
sf.write("output_custom_voice.wav", wavs[0], sr)

# # batch inference
# wavs, sr = model.generate_custom_voice(
#     text=[
#         "Nel mezzo del cammin di nostra vita mi ritrovai per una selva oscura, ché la diritta via era smarrita. Ahi quanto a dir qual era è cosa dura esta selva selvaggia e aspra e forte che nel pensier rinova la paura!",
#         "She said she would be here by noon."
#     ],
#     language=["Italian", "English"],
#     speaker=["Aiden", "Aiden"],
# )
# sf.write("output_custom_voice_1.wav", wavs[0], sr)
# sf.write("output_custom_voice_2.wav", wavs[1], sr)
