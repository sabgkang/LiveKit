This is originally tested on PC4090

| 檔案／目錄 | 用途 |
|---|---|
| compose.yaml | 管理 LiveKit Server、Agent、網頁三個容器 |
| runtime/livekit.yaml | 自架 LiveKit Server 的設定，包含連接埠及自架憑證 |
| agent/ | Python 語音 Agent，串接 VAD、STT、LLM、TTS |
| web/ | 瀏覽器對話介面與 token 後端 |
| .env | 自架憑證、Cloud 推論憑證及模型設定 |
| scripts/ | 整套服務的初始化、啟動與驗證工具 |
| tests/ | 程式測試 |

LiveKit Server 本身使用官方 Docker image：livekit/livekit-server:v1.13.10，因此這個目錄沒有它的伺服器原始碼；但它的部署與設定都在這裡。

目前的分工是：

```text
本機瀏覽器 ↔ 本機 LiveKit Server ↔ 本機 Agent
                                      ↕
                              LiveKit Cloud 推論
                              STT／LLM／TTS
```

所以，房間與影音傳輸已經自架在這台機器上；AI 推論目前使用雲端。
