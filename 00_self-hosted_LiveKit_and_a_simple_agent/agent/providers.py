"""Replace a stage here when adding a local provider; room lifecycle stays separate."""
from settings import Settings


def build_pipeline(config: Settings):
    from livekit.agents import inference
    stt_options = config.inference_kwargs(config.stt)
    if config.stt_language:
        stt_options['language'] = config.stt_language
    tts_options = config.inference_kwargs(config.tts)
    tts_options['voice'] = config.voice
    if config.tts_language:
        tts_options['language'] = config.tts_language
    return {
        'stt': inference.STT(**stt_options),
        'llm': inference.LLM(**config.inference_kwargs(config.llm)),
        'tts': inference.TTS(**tts_options),
    }
