#!/usr/bin/env python3
"""Read-only host probes. This is evidence, not an Unreal/Windows compatibility test."""
import datetime, json, os, pathlib, platform, shutil, subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
def run(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=20)
        return {"command": args, "exit_code": p.returncode,
                "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"command": args, "unavailable": str(e)}

report = {
    "checked_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "platform": platform.platform(), "workspace": str(ROOT),
    "scope": "Managed remote Linux container; no access to user's Windows desktop",
    "tools": {x: shutil.which(x) for x in ["UnrealEditor", "UnrealEditor-Cmd", "UnrealBuildTool", "dotnet", "cl.exe", "pwsh", "blender", "node", "npm", "python3", "g++", "ffmpeg", "nvidia-smi"]},
    "disk": dict(zip(["total", "used", "free"], shutil.disk_usage(ROOT))),
    "gpu_devices": [str(p) for pattern in ["nvidia*", "dri/*"] for p in pathlib.Path("/dev").glob(pattern)],
    "probes": [run(x) for x in [["git", "status", "--short", "--branch"], ["node", "--version"], ["npm", "--version"], ["blender", "--version"], ["g++", "--version"], ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=s=128x128:d=0.1", "-c:v", "h264_nvenc", "-f", "null", "-"]]],
    "unreal_build": "BLOCKED: no engine or Windows compiler/SDK installed",
    "pixel_streaming": "BLOCKED: no Unreal executable or hardware encoder; no playable URL",
}
for name in ["memory.max", "cpu.max"]:
    p = pathlib.Path("/sys/fs/cgroup") / name
    report[name] = p.read_text().strip() if p.exists() else "unavailable"
path = ROOT / "Docs/PathOfDawnUnreal/Evidence/environment-probe.json"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(path)
