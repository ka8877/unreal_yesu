// Application wrapper around Epic's pinned signalling library; no alternate game implementation.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const here = path.dirname(fileURLToPath(import.meta.url));
const configPath = process.argv[process.argv.indexOf('--config') + 1];
if (!process.argv.includes('--config') || !configPath) throw new Error('Use --config <local config JSON>');
const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
for (const name of ['port', 'streamerPort']) {
  if (!Number.isInteger(config[name]) || config[name] < 1024 || config[name] > 65535) throw new Error(`Invalid ${name}`);
}
if (!/^[A-Za-z0-9][A-Za-z0-9_.-]{2,79}$/.test(config.buildId)) throw new Error('Invalid buildId');
const vendor = path.resolve(config.vendor);
const require = createRequire(path.join(vendor, 'package.json'));
const { SignallingServer, InitLogging } = require('@epicgames-ps/lib-pixelstreamingsignalling-ue5.8');
const frontend = path.join(vendor, 'SignallingWebServer', 'www');
if (!fs.existsSync(path.join(frontend, 'player.html'))) throw new Error('Run PrepareStreaming.ps1 first');
InitLogging({ logDir: config.logRoot, logLevelConsole: 'info', logLevelFile: 'info' });
const allowedHosts = new Set([`127.0.0.1:${config.port}`, `localhost:${config.port}`]);
const allowedOrigins = new Set([...allowedHosts].map(value => `http://${value}`));
const loopback = address => address === '127.0.0.1' || address === '::1' || address === '::ffff:127.0.0.1';
let signalling;
const server = http.createServer((request, response) => {
  response.setHeader('Cache-Control', 'no-store');
  response.setHeader('X-Content-Type-Options', 'nosniff');
  response.setHeader('Referrer-Policy', 'no-referrer');
  response.setHeader('X-Frame-Options', 'SAMEORIGIN');
  if (!loopback(request.socket.remoteAddress) || !allowedHosts.has(request.headers.host)) {
    response.writeHead(403).end('Local host only'); return;
  }
  if (request.method !== 'GET' && request.method !== 'HEAD') { response.writeHead(405).end(); return; }
  let pathname;
  try { pathname = decodeURIComponent(new URL(request.url, `http://${request.headers.host}`).pathname); }
  catch { response.writeHead(400).end(); return; }
  if (pathname === '/status') {
    const streamers = signalling?.streamerRegistry.streamers ?? [];
    response.setHeader('Content-Type', 'application/json; charset=utf-8');
    response.end(JSON.stringify({ hostBuildId: config.buildId, streamerRegistered: streamers.some(s => s.streaming), controllers: signalling?.playerRegistry.listPlayers().filter(p => p.subscribedStreamer).length ?? 0, maxControllers: 1, scope: 'localhost', mediaVerified: false }));
    return;
  }
  let root, relative;
  if (pathname === '/' || pathname === '/index.html') { root = here; relative = 'index.html'; }
  else if (pathname === '/toolbar.js') { root = here; relative = 'toolbar.js'; }
  else if (pathname.startsWith('/player/')) { root = frontend; relative = pathname.slice('/player/'.length); }
  else { response.writeHead(404).end(); return; }
  const full = path.resolve(root, relative);
  if (!full.startsWith(path.resolve(root) + path.sep) || full.includes('\0')) { response.writeHead(403).end(); return; }
  const ext = path.extname(full).toLowerCase();
  const mime = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css', '.png': 'image/png', '.svg': 'image/svg+xml', '.jpg': 'image/jpeg', '.woff2': 'font/woff2' }[ext];
  if (!mime || !fs.existsSync(full) || !fs.statSync(full).isFile()) { response.writeHead(404).end(); return; }
  response.setHeader('Content-Type', mime);
  if (request.method === 'HEAD') { response.end(); return; }
  fs.createReadStream(full).on('error', () => response.destroy()).pipe(response);
});
signalling = new SignallingServer({
  httpServer: server,
  streamerPort: config.streamerPort,
  peerOptions: { iceServers: [] },
  maxSubscribers: 1,
  playerKeepaliveTimeout: 15000,
  // Omit sfuPort: no SFU, REST API, editor or MCP listener is enabled.
  streamerWsOptions: {
    host: '127.0.0.1',
    verifyClient: info => loopback(info.req.socket.remoteAddress) && signalling.streamerRegistry.streamers.length === 0
  },
  playerWsOptions: {
    verifyClient: info => loopback(info.req.socket.remoteAddress) && allowedHosts.has(info.req.headers.host) && allowedOrigins.has(info.origin) && signalling.playerRegistry.listPlayers().length === 0
  }
});
server.listen(config.port, '127.0.0.1', () => console.log(`PathOfDawn ${config.buildId}: http://127.0.0.1:${config.port}/ (localhost only)`));
