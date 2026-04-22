# Topic JSON Schema

`make_video.py` 和 `upload_youtube.py` 共用同一份 JSON。

## 頂層欄位

| 欄位 | 必填 | 說明 |
|---|---|---|
| `title` | ✅ | 主題名稱，會成為 YouTube 影片標題前半與標題頁大字 |
| `subtitle` | ⬜ | 副標，標題頁小字 + YouTube 標題後半 |
| `voice` | ⬜ | Edge-TTS 聲音 ID，預設 `zh-TW-HsiaoChenNeural`。其他可選：`zh-TW-HsiaoYuNeural`（柔）、`zh-TW-YunJheNeural`（男聲） |
| `rate` | ⬜ | 語速，預設 `+10%`。可接受範圍 `-20%` ~ `+20%`，中文 `+10%` 最自然。**不建議隨便改**。 |
| `output_name` | ⬜ | 輸出 PPTX/MP4/SRT 共用的檔名，不含副檔名。省略時用 JSON 檔名（不含副檔名） |
| `slides` | ✅ | 投影片陣列，見下方 |

## Slide 物件

每個 slide 的 `type` 欄位決定佈局；所有 type 都共用 `narration` 和 `subtitle_text`。

### 共用欄位

| 欄位 | 必填 | 說明 |
|---|---|---|
| `type` | ✅ | `title` / `bullets` / `code` / `closing` |
| `narration` | ✅ | 給 TTS 唸的文本。英文縮寫、符號需拆字母（見 SKILL.md 表格）。建議 20-30 秒長度（中文 50-90 字） |
| `subtitle_text` | ⬜ | 畫面字幕文本。用乾淨寫法，`｜` 分段。省略時會用 `narration`，但通常效果差，**強烈建議填** |

### type: "title"（開場頁）

```json
{
  "type": "title",
  "title": "KD 技術指標",
  "subtitle": "XQ 全球贏家  程式撰寫介紹",
  "tagline": "從內建函數到黃金交叉選股腳本",
  "narration": "...",
  "subtitle_text": "..."
}
```

`tagline` 選填。`title` / `subtitle` 預設會沿用頂層的同名欄位，這裡可以覆寫。

### type: "bullets"（條列頁）

```json
{
  "type": "bullets",
  "heading": "什麼是 KD 指標？",
  "bullets": [
    "又稱「隨機指標」Stochastic Oscillator",
    "反映收盤價在近 N 日高低區間中的相對位置",
    "K 值：較敏感的快線  ／  D 值：較平滑的慢線",
    "數值介於 0 到 100，常用 20 與 80 為超賣 / 超買界線"
  ],
  "narration": "...",
  "subtitle_text": "..."
}
```

- `bullets` 建議 4-5 點，太多會擠、太少頁面空
- 每點約 20-35 字，太長會被縮小或截字

### type: "code"（程式碼頁）

```json
{
  "type": "code",
  "heading": "XQ 內建函數：Stochastic",
  "code": "// 當前頻率計算\nStochastic(Length, RSVt, Kt, rsv, k, _d);\n\n// 指定頻率跨週期計算\nxf_Stochastic(頻率, Length, RSVt, Kt, rsv, k, _d);",
  "caption": "兩個核心函數：當前頻率用 Stochastic，跨頻率用 xf_Stochastic。",
  "narration": "...",
  "subtitle_text": "..."
}
```

- `code` 用 `\n` 分行。整段最多約 12-15 行，超過會字太小
- `caption` 選填，顯示在程式碼下方作輔助說明（一行為宜）
- 註解用 `//` 在各家平台普遍可接受

### type: "closing"（結尾頁）

```json
{
  "type": "closing",
  "heading": "本集重點回顧",
  "bullets": [
    "Stochastic ／ xf_Stochastic 兩個核心函數",
    "三輸入、三輸出的呼叫模式",
    "cross above / cross below 抓交叉",
    "k[1]、_d[1] 存取歷史值做更精準判斷"
  ],
  "tagline": "下集見！",
  "narration": "...",
  "subtitle_text": "..."
}
```

- 與 `bullets` 類似，但版面更視覺化（深色底 + 金色 tagline）
- `tagline` 是金色大字，通常是「下集見！」「歡迎訂閱！」之類

## 完整範例

直接 Read `%PIPELINE_PATH%\topics\kd_indicator.json` 是最快的方法。那是已經跑通、驗證過的標準樣本。
