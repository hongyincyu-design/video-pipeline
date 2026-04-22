"""
FastAPI server wrapping make_video.py + upload_youtube.py.

Endpoints
---------
GET  /                       — mobile-friendly web UI (paste JSON, hit submit)
POST /api/videos             — enqueue a job; body = topic spec JSON (same as topics/*.json)
GET  /api/videos             — list all jobs
GET  /api/videos/{task_id}   — get one job's status + log
GET  /api/videos/{task_id}/log   — plain text log (for tailing)

Jobs run serially in a background worker (PowerPoint COM is single-threaded).

Run:
    python api_server.py            # localhost:8000
    python api_server.py --port 8765 --token MYSECRET
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import secrets
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent
TOPICS_DIR = ROOT / "topics"
OUTPUT_DIR = ROOT / "output"
TOPICS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# ---------- Job model ----------

@dataclass
class Job:
    task_id: str
    slug: str
    status: str = "queued"      # queued / running / done / failed
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    privacy: str = "private"
    youtube_url: str | None = None
    error: str | None = None
    log: list[str] = field(default_factory=list)

    def append_log(self, line: str) -> None:
        self.log.append(line.rstrip())

    def public_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # trim log for list views
        return d


JOBS: dict[str, Job] = {}
QUEUE: asyncio.Queue[str] = asyncio.Queue()


# ---------- Helpers ----------

def slugify(text: str) -> str:
    text = re.sub(r"[^\w\u4e00-\u9fff\-]+", "_", text.lower()).strip("_")
    return text or f"job_{secrets.token_hex(3)}"


def write_spec(spec: dict[str, Any]) -> tuple[Path, str]:
    """Write the spec to topics/<slug>.json and return (path, slug)."""
    base = spec.get("output_name") or spec.get("title") or "untitled"
    slug = slugify(base)[:60]
    # dedupe if already exists
    path = TOPICS_DIR / f"{slug}.json"
    if path.exists():
        slug = f"{slug}_{secrets.token_hex(2)}"
        path = TOPICS_DIR / f"{slug}.json"
    path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    return path, slug


async def run_subprocess(job: Job, args: list[str]) -> int:
    """Run a subprocess, streaming stdout+stderr into job.log."""
    job.append_log(f"$ {' '.join(args)}")
    proc = await asyncio.create_subprocess_exec(
        *args,
        cwd=str(ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert proc.stdout is not None
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        try:
            job.append_log(line.decode("utf-8", errors="replace"))
        except Exception:
            job.append_log(repr(line))
    return await proc.wait()


async def process_job(task_id: str) -> None:
    job = JOBS[task_id]
    job.status = "running"
    job.started_at = time.time()
    spec_path = TOPICS_DIR / f"{job.slug}.json"
    try:
        # 1) make_video.py
        rc = await run_subprocess(
            job,
            [sys.executable, str(ROOT / "make_video.py"), str(spec_path.relative_to(ROOT))],
        )
        if rc != 0:
            raise RuntimeError(f"make_video.py exited with {rc}")

        # 2) upload_youtube.py
        rc = await run_subprocess(
            job,
            [
                sys.executable,
                str(ROOT / "upload_youtube.py"),
                str(spec_path.relative_to(ROOT)),
                "--privacy",
                job.privacy,
            ],
        )
        if rc != 0:
            raise RuntimeError(f"upload_youtube.py exited with {rc}")

        # 3) parse YouTube URL from log
        full_log = "\n".join(job.log)
        m = re.search(r"https://www\.youtube\.com/watch\?v=[\w-]+", full_log)
        if m:
            job.youtube_url = m.group(0)
        job.status = "done"
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
    finally:
        job.finished_at = time.time()


async def worker() -> None:
    while True:
        task_id = await QUEUE.get()
        try:
            await process_job(task_id)
        except Exception as exc:
            JOBS[task_id].error = f"worker crash: {exc}"
            JOBS[task_id].status = "failed"
        finally:
            QUEUE.task_done()


# ---------- FastAPI app ----------

app = FastAPI(title="video-pipeline API", version="0.1")

AUTH_TOKEN: str | None = None  # set from CLI --token


async def require_token(request: Request) -> None:
    if AUTH_TOKEN is None:
        return
    header = request.headers.get("authorization", "")
    provided = header.removeprefix("Bearer ").strip()
    if provided != AUTH_TOKEN:
        # also accept ?token=... query param (for easy mobile browser use)
        q = request.query_params.get("token", "")
        if q != AUTH_TOKEN:
            raise HTTPException(401, "invalid or missing token")


class SpecBody(BaseModel):
    spec: dict[str, Any]
    privacy: str = "private"


@app.on_event("startup")
async def _startup() -> None:
    asyncio.create_task(worker())


@app.get("/", response_class=HTMLResponse)
async def home() -> str:
    return INDEX_HTML


@app.post("/api/videos", dependencies=[Depends(require_token)])
async def create_job(body: SpecBody) -> dict[str, Any]:
    if body.privacy not in ("private", "unlisted", "public"):
        raise HTTPException(400, "privacy must be private / unlisted / public")
    if "slides" not in body.spec:
        raise HTTPException(400, "spec must contain 'slides'")
    path, slug = write_spec(body.spec)
    task_id = uuid.uuid4().hex[:12]
    JOBS[task_id] = Job(task_id=task_id, slug=slug, privacy=body.privacy)
    await QUEUE.put(task_id)
    return {"task_id": task_id, "slug": slug, "spec_path": str(path.relative_to(ROOT))}


@app.get("/api/videos", dependencies=[Depends(require_token)])
async def list_jobs() -> dict[str, Any]:
    return {
        "jobs": [
            {
                "task_id": j.task_id,
                "slug": j.slug,
                "status": j.status,
                "youtube_url": j.youtube_url,
                "error": j.error,
                "created_at": j.created_at,
                "finished_at": j.finished_at,
            }
            for j in sorted(JOBS.values(), key=lambda x: x.created_at, reverse=True)
        ]
    }


@app.get("/api/videos/{task_id}", dependencies=[Depends(require_token)])
async def get_job(task_id: str) -> dict[str, Any]:
    job = JOBS.get(task_id)
    if not job:
        raise HTTPException(404, "task not found")
    return job.public_dict()


@app.get("/api/videos/{task_id}/log", response_class=PlainTextResponse,
         dependencies=[Depends(require_token)])
async def get_job_log(task_id: str) -> str:
    job = JOBS.get(task_id)
    if not job:
        raise HTTPException(404, "task not found")
    return "\n".join(job.log)


# ---------- Inline HTML UI ----------

INDEX_HTML = """<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Video Pipeline</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin:0; padding:16px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         background:#1e2761; color:#e8edff; min-height:100vh; }
  h1 { font-size:20px; margin:0 0 16px; }
  textarea { width:100%; min-height:240px; padding:10px; border-radius:8px; border:1px solid #3a4894;
             background:#0f143a; color:#e8edff; font-family: Consolas, monospace; font-size:13px; }
  input, select { width:100%; padding:10px; border-radius:8px; border:1px solid #3a4894;
                  background:#0f143a; color:#e8edff; font-size:14px; }
  label { display:block; font-size:12px; opacity:.7; margin:10px 0 4px; }
  button { width:100%; padding:14px; border-radius:8px; border:none; background:#ffd166; color:#1e2761;
           font-weight:700; font-size:16px; cursor:pointer; margin-top:12px; }
  button:disabled { opacity:.5; }
  .job { border:1px solid #3a4894; border-radius:8px; padding:10px; margin:10px 0; font-size:13px; }
  .status { display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; }
  .queued { background:#6b7280; } .running { background:#f59e0b; }
  .done { background:#10b981; } .failed { background:#ef4444; }
  a { color:#ffd166; } pre { white-space:pre-wrap; word-break:break-all; font-size:11px; opacity:.7; }
</style>
</head>
<body>
<h1>🎬 Video Pipeline</h1>

<label>Topic spec JSON（同 topics/*.json 格式）</label>
<textarea id="spec" placeholder='{"title":"...","slides":[...]}'></textarea>

<label>Privacy</label>
<select id="privacy">
  <option value="private" selected>private</option>
  <option value="unlisted">unlisted</option>
  <option value="public">public</option>
</select>

<label>Auth token（若伺服器有設）</label>
<input id="token" type="password" placeholder="optional" autocomplete="off">

<button id="submit">送出</button>

<h1 style="margin-top:24px;font-size:16px;">近期任務</h1>
<div id="jobs">載入中…</div>

<script>
const tokenInput = document.getElementById('token');
tokenInput.value = localStorage.getItem('vp_token') || '';
tokenInput.addEventListener('change', () => localStorage.setItem('vp_token', tokenInput.value));

function authHeader() {
  const t = tokenInput.value.trim();
  return t ? { 'Authorization': 'Bearer ' + t } : {};
}

async function refresh() {
  try {
    const r = await fetch('/api/videos', { headers: authHeader() });
    if (!r.ok) { document.getElementById('jobs').textContent = '需要 token'; return; }
    const data = await r.json();
    document.getElementById('jobs').innerHTML = data.jobs.map(j => `
      <div class="job">
        <div><span class="status ${j.status}">${j.status}</span> <b>${j.slug}</b></div>
        ${j.youtube_url ? `<div>🔗 <a href="${j.youtube_url}" target="_blank">${j.youtube_url}</a></div>` : ''}
        ${j.error ? `<pre>${j.error}</pre>` : ''}
      </div>
    `).join('') || '<em>尚無任務</em>';
  } catch (e) { console.error(e); }
}

document.getElementById('submit').onclick = async () => {
  const btn = document.getElementById('submit');
  btn.disabled = true; btn.textContent = '送出中…';
  try {
    const spec = JSON.parse(document.getElementById('spec').value);
    const privacy = document.getElementById('privacy').value;
    const r = await fetch('/api/videos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeader() },
      body: JSON.stringify({ spec, privacy }),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(JSON.stringify(data));
    alert('已送出，task_id = ' + data.task_id);
    refresh();
  } catch (e) {
    alert('錯誤：' + e.message);
  } finally {
    btn.disabled = false; btn.textContent = '送出';
  }
};

refresh();
setInterval(refresh, 3000);
</script>
</body>
</html>"""


# ---------- CLI entry ----------

def main() -> None:
    global AUTH_TOKEN
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--token", default=os.environ.get("VP_TOKEN"),
                    help="shared secret; clients must send Authorization: Bearer <token>")
    args = ap.parse_args()
    AUTH_TOKEN = args.token
    if AUTH_TOKEN:
        print(f"[auth] bearer token required (length={len(AUTH_TOKEN)})")
    else:
        print("[auth] NO TOKEN — API is open; only use on trusted networks")
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
