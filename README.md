# 主題 → PPT → 旁白 → MP4 → YouTube  Pipeline

一條龍把任何技術主題做成介紹影片並上傳到 YouTube，並附一個 Claude Code Skill，讓你可以直接對 Claude 說「做個 RSI 的教學影片」就自動跑完整個流程。

---

## ⚡ 快速開始（新機器三步驟）

### 0. 前置需求
- Windows 10/11
- **Microsoft PowerPoint**（必要，pipeline 用 PowerPoint COM 把投影片轉成 PNG）
- Python 3.10+
- Claude Code

### 1. Clone repo
```powershell
cd $HOME
git clone https://github.com/<你的帳號>/video-pipeline.git
cd video-pipeline
```

### 2. 跑一鍵安裝腳本
```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1
```
這會幫你：
- 安裝 Python 套件（`requirements.txt`）
- 透過 winget 安裝 FFmpeg
- 把 `skills/topic-to-youtube-video` 複製到 `~/.claude/skills/`，並把路徑自動代換成這台機器的實際位置

### 3. 放 YouTube OAuth 憑證
依照下方「YouTube API 憑證申請」申請完，把 `client_secret.json` 放到這個 repo 根目錄。

完成後，直接對 Claude Code 說：
> 做個 MACD 的教學影片

Claude 會自動：研究主題 → 寫投影片 JSON → 產影片 → 上傳 YouTube（預設 private）。

---

## 目錄結構
```
video-pipeline/
├── make_video.py            # PPTX + Edge-TTS 旁白 → MP4（含字幕）
├── upload_youtube.py        # MP4 → 你的 YouTube 頻道
├── setup.ps1                # 一鍵安裝腳本
├── requirements.txt         # Python 依賴
├── topics/
│   ├── kd_indicator.json    # 範例：KD 指標
│   ├── bollinger_bands.json
│   └── rsi_indicator.json
├── skills/
│   └── topic-to-youtube-video/   # Claude Code Skill
│       ├── SKILL.md
│       └── references/json_schema.md
├── output/                  # 產出的 PPTX / MP4 / SRT（.gitignore）
├── client_secret.json       # ← 你要自己申請、放這裡（.gitignore）
└── token.json               # ← 第一次授權後自動產生（.gitignore）
```

## 📱 手機 / 遠端使用（方案 A）

想在手機上觸發？啟動 API 伺服器 + Cloudflare Tunnel，就能在手機瀏覽器送任務：

```powershell
# 1. 設 token
$env:VP_TOKEN = "your-long-random-token"

# 2. 啟動 API server
powershell -ExecutionPolicy Bypass -File run_server.ps1

# 3. 另開視窗：Cloudflare Tunnel（會印出公開 URL）
cloudflared tunnel --url http://localhost:8000
```

完整說明見 [docs/mobile_setup.md](docs/mobile_setup.md)。

---

## 手動使用（不透過 Claude）
```bash
# 1) 編輯 topics/<主題>.json（或複製 kd_indicator.json 改）
# 2) 生影片
python make_video.py topics/<主題>.json
# 3) 上傳 YouTube
python upload_youtube.py topics/<主題>.json --privacy private
```

`--privacy` 可選：
- `private`（預設）：只有你自己能看，最安全
- `unlisted`：有連結的人才看得到
- `public`：公開上架

## 主題 JSON 格式
詳見 [skills/topic-to-youtube-video/references/json_schema.md](skills/topic-to-youtube-video/references/json_schema.md)

```json
{
  "title": "主題名稱",
  "subtitle": "副標",
  "voice": "zh-TW-HsiaoChenNeural",
  "rate": "+10%",
  "output_name": "檔名（不含副檔名）",
  "slides": [
    { "type": "title",    "title": "...", "subtitle": "...", "narration": "...", "subtitle_text": "..." },
    { "type": "bullets",  "heading": "...", "bullets": ["...","..."], "narration": "...", "subtitle_text": "..." },
    { "type": "code",     "heading": "...", "code": "...", "caption": "...", "narration": "...", "subtitle_text": "..." },
    { "type": "closing",  "heading": "...", "bullets": ["..."], "tagline": "...", "narration": "...", "subtitle_text": "..." }
  ]
}
```

### 旁白撰寫小訣竅
- 英文縮寫、符號要拆字母，例如「K D」、「R S V t」、「x f underscore Stochastic」，Edge-TTS 念起來才清楚。
- 一張投影片約 20–30 秒旁白最順。
- `rate` 可調 `-10%` ~ `+20%`，中文嗓音 `+10%` 最自然。

### 其他可用中文嗓音
- `zh-TW-HsiaoChenNeural`（女聲，預設）
- `zh-TW-HsiaoYuNeural`（女聲，較柔）
- `zh-TW-YunJheNeural`（男聲）
- `zh-CN-XiaoxiaoNeural`（女聲，中國口音）

---

## YouTube API 憑證申請（一次性，約 10 分鐘）

### 步驟 1：建立 Google Cloud 專案
1. 到 <https://console.cloud.google.com/>。
2. 頂端專案選單 → 「New Project」，名稱自訂（例如 `yt-upload-bot`）→ 建立。

### 步驟 2：啟用 YouTube Data API v3
1. 左側選單 → **APIs & Services** → **Library**。
2. 搜尋 **YouTube Data API v3** → 點 **Enable**。

### 步驟 3：設定 OAuth 同意畫面
1. 左側選單 → **APIs & Services** → **OAuth consent screen**。
2. User Type 選 **External**（免費帳號只能選這個）→ Create。
3. 填 App name（例如 `YT Upload Bot`）、User support email、Developer email → Save。
4. Scopes 頁跳過（Save and Continue）。
5. Test users 頁 → **Add Users** → 加入你自己的 Google 帳號（就是有 YouTube 頻道那個）→ Save。
6. 回到 Dashboard。**不要按 Publish**，保留在 Testing 狀態即可。

### 步驟 4：建立 OAuth Client ID
1. 左側選單 → **APIs & Services** → **Credentials**。
2. **Create Credentials** → **OAuth client ID**。
3. Application type 選 **Desktop app**，名稱自訂 → Create。
4. 彈出視窗點 **Download JSON**，檔案改名為 `client_secret.json`，放到 repo 根目錄。

### 步驟 5：第一次授權
```bash
python upload_youtube.py topics/kd_indicator.json --privacy private
```
- 會自動開瀏覽器 → 登入 Google（選有 YouTube 頻道的帳號）→ 「允許」。
- 授權成功後腳本自動存 `token.json`，以後直接用不用再登入。
- 畫面若看到「Google hasn't verified this app」，點 **Advanced** → **Go to (unsafe)**，
  因為這是你自己做的 app，在 Testing 狀態下是正常的。

### 配額說明
- YouTube Data API 每日配額 10,000 單位，上傳一次約耗 1,600 單位 → 一天可上傳 ~6 部。
- 配額重置時間：太平洋時間午夜（約台灣下午 3-4 點）。

---

## 在新機器上重建的 checklist
1. ✅ Windows 10/11 + Microsoft PowerPoint
2. ✅ Python 3.10+
3. ✅ `git clone` 本 repo
4. ✅ 跑 `setup.ps1`
5. ✅ 複製（或重新申請）`client_secret.json` 到 repo 根目錄
6. ✅ 複製 `token.json` 過去（可省略；第一次跑會重新授權）
7. ✅ 開 Claude Code，在任何資料夾都能用 `做個 XXX 的教學影片` 觸發 skill
