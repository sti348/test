# School World · 视觉小说 CG / 背景

用图像模型（`gpt-image-2.6-flare`，OpenAI Images API，quality high，3840×2160 原生 16:9）画视觉小说背景；地图生成器（`megaschool/`）只当作地点设定参考。

| 文件 | 内容 |
| --- | --- |
| `style.md` | 世界观与视觉规则（巨物尺度、窗户成组、暮色、无文字、无人物） |
| `styles.json` | 候选画风（媒介与技法的描述），用于对比挑选 |
| `scenes.json` | 镜头清单：26 个地点、47 张图（暮色 / 白天 / 深夜变体） |
| `gen.py` | 调用 API 生成、裁成 1920×1080、保存提示词；`styles` 命令做画风对照 |
| `stage.py` + `locations/<地点>/scene.py` | 简模：照着一张主图用方块复刻场景（含画外部分），从新机位渲染构图图，让不同角度的图在结构上连续（暂停中，先定画风） |
| `docs/style_round1.jpg`、`docs/style_round2.jpg` | 两轮画风对照（通用媒介） |
| `styles_anime.json`、`docs/style_anime_*.jpg` | 第三轮：12 种小众日系二次元画风 × 广场、教室（3840×2160 原生） |

```bash
python3 vn/gen.py list                       # 镜头清单
python3 vn/gen.py styles forecourt dusk      # 同一场景 × 全部候选画风 -> vn/out/_styles/.../sheet.jpg
python3 vn/gen.py styles forecourt,classroom dusk --set styles_anime.json --tag anime
python3 vn/gen.py run classroom --variants dusk
```

密钥：在 Claude 云端会话里由网络代理注入（不需要环境变量）；本地运行时设 `IMAGE_API_KEY`。

画风对照的经验：第一轮把画风放在一长段世界描述前面，12 种画风几乎全部收敛成同一种精致数字绘画（`docs/style_round1.jpg`）；第二轮改成「画风开头并结尾重申、场景一句话」，差别才明显（`docs/style_round2.jpg`）。
