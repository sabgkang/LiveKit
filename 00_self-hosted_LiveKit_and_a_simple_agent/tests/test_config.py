import contextlib
import io
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.settings import Settings
from scripts.setup import read_env, setup


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copy(ROOT / '.env.example', self.root)
        with contextlib.redirect_stdout(io.StringIO()):
            setup(self.root)
        self.env = read_env(self.root / '.env')
        self.env.update(LIVEKIT_INFERENCE_API_KEY='cloud_key', LIVEKIT_INFERENCE_API_SECRET='cloud_secret')

    def test_cloud_credentials_never_fall_back_to_local_credentials(self):
        self.env['LIVEKIT_INFERENCE_API_SECRET'] = ''
        with self.assertRaisesRegex(ValueError, 'LIVEKIT_INFERENCE_API_SECRET'):
            Settings.from_env(self.env)

    def test_shared_credentials_are_rejected(self):
        self.env['LIVEKIT_INFERENCE_API_KEY'] = self.env['LIVEKIT_API_KEY']
        with self.assertRaisesRegex(ValueError, '不同的憑證'):
            Settings.from_env(self.env)

    def test_pipeline_options_only_receive_cloud_credentials(self):
        settings = Settings.from_env(self.env)
        for stage in (settings.stt, settings.llm, settings.tts):
            options = settings.inference_kwargs(stage)
            self.assertEqual(options['api_key'], 'cloud_key')
            self.assertEqual(options['api_secret'], 'cloud_secret')
        self.assertNotIn('cloud_secret', repr(settings))

    def test_unsupported_provider_fails_without_fallback(self):
        self.env['STT_PROVIDER'] = 'local'
        with self.assertRaisesRegex(ValueError, '尚未實作'):
            Settings.from_env(self.env)

    def test_stage_endpoints_are_independent(self):
        self.env['STT_BASE_URL'] = 'https://stt.example.invalid'
        settings = Settings.from_env(self.env)
        self.assertEqual(settings.inference_kwargs(settings.stt)['base_url'], self.env['STT_BASE_URL'])
        self.assertNotIn('base_url', settings.inference_kwargs(settings.llm))

    def test_setup_preserves_credentials_and_private_permissions(self):
        original = (self.root / '.env').read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            setup(self.root)
        self.assertEqual((self.root / '.env').read_bytes(), original)
        for path in (self.root / '.env', self.root / 'runtime/livekit.yaml'):
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        config = (self.root / 'runtime/livekit.yaml').read_text()
        self.assertIn(self.env['LIVEKIT_API_SECRET'], config)
        self.assertNotIn('cloud_secret', config)
        self.assertIn('node_ip: 127.0.0.1', config)


if __name__ == '__main__':
    unittest.main()
