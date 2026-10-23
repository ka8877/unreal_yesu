// Tests the actual pinned signalling wrapper over real local WebSockets.
// The streamer is a protocol test client, never a rendering/gameplay surrogate.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { once } from 'node:events';
import net from 'node:net';

const here = path.dirname(fileURLToPath(import.meta.url));
const index = process.argv.indexOf('--vendor');
if (index < 0) throw new Error('Use --vendor <pinned infrastructure checkout>');
const vendor = path.resolve(process.argv[index + 1]);
const require = createRequire(path.join(vendor, 'package.json'));
const WebSocket = require('ws');
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'pathofdawn-signalling-test-'));
const freePort = () => new Promise((resolve, reject) => {
  const socket = net.createServer(); socket.on('error', reject);
  socket.listen(0, '127.0.0.1', () => { const port = socket.address().port; socket.close(() => resolve(port)); });
});
const port = await freePort(), streamerPort = await freePort();
const base = `http://127.0.0.1:${port}`;
fs.writeFileSync(path.join(temporary, 'config.json'), JSON.stringify({vendor, buildId: 'test-protocol-only', port, streamerPort, logRoot: path.join(temporary, 'logs')}));
const processHandle = spawn(process.execPath, [path.join(here, 'server.mjs'), '--config', path.join(temporary, 'config.json')], {stdio: ['ignore', 'pipe', 'pipe']});
let output = ''; processHandle.stdout.on('data', chunk => output += chunk); processHandle.stderr.on('data', chunk => output += chunk);
const clients = [];
const connect = async (url, origin = base) => {
  const ws = new WebSocket(url, {origin}); clients.push(ws);
  ws.messages = [];
  ws.on('message', data => { ws.messages.push(JSON.parse(data.toString())); });
  await once(ws, 'open'); return ws;
};
const waitFor = async predicate => {
  for (let attempt = 0; attempt < 100; attempt++) {
    if (await predicate()) return;
    await new Promise(resolve => setTimeout(resolve, 40));
  }
  throw new Error(`Timed out. Server output:\n${output}`);
};
const rejected = (url, origin = base) => new Promise((resolve, reject) => {
  const ws = new WebSocket(url, {origin}); clients.push(ws);
  const timer = setTimeout(() => reject(new Error('Rejected connection timed out')), 3000);
  ws.on('unexpected-response', (_request, response) => { clearTimeout(timer); ws.terminate(); resolve(response.statusCode); });
  ws.on('error', () => {});
  ws.on('open', () => { clearTimeout(timer); reject(new Error('Unauthorized connection opened')); });
});
let checks = 0;
try {
  await waitFor(async () => { try { return (await fetch(`${base}/status`)).ok; } catch { return false; } });
  const page = await fetch(base);
  assert.equal(page.headers.get('cache-control'), 'no-store'); checks++;
  assert.equal((await fetch(`${base}/api/status`)).status, 404); checks++;
  assert.equal((await fetch(`${base}/versions.lock.json`)).status, 404); checks++;
  assert.equal(await rejected(`ws://127.0.0.1:${port}`, 'https://untrusted.invalid'), 401); checks++;
  const streamer = await connect(`ws://127.0.0.1:${streamerPort}`);
  streamer.send(JSON.stringify({type: 'endpointId', id: 'ProtocolTest'}));
  await waitFor(() => streamer.messages.some(m => m.type === 'endpointIdConfirm'));
  assert.equal(await rejected(`ws://127.0.0.1:${streamerPort}`), 401); checks++;
  const first = await connect(`ws://127.0.0.1:${port}`);
  first.send(JSON.stringify({type:'subscribe',streamerId:'ProtocolTest'}));
  await waitFor(() => streamer.messages.some(m => m.type === 'playerConnected'));
  const state = await (await fetch(`${base}/status`)).json();
  assert.equal(state.controllers, 1); assert.equal(state.mediaVerified, false); checks++;
  assert.equal(await rejected(`ws://127.0.0.1:${port}`), 401); checks++;
  first.close(); await once(first, 'close');
  await waitFor(async () => (await (await fetch(`${base}/status`)).json()).controllers === 0);
  const reconnected = await connect(`ws://127.0.0.1:${port}`);
  reconnected.send(JSON.stringify({type:'subscribe',streamerId:'ProtocolTest'}));
  await waitFor(async () => (await (await fetch(`${base}/status`)).json()).controllers === 1); checks++;
  assert.equal((await (await fetch(`${base}/status`)).json()).hostBuildId, 'test-protocol-only'); checks++;
  console.log(JSON.stringify({passed: true, checks, scope: 'actual HTTP/WebSocket signalling; protocol test peer only', unrealVideoAudioGameplay: 'NOT TESTED', node:process.version}, null, 2));
} finally {
  for (const ws of clients) if (ws.readyState !== WebSocket.CLOSED) ws.terminate();
  if (processHandle.exitCode === null) { processHandle.kill(); await once(processHandle, 'exit'); }
  fs.rmSync(temporary, {recursive:true, force:true});
}
