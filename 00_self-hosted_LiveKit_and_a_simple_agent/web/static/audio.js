/* Shared playback handling; failures must not tear down the microphone session. */
'use strict';
globalThis.AudioPlayback = {
  async play(element, deviceId) {
    const result = { outputError: false, blocked: false, playbackError: false };
    element.muted = false;
    element.volume = 1;
    if (deviceId && typeof element.setSinkId === 'function') {
      try { await element.setSinkId(deviceId); }
      catch { result.outputError = true; }
    } else if (deviceId && deviceId !== 'default') {
      result.outputError = true;
    }
    try { await element.play(); }
    catch (exc) {
      if (exc.name === 'NotAllowedError') result.blocked = true;
      else result.playbackError = true;
    }
    return result;
  },

  testWav() {
    const rate = 48000;
    const samples = rate / 2;
    const buffer = new ArrayBuffer(44 + samples * 2);
    const view = new DataView(buffer);
    const text = (offset, value) => [...value].forEach((char, index) => view.setUint8(offset + index, char.charCodeAt(0)));
    text(0, 'RIFF'); view.setUint32(4, buffer.byteLength - 8, true); text(8, 'WAVE');
    text(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
    view.setUint16(22, 1, true); view.setUint32(24, rate, true); view.setUint32(28, rate * 2, true);
    view.setUint16(32, 2, true); view.setUint16(34, 16, true); text(36, 'data');
    view.setUint32(40, samples * 2, true);
    for (let index = 0; index < samples; index++) {
      const fade = Math.min(1, index / 480, (samples - index - 1) / 480);
      view.setInt16(44 + index * 2, Math.sin(2 * Math.PI * 440 * index / rate) * 5000 * fade, true);
    }
    return buffer;
  },
};
