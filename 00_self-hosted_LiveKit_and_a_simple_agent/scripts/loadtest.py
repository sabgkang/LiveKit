"""Opt-in real speech load test. Cloud inference is billed by the user's project."""
import argparse
import asyncio
import json
from pathlib import Path
import time
import urllib.request
import wave


def get_token():
    request = urllib.request.Request('http://127.0.0.1:3000/api/token', data=b'{}',
                                    headers={'Content-Type': 'application/json', 'Origin': 'http://127.0.0.1:3000'})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


async def one_call(index, pcm, sample_rate, seconds):
    from livekit import rtc
    room = rtc.Room()
    tasks = set()
    started = time.monotonic()
    result = {'call': index, 'connected': False, 'audio_frames': 0,
              'first_audio_seconds': None, 'inference_errors': 0, 'unexpected_disconnect': False}
    stopping = False

    @room.on('disconnected')
    def disconnected(reason):
        if not stopping:
            result['unexpected_disconnect'] = True

    async def consume(track):
        stream = rtc.AudioStream(track)
        try:
            async for event in stream:
                if any(event.frame.data):
                    result['audio_frames'] += 1
                    if result['first_audio_seconds'] is None:
                        result['first_audio_seconds'] = round(time.monotonic() - started, 3)
        finally:
            await stream.aclose()

    @room.on('track_subscribed')
    def subscribed(track, publication, participant):
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            task = asyncio.create_task(consume(track))
            tasks.add(task)

    @room.on('data_received')
    def data_received(packet):
        if packet.topic == 'agent.error':
            result['inference_errors'] += 1

    try:
        token = await asyncio.to_thread(get_token)
        await asyncio.wait_for(room.connect(token['url'], token['token']), timeout=30)
        result['connected'] = True
        source = rtc.AudioSource(sample_rate, 1)
        track = rtc.LocalAudioTrack.create_audio_track('load-speech', source)
        await room.local_participant.publish_track(track, rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE))
        # Allow time for the initial greeting, then alternate real speech and silence.
        await asyncio.sleep(8)
        end = time.monotonic() + seconds
        frame_bytes = sample_rate // 50 * 2
        silence = bytes(sample_rate * 2 * 10)
        while time.monotonic() < end:
            for block in (pcm, silence):
                for offset in range(0, len(block), frame_bytes):
                    if time.monotonic() >= end:
                        break
                    data = block[offset:offset + frame_bytes].ljust(frame_bytes, b'\0')
                    await source.capture_frame(rtc.AudioFrame(data, sample_rate, 1, frame_bytes // 2))
        await source.wait_for_playout()
    except Exception as exc:
        # Error type is enough for the summary; never dump tokens or provider bodies.
        result['error_type'] = type(exc).__name__
    finally:
        stopping = True
        await room.disconnect()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    return result


async def run(args):
    with wave.open(str(args.wav), 'rb') as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2 or wav.getcomptype() != 'NONE':
            raise ValueError('需要 16-bit PCM 單聲道 WAV。')
        if wav.getframerate() not in (16000, 24000, 48000):
            raise ValueError('WAV 採樣率需為 16000、24000 或 48000 Hz。')
        sample_rate = wav.getframerate()
        if not 1 <= wav.getnframes() / sample_rate <= 15:
            raise ValueError('請使用 1–15 秒、含真實語音的 WAV。')
        pcm = wav.readframes(wav.getnframes())
    results = await asyncio.gather(*(one_call(i + 1, pcm, sample_rate, args.seconds) for i in range(args.calls)))
    print(json.dumps({'calls': args.calls, 'seconds': args.seconds, 'results': results}, ensure_ascii=False))
    return all(item['connected'] and item['audio_frames'] > 0 and item['inference_errors'] == 0
               and not item['unexpected_disconnect'] and 'error_type' not in item for item in results)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='實際呼叫 Cloud 推論的語音負載測試，會產生用量。')
    parser.add_argument('--wav', type=Path, required=True)
    parser.add_argument('--calls', type=int, choices=(1, 5, 10, 20), default=1)
    parser.add_argument('--seconds', type=int, default=60)
    args = parser.parse_args()
    if not 30 <= args.seconds <= 600:
        parser.error('--seconds 必須介於 30 與 600。')
    try:
        success = asyncio.run(run(args))
    except (ValueError, OSError) as exc:
        raise SystemExit(str(exc)) from None
    raise SystemExit(0 if success else 1)
