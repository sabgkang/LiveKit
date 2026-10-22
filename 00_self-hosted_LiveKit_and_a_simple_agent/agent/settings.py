"""Provider-independent pipeline configuration; no network or SDK imports."""
from dataclasses import dataclass, field
import os


@dataclass(frozen=True)
class Stage:
    provider: str
    model: str
    base_url: str = ''


@dataclass(frozen=True)
class Settings:
    stt: Stage
    llm: Stage
    tts: Stage
    cloud_key: str = field(repr=False)
    cloud_secret: str = field(repr=False)
    stt_language: str = ''
    tts_language: str = ''
    voice: str = ''

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        def required(name):
            value = env.get(name, '').strip()
            if not value:
                raise ValueError(f'缺少 {name}；請在本機 .env 設定，勿貼到對話中。')
            return value
        stages = []
        for name in ('STT', 'LLM', 'TTS'):
            provider = env.get(f'{name}_PROVIDER', 'livekit')
            if provider != 'livekit':
                raise ValueError(f'{name}_PROVIDER={provider} 尚未實作；目前僅支援 livekit，沒有自動 fallback。')
            stages.append(Stage(provider, required(f'{name}_MODEL'), env.get(f'{name}_BASE_URL', '').strip()))
        cloud_key = required('LIVEKIT_INFERENCE_API_KEY')
        cloud_secret = required('LIVEKIT_INFERENCE_API_SECRET')
        if cloud_key == required('LIVEKIT_API_KEY') or cloud_secret == required('LIVEKIT_API_SECRET'):
            raise ValueError('Cloud 推論與自架 LiveKit 必須使用不同的憑證。')
        if env.get('LIVEKIT_URL') != 'ws://127.0.0.1:7880':
            raise ValueError('第一階段 LIVEKIT_URL 必須是 ws://127.0.0.1:7880。')
        return cls(*stages, cloud_key, cloud_secret,
                   env.get('STT_LANGUAGE', '').strip(), env.get('TTS_LANGUAGE', '').strip(), required('TTS_VOICE'))

    def inference_kwargs(self, stage):
        options = {'model': stage.model, 'api_key': self.cloud_key, 'api_secret': self.cloud_secret}
        if stage.base_url:
            options['base_url'] = stage.base_url
        return options
