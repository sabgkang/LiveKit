const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const context = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../web/static/audio.js'), 'utf8'), context);
const playback = context.AudioPlayback;

test('autoplay rejection is reported without rejecting the session', async () => {
  const element = { muted: true, volume: 0, play: async () => { throw { name: 'NotAllowedError' }; } };
  const result = await playback.play(element, '');
  assert.equal(result.blocked, true);
  assert.equal(result.playbackError, false);
  assert.equal(element.muted, false);
  assert.equal(element.volume, 1);
});

test('output selection failure still attempts playback on the current output', async () => {
  let played = false;
  const element = { setSinkId: async () => { throw new Error('device unavailable'); }, play: async () => { played = true; } };
  const result = await playback.play(element, 'jabra');
  assert.equal(result.outputError, true);
  assert.equal(played, true);
});

test('unsupported output selection is reported', async () => {
  const result = await playback.play({ play: async () => {} }, 'jabra');
  assert.equal(result.outputError, true);
  assert.equal(result.blocked, false);
});

test('successful output selection happens before playback', async () => {
  const calls = [];
  const result = await playback.play({
    setSinkId: async (id) => { calls.push(id); }, play: async () => { calls.push('play'); },
  }, 'jabra');
  assert.deepEqual(calls, ['jabra', 'play']);
  assert.equal(result.outputError, false);
  assert.equal(result.playbackError, false);
});

test('test tone is a non-silent half-second mono PCM WAV', () => {
  const bytes = Buffer.from(playback.testWav());
  assert.equal(bytes.toString('ascii', 0, 4), 'RIFF');
  assert.equal(bytes.toString('ascii', 8, 12), 'WAVE');
  assert.equal(bytes.readUInt32LE(4), bytes.length - 8);
  assert.equal(bytes.readUInt16LE(22), 1);
  assert.equal(bytes.readUInt32LE(24), 48000);
  assert.equal(bytes.readUInt16LE(34), 16);
  assert.equal(bytes.readUInt32LE(40), 48000);
  assert.ok(bytes.subarray(44).some((value) => value !== 0));
});
