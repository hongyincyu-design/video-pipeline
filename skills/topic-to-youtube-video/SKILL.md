---
name: topic-to-youtube-video
description: 從「主題名稱」一條龍做出介紹影片並上傳 YouTube — 先上網搜尋該主題資料、寫出 7-8 張投影片的腳本 JSON、用 Edge-TTS 中文女聲旁白 + FFmpeg 合成約 3 分鐘 MP4（含燒入字幕），最後用 OAuth 上傳到使用者的 YouTube 頻道（預設 private）。只要使用者提到「幫我做一集 / 做個介紹影片 / 做教學影片 / 上 YouTube / YT 影片」並指定一個技術/交易/程式主題（例如 MACD、RSI、布林通道、XQ 某函數、某演算法、某工具），就應該使用這個 skill，即使使用者沒有明確說「影片」——例如「介紹一下 RSI 指標並上傳」也應該觸發。不適用於：純粹的資料查詢、只要 PPT 不要影片、只要字幕稿、非繁體中文主題、使用者已經自己寫好腳本。
---

# Topic → PPT → Narrated Video → YouTube

把任何技術主題做成一部約 3 分鐘的繁體中文介紹影片，並上傳到使用者的 YouTube 頻道。整條 pipeline 的 Python 腳本已經寫好並就緒，這個 skill 負責：(1) 研究主題、(2) 把研究成果轉成指定格式的 JSON、(3) 叫用 pipeline 腳本、(4) 回報結果。

## Pipeline 位置（絕對路徑）

```
%PIPELINE_PATH%\
├── make_video.py            # JSON → PPTX → MP4（含字幕）
├── upload_youtube.py        # MP4 → YouTube
├── topics\
│   └── kd_indicator.json    # 已經跑通的範例，請仔細參考
├── client_secret.json       # YouTube OAuth 憑證（使用者自備）
└── token.json               # 授權後自動產生
```

工作目錄固定在 `%PIPELINE_PATH%`。所有命令都從這裡執行。

## 工作流程（固定五步驟）

### 步驟 1：確認主題與檢查前置條件

從使用者訊息抽出主題名稱（例如「MACD 技術指標」、「RSI 相對強弱指標」）。順手：

- 把主題轉成檔名 slug（英文小寫、底線分隔，例如 `macd_indicator`、`rsi_indicator`）
- 檢查 `client_secret.json` 是否存在。不存在的話先停下來，引導使用者完成 `README.md` 裡「YouTube API 憑證申請」步驟 1–5，不要硬跑到上傳階段才爆炸。

### 步驟 2：上網研究主題

用 WebSearch / WebFetch 搜集關於該主題的核心內容，至少涵蓋：

- 定義與原理（是什麼、怎麼算）
- 關鍵參數與公式
- 程式語法範例（如果是 XQ / TradingView / Python 之類的，找具體 code snippet）
- 實戰應用（交叉訊號、進出場條件）
- 常見坑／注意事項

建議搜尋模式：先中文官方文件或部落格（例如 XQ 官方部落格 `xq.com.tw`、Mr.Market、StockFeel），再補英文 Wikipedia 或演算法細節。蒐集到足夠資料為止，大概 3-5 筆 WebSearch / WebFetch 就夠。

### 步驟 3：撰寫主題 JSON

**務必**先 Read 一次 `topics\kd_indicator.json` 當成 canonical 模板，再仿照它寫新的 JSON。

檔名：`topics\<slug>.json`。Schema 關鍵欄位見 [references/json_schema.md](references/json_schema.md)。

#### 核心原則：narration 與 subtitle_text 是兩份文本

這是整個 skill 最容易做錯的地方。請把兩者視為兩種不同的文本類型：

- `narration`：**給 Edge-TTS 唸的**。英文縮寫、代號、符號都要拆成一個字母一個字母、或念出來的字（例如 `underscore`、`bracket`），否則 TTS 會把「KD」念成「凱迪」或整串英文亂念。
- `subtitle_text`：**顯示在畫面底部的**。用乾淨、可讀的寫法，用 `｜` 當字幕切段符號（一個 `｜` = 一行新字幕）。

| 寫在 narration | 寫在 subtitle_text |
|---|---|
| `K D 指標` | `KD 指標` |
| `R S V t` | `RSVt` |
| `x f underscore Stochastic` | `xf_Stochastic` |
| `k 中括號 1` | `k[1]` |
| `百分之二十` | `20%` |
| `反斜線 n` | `\n` |

寫旁白的時候腦中默念一遍，如果自己都不確定 TTS 會唸對就拆得更細。

#### 字數 / 時間預算

- 每張投影片旁白 **20-30 秒**（中文約 50-90 字，因為 Edge-TTS 預設 `rate: "+10%"` 唸得比較快）
- 總共 **7-8 張投影片**，目標影片約 3 分鐘
- 太長會超時、太短會顯得倉促

#### 投影片結構（7-8 張的典型配比）

1. `title` — 開場（約 15 秒旁白）
2. `bullets` — 這個主題是什麼（4 點左右）
3. `code` — 核心函數／公式
4. `bullets` — 參數解釋（4-5 點）
5. `code` — 完整範例程式
6. `code` — 應用案例（交叉判斷之類）
7. `bullets` — 實戰技巧
8. `closing` — 重點回顧（4 點 + tagline）

根據主題調整，不要死守結構。非程式類主題可以把 `code` 換成 `bullets`。

### 步驟 4：執行 `make_video.py`

```bash
cd %PIPELINE_PATH%
python make_video.py topics\<slug>.json
```

預期輸出：

```
[done] 影片長度約 3 分 XX 秒
影片：...\<slug>.mp4
字幕：...\<slug>.srt
```

如果長度**顯著**偏離 3 分鐘（例如 > 3:30 或 < 2:30），建議回去微調 JSON（刪減或補充旁白），**不要**硬改 rate 把聲音變太快或太慢。如果只差 10-20 秒則不用處理——使用者同意「約 3 分鐘」的彈性。

### 步驟 5：上傳 YouTube

```bash
cd %PIPELINE_PATH%
python upload_youtube.py topics\<slug>.json --privacy private
```

預設隱私 = `private`，讓使用者自己到 YouTube Studio 預覽後再改成 unlisted/public。除非使用者明確說「直接公開」或「分享連結」再改 `--privacy public` 或 `--privacy unlisted`。

上傳成功後會印出類似：

```
上傳：<slug>.mp4  (X.X MB)
標題：<主題> | <副標>
隱私：private
  上傳中… 100%

完成！影片網址：https://www.youtube.com/watch?v=XXXXXXXXXXX
```

把最後那個 URL 明顯地回報給使用者。

## 錯誤處理

| 情況 | 處理方式 |
|---|---|
| `client_secret.json` 不存在 | 引導使用者做 README 步驟 1-5 申請憑證，**不要**跑 upload |
| `access_denied: automl-step1 未完成驗證程序` | 告訴使用者把自己的 Google Account 加到 OAuth consent screen 的 Test users 清單 |
| `make_video.py` 中途失敗 | 先看 stderr 找到哪個 FFmpeg 步驟爆炸；常見是 PowerPoint COM 沒啟動（重啟電腦或關閉背景 PPT 程序） |
| 影片超過 4 分鐘 | 回去刪 `narration` 和 `subtitle_text` 裡的冗詞，或合併相鄰投影片 |
| PPTX 中的投影片頁數和 JSON 不符 | 通常是投影片標題換行被當成額外頁；檢查 PPTX 再報告 |

## 回報格式

完成後用這種結構回報給使用者（繁體中文）：

```
上傳成功 🎉

影片網址：https://www.youtube.com/watch?v=XXXXXXXXXXX

- 隱私：private（請到 YouTube Studio 確認後手動改成 unlisted 或 public）
- 長度：X 分 XX 秒
- 主題 JSON：topics\<slug>.json（之後想改可以重跑）

下一步建議：
1. 點開上方連結檢查影片與字幕
2. 到 YouTube Studio 上傳 .srt 檔當 CC 字幕（畫質比燒入的好）
3. 隱私改成 unlisted / public
```

## 重要設計約束（請記住）

- **聲音固定** Edge-TTS `zh-TW-HsiaoChenNeural`（女聲）。除非使用者指定別的嗓音，不要自己改。
- **字幕永遠燒入**，除非使用者明確說「不要字幕」才加 `--no-subs`。燒入字幕的同時還會另存 SRT 檔，不衝突。
- **隱私預設 private**。這是故意的安全網——讓使用者自己驗收後再公開。
- **不要自己幫使用者把 private 改成 public**。就算影片看起來完美也不要。
- **不要嘗試用 PowerPoint 以外的方式產 PPTX 圖片**。make_video.py 用 PowerPoint COM，強行換 libreoffice 會破壞排版一致性。

## 參考資料

- [references/json_schema.md](references/json_schema.md) — 主題 JSON 完整欄位說明
- `%PIPELINE_PATH%\topics\kd_indicator.json` — 活生生的範例
- `%PIPELINE_PATH%\README.md` — Pipeline 原始使用文件（含 YouTube 憑證申請步驟）
