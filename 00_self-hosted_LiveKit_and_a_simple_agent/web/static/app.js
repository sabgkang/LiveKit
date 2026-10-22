/* global LivekitClient, AudioPlayback */
'use strict';
const $ = (id) => document.getElementById(id);
let room = null;
let attempt = 0;
let agentTimer = null;
const error = (message) => { $('error').textContent = message; };
const status = (message) => { $('status').textContent = message; };
const audioStatus = (message) => { $('audio-status').textContent = message; };
let testAudioUrl = null;

function reportPlayback(result) {
  if (result.outputError) error('無法切換到所選喇叭；請在系統音效設定選擇 Jabra，或改選「系統預設」。');
  if (result.blocked) {
    audioStatus('瀏覽器阻擋自動播放。請點「啟用／重試聲音播放」或音訊播放器的播放鍵。');
  } else if (result.playbackError) {
    audioStatus('音訊播放失敗。請按播放器播放鍵，並檢查瀏覽器分頁是否靜音。');
  } else {
    audioStatus('播放已啟動；若仍無聲，請測試喇叭並檢查系統輸出與分頁靜音。');
  }
}

async function resumePlayback() {
  const activeRoom = room;
  if (!activeRoom) return;
  // Call directly from the click handler, before awaiting output-device changes.
  const start = activeRoom.startAudio();
  const elements = [...$('audio').querySelectorAll('audio')];
  const playback = elements.map((element) => AudioPlayback.play(element, $('speaker').value));
  try { await start; }
  catch { audioStatus('瀏覽器尚未允許播放，請點音訊播放器的播放鍵。'); }
  for (const result of await Promise.all(playback)) {
    if (room === activeRoom) reportPlayback(result);
  }
  if (!elements.length && room === activeRoom) audioStatus('播放已啟用，尚未收到助理音訊。');
}

async function refreshDevices(requestPermission = false) {
  if (!navigator.mediaDevices) throw new Error('瀏覽器無法使用音訊裝置，請從 http://localhost:3000 開啟。');
  if (requestPermission) {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    stream.getTracks().forEach((track) => track.stop());
  }
  const devices = await navigator.mediaDevices.enumerateDevices();
  for (const [id, kind] of [['microphone', 'audioinput'], ['speaker', 'audiooutput']]) {
    const select = $(id);
    const previous = select.value;
    const items = devices.filter((device) => device.kind === kind);
    select.replaceChildren(new Option('系統預設', ''));
    items.forEach((device, index) => select.add(new Option(device.label || `裝置 ${index + 1}`, device.deviceId)));
    const preferred = items.find((device) => /jabra/i.test(device.label));
    select.value = items.some((item) => item.deviceId === previous) ? previous : (preferred?.deviceId || '');
  }
}

function finishUI() {
  clearTimeout(agentTimer);
  $('connect').disabled = false;
  $('disconnect').disabled = true;
  $('microphone').disabled = false;
  $('speaker').disabled = false;
  $('devices').disabled = false;
  $('play').disabled = true;
  $('audio').replaceChildren();
  audioStatus('尚未收到助理音訊。可先測試喇叭。');
}

async function connect() {
  const currentAttempt = ++attempt;
  $('connect').disabled = true;
  $('disconnect').disabled = false;
  error('');
  status('正在取得麥克風權限…');
  let nextRoom;
  try {
    if (!window.LivekitClient) throw new Error('LiveKit 網頁 SDK 載入失敗，請重新建置 web image。');
    await refreshDevices(true);
    if (attempt !== currentAttempt) return;
    $('microphone').disabled = true;
    $('speaker').disabled = true;
    $('devices').disabled = true;
    const { Room, RoomEvent, Track } = LivekitClient;
    nextRoom = new Room();
    room = nextRoom;
    nextRoom.on(RoomEvent.TrackSubscribed, (track) => {
      if (track.kind !== Track.Kind.Audio) return;
      const element = track.attach();
      element.controls = true;
      element.autoplay = true;
      element.setAttribute('aria-label', '助理語音');
      track.setVolume(1);
      $('audio').appendChild(element);
      audioStatus('已收到助理音訊軌，正在啟動播放…');
      element.addEventListener('playing', () => {
        if (room === nextRoom) audioStatus('助理音訊播放器正在播放。');
      });
      AudioPlayback.play(element, $('speaker').value).then((result) => {
        if (room === nextRoom) reportPlayback(result);
      });
    });
    nextRoom.on(RoomEvent.TrackUnsubscribed, (track) => track.detach().forEach((element) => element.remove()));
    nextRoom.on(RoomEvent.AudioPlaybackStatusChanged, () => {
      if (room === nextRoom && !nextRoom.canPlaybackAudio) {
        audioStatus('瀏覽器阻擋自動播放，請點「啟用／重試聲音播放」。');
      }
    });
    nextRoom.on(RoomEvent.TrackSubscriptionFailed, () => {
      if (room === nextRoom) audioStatus('助理音訊訂閱失敗，請重新連線並查看服務日誌。');
    });
    nextRoom.on(RoomEvent.Reconnecting, () => status('連線中斷，正在重新連線…'));
    nextRoom.on(RoomEvent.Reconnected, () => status('已重新連線'));
    nextRoom.on(RoomEvent.Disconnected, () => {
      if (room === nextRoom) { room = null; ++attempt; finishUI(); status('已結束對話，可重新連線。'); }
    });
    nextRoom.on(RoomEvent.DataReceived, (payload, participant, kind, topic) => {
      if (topic === 'agent.error') {
        try { error(JSON.parse(new TextDecoder().decode(payload)).message); }
        catch { error('Agent 回報推論錯誤，請檢查服務日誌。'); }
      }
    });
    const updateAgent = (participant) => {
      const state = participant.attributes?.['lk.agent.state'];
      if (!state) return;
      clearTimeout(agentTimer);
      const labels = { initializing: '助理初始化中…', listening: '正在聆聽', thinking: '助理思考中…', speaking: '助理說話中…' };
      status(labels[state] || '助理已連線');
    };
    nextRoom.on(RoomEvent.ParticipantConnected, updateAgent);
    nextRoom.on(RoomEvent.ParticipantAttributesChanged, (changes, participant) => updateAgent(participant));
    nextRoom.registerTextStreamHandler('lk.transcription', async (reader, participantInfo) => {
      const line = document.createElement('div');
      const isUser = participantInfo.identity === nextRoom.localParticipant.identity;
      line.className = `utterance${isUser ? '' : ' assistant'}`;
      const label = document.createElement('strong');
      label.textContent = isUser ? '你' : '助理';
      const content = document.createElement('span');
      line.append(label, content);
      $('transcript').appendChild(line);
      try { for await (const chunk of reader) content.textContent += chunk; }
      catch { error('逐字稿串流中斷。'); }
    });
    const response = await fetch('/api/token', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || '無法取得連線權杖。');
    if (attempt !== currentAttempt) return;
    status('正在加入語音房間…');
    await nextRoom.connect(result.url, result.token);
    if (attempt !== currentAttempt) { await nextRoom.disconnect(); return; }
    if ($('speaker').value) {
      try {
        const switched = await nextRoom.switchActiveDevice('audiooutput', $('speaker').value);
        if (!switched) error('喇叭切換未成功；請確認系統預設輸出為 Jabra。');
      }
      catch { error('瀏覽器不支援指定喇叭；請在系統音效設定選擇 Jabra。'); }
    }
    await nextRoom.localParticipant.setMicrophoneEnabled(true, {
      deviceId: $('microphone').value || undefined,
      echoCancellation: true, noiseSuppression: true, autoGainControl: true,
    });
    if (attempt !== currentAttempt) { await nextRoom.disconnect(); return; }
    $('play').disabled = false;
    await resumePlayback();
    if (attempt !== currentAttempt) { await nextRoom.disconnect(); return; }
    status('已連線，等待助理…');
    agentTimer = setTimeout(() => {
      if (room === nextRoom) error('助理尚未回應，請檢查 Agent 日誌及 Cloud 推論權限、額度與網路。');
    }, 30000);
    nextRoom.remoteParticipants.forEach(updateAgent);
  } catch (exc) {
    if (attempt === currentAttempt) {
      error(exc.message || String(exc));
      room = null;
      finishUI();
      status('連線失敗，可修正問題後重試。');
    }
    if (nextRoom) await nextRoom.disconnect();
  }
}

$('devices').onclick = async () => { try { await refreshDevices(true); error(''); } catch (exc) { error(exc.message); } };
$('connect').onclick = connect;
$('disconnect').onclick = async () => {
  ++attempt;
  const previousRoom = room;
  room = null;
  if (previousRoom) await previousRoom.disconnect();
  finishUI();
  status('已結束對話。');
};
$('play').onclick = async () => { try { await resumePlayback(); } catch { error('無法啟用音訊，請點播放器播放鍵重試。'); } };
$('test-speaker').onclick = async () => {
  $('test-speaker').disabled = true;
  error('');
  try {
    const element = $('speaker-test');
    element.pause();
    if (testAudioUrl) URL.revokeObjectURL(testAudioUrl);
    testAudioUrl = URL.createObjectURL(new Blob([AudioPlayback.testWav()], { type: 'audio/wav' }));
    element.src = testAudioUrl;
    element.hidden = false;
    audioStatus('正在播放半秒測試音；這項測試不使用 AI 或 LiveKit。');
    reportPlayback(await AudioPlayback.play(element, $('speaker').value));
  } catch { error('無法播放測試音，請使用下方播放器播放鍵重試。'); }
  finally { $('test-speaker').disabled = false; }
};
refreshDevices().catch((exc) => error(exc.message));
