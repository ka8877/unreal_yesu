const viewport = document.querySelector('#viewport');
const status = document.querySelector('#status');
let frame;
let lastBuild;
let playerBuild;
const openPlayer = event => {
  event?.preventDefault(); event?.stopPropagation();
  frame?.remove();
  frame = document.createElement('iframe');
  frame.title = 'Unreal Engine Pixel Streaming';
  frame.allow = 'autoplay; fullscreen; pointer-lock';
  const query = new URLSearchParams({ss: `ws://${location.host}`, AutoConnect: 'true', AutoPlayVideo: 'false', StartVideoMuted: 'false', UseMic: 'false', UseCamera: 'false', HoveringMouse: 'false', MatchViewportRes: 'false'});
  frame.src = `/player/player.html?${query}`;
  playerBuild = lastBuild;
  viewport.replaceChildren(frame);
  document.querySelector('#reconnect').disabled = false;
  document.querySelector('#fullscreen').disabled = false;
};
document.querySelector('#start').addEventListener('click', openPlayer);
document.querySelector('#reconnect').addEventListener('click', event => {
  frame?.remove(); frame = undefined;
  // Closing the previous WebSocket frees the one-controller gate before reconnect.
  setTimeout(() => openPlayer(event), 500);
});
document.querySelector('#fullscreen').addEventListener('click', () => viewport.requestFullscreen());
async function refresh() {
  try {
    const response = await fetch('/status', {cache: 'no-store'});
    if (!response.ok) throw new Error('Host unavailable');
    const state = await response.json();
    const video = frame?.contentDocument?.querySelector('video');
    const received = state.streamerRegistered && video && video.videoWidth > 0 && video.currentTime > 0;
    const changed = playerBuild && playerBuild !== state.hostBuildId;
    status.textContent = `호스트 ${state.hostBuildId} · ${changed ? '업데이트됨 · 재연결하세요' : received ? '영상 수신 중' : state.streamerRegistered ? '게임 연결 대기' : '게임 시작 중'} · 제어 ${state.controllers}/1`;
    lastBuild = state.hostBuildId;
  } catch { status.textContent = '호스트 연결 끊김 · 업데이트 중이면 잠시 후 재연결하세요'; }
}
setInterval(refresh, 2000); refresh();
