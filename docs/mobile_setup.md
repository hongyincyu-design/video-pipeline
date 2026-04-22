# 手機遠端使用指南（方案 A）

把家裡 Windows PC 當「影片工廠」，手機透過網頁表單遠端觸發。

---

## 架構

```
[手機瀏覽器] ──https──▶ [Cloudflare Tunnel]
                              │
                              ▼
                   [家裡 PC  api_server.py:8000]
                              │
                              ├─▶ make_video.py  (PPT+TTS+FFmpeg)
                              └─▶ upload_youtube.py
```

---

## 步驟 1：裝好 pipeline 本體

先確認 `setup.ps1` 已成功跑完，`python make_video.py topics\kd_indicator.json` 能正常產影片。

---

## 步驟 2：本機啟動 API 伺服器

```powershell
# 自己設一組長一點的隨機 token（暴露到公網必設）
$env:VP_TOKEN = "ChangeThis_ToASecureRandomString_12345"

# 啟動
powershell -ExecutionPolicy Bypass -File run_server.ps1
```

瀏覽器打開 <http://localhost:8000>，應該看到深藍色的表單頁面。

測試：把 `topics/kd_indicator.json` 的內容貼到 textarea，送出，任務應該出現在清單裡並跑完。

---

## 步驟 3：設定 Cloudflare Tunnel（推薦，免費、無需開 port）

### 3a. 安裝 cloudflared
```powershell
winget install --id Cloudflare.cloudflared
```

### 3b. 登入 Cloudflare（會開瀏覽器要你登入 Cloudflare 帳號）
```powershell
cloudflared tunnel login
```

### 3c. 建立 tunnel（取個名字）
```powershell
cloudflared tunnel create video-pipeline
```
會印出一個 tunnel UUID，同時在 `~/.cloudflared/` 產生 credentials JSON。

### 3d. 設定路由（把一個 subdomain 指到本機 8000）

選項 A（最簡單，Cloudflare 免費子網域）：
```powershell
cloudflared tunnel --url http://localhost:8000
```
會印出類似 `https://fluffy-dragon-1234.trycloudflare.com` 的網址 —— 手機直接用這個。

選項 B（自有網域 + 固定子網域）：
需要先把網域託管到 Cloudflare。建立 `~/.cloudflared/config.yml`：
```yaml
tunnel: <你的-tunnel-uuid>
credentials-file: C:\Users\user\.cloudflared\<uuid>.json

ingress:
  - hostname: video.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
```
然後：
```powershell
cloudflared tunnel route dns video-pipeline video.yourdomain.com
cloudflared tunnel run video-pipeline
```

### 3e. （可選）設定為 Windows 服務自動啟動
```powershell
cloudflared service install
```

---

## 步驟 4：手機使用

1. 瀏覽器打開 tunnel 給的 URL（例如 `https://fluffy-dragon-1234.trycloudflare.com`）
2. 在「Auth token」欄填入你剛剛設的 `VP_TOKEN`（會存在瀏覽器 localStorage，下次不用再填）
3. 把 JSON 貼到 textarea → 送出
4. 清單會每 3 秒自動重整，跑完會顯示 YouTube 網址

**建議做法**：把這個 URL 加到手機主畫面當 PWA icon（Safari：分享 → 加到主畫面）。

---

## 步驟 5：用手機 Claude 寫 JSON 然後貼進來

手機 Claude App（或網頁版）可以：
1. 幫你研究主題
2. 寫出符合格式的 JSON（你可以貼 `skills/topic-to-youtube-video/references/json_schema.md` 當參考）
3. 你複製 JSON → 貼到手機表單 → 送出

想要「打一句話就自動做」的話，繼續看下一節 MCP。

---

## 進階：MCP Server 讓 Claude 直接呼叫（選配）

如果你的 Claude 介面支援 MCP，可以寫一個 MCP server 包住這個 API，讓 Claude 直接以 function-call 的方式送任務。架構：

```
Claude ──MCP──▶ local MCP server (node/python) ──HTTPS──▶ api_server (家裡 PC)
```

這部分因為 Claude 手機 App 目前 MCP 支援還不完整，先等等。如果你用 Claude Desktop 或 Claude Code 在其他機器上，可以再找我做。

---

## 安全提醒

- **一定要設 `VP_TOKEN`**，否則任何人拿到 URL 都能叫你家裡 PC 產影片 + 上傳你的 YouTube
- Token 越長越好（建議 32 字元以上隨機字串）
- 如果不小心洩漏，重新設 `VP_TOKEN` 並重啟 server
- 不要把 `VP_TOKEN` 寫死在任何 commit 進 git 的檔案裡
