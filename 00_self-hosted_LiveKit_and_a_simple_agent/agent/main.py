import asyncio
import json
import logging

from livekit.agents import Agent, AgentServer, AgentSession, JobContext, TurnHandlingOptions, cli
from livekit.plugins import silero

from providers import build_pipeline
from settings import Settings

logger = logging.getLogger('local-voice')
server = AgentServer(host='127.0.0.1', port=8081, num_idle_processes=2, drain_timeout=600)


@server.rtc_session(agent_name='local-voice')
async def voice_session(ctx: JobContext):
    config = Settings.from_env()
    await ctx.connect()
    session = AgentSession(
        **build_pipeline(config),
        vad=silero.VAD.load(),
        turn_handling=TurnHandlingOptions(
            turn_detection='vad', interruption={'enabled': True, 'mode': 'vad'},
        ),
    )
    tasks = set()

    @session.on('error')
    def on_error(event):
        # Never send raw exceptions, tokens, or provider response bodies to the browser.
        error = getattr(event, 'error', None)
        message = '雲端推論發生錯誤，請檢查 Cloud 憑證、模型權限、額度及網路，再重新連線。'
        logger.error('inference_error type=%s', type(error).__name__)
        async def notify():
            try:
                await ctx.room.local_participant.publish_data(
                    json.dumps({'message': message}).encode(), reliable=True, topic='agent.error')
            except Exception:
                logger.warning('Could not deliver inference error to participant')
        task = asyncio.create_task(notify())
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    @session.on('metrics_collected')
    def on_metrics(event):
        metric = event.metrics
        fields = {name: getattr(metric, name) for name in
                  ('type', 'duration', 'ttft', 'ttfb', 'eou_delay', 'transcription_delay')
                  if hasattr(metric, name)}
        logger.info('pipeline_metric room=%s %s', ctx.room.name, json.dumps(fields))

    await session.start(
        room=ctx.room,
        agent=Agent(instructions=(
            '你是友善的語音助理。預設以繁體中文回答；使用者以英文對話時可用英文。'
            '回答簡短自然，適合朗讀，避免 Markdown、表格及程式碼。'
            '不聲稱已執行你沒有工具可執行的操作。')),
    )
    await session.generate_reply(instructions='用繁體中文簡短問候，告訴使用者可以開始說話。')


if __name__ == '__main__':
    cli.run_app(server)
