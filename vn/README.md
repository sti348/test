# School World · 视觉小说 CG / 背景

用图像模型（`gpt-image-2.6-flare`，OpenAI Images API，quality high，原生 16:9；试画风用 1536×864、每轮少量）画视觉小说背景；地图生成器（`megaschool/`）只当作地点设定参考。

| 文件 | 内容 |
| --- | --- |
| `style.md` | 世界观与视觉规则（巨物尺度、窗户成组、暮色、无文字、无人物） |
| `styles.json` | 候选画风（媒介与技法的描述），用于对比挑选 |
| `scenes.json` | 镜头清单：26 个地点、47 张图（暮色 / 白天 / 深夜变体） |
| `gen.py` | 调用 API 生成、裁成 1920×1080、保存提示词；`styles` 命令做画风对照 |
| `stage.py` + `locations/<地点>/scene.py` | 简模：照着一张主图用方块复刻场景（含画外部分），从新机位渲染构图图，让不同角度的图在结构上连续（暂停中，先定画风） |
| `docs/style_round1.jpg`、`docs/style_round2.jpg` | 两轮画风对照（通用媒介） |
| `styles_anime.json`、`docs/style_anime_*.jpg` | 第三轮：12 种小众日系二次元画风 × 广场、教室（3840×2160 原生；结论：只有 City Pop 及格，其余暗淡、噪点多） |
| `styles_keep.json` | 保留备用的画风提示词（City Pop、C2 侧光、K 日食冷光） |
| `styles_persona.json`、`docs/style_persona.jpg` | 第四轮：3 位虚构作者的个人画风（具体的配色、线条、阴影、天空、构图习惯），巨物感学校图，1536×864；选中 C（精美，但光太强发白） |
| `styles_c.json`、`docs/style_c_round.jpg` | 第五轮：C 的三种修正（控曝光 / 侧光 / 加细节与点缀色）；选中 C2，已存进 `styles_keep.json` |
| `styles_mega.json`、`docs/style_mega.jpg` | 第六轮：巨物压迫感方向的 3 位虚构作者（D 巨碑极简 / E 巴洛克云景 / F 冷色图形），海上空岛；D、F 勉强及格，E 排除 |
| `styles_rich.json`、`docs/style_rich.jpg` | 第七轮：非极简的 3 位虚构作者（G 细密钢笔＋淡彩 / H 层叠透明色片 / I 装饰纹样），躺在海面仰望极高处的空岛，768×1920 竖长条；结论：三种雷同、没有压迫感 |
| `styles_press.json`、`docs/style_press.jpg` | 第八轮：压迫感方向、渲染方式各不相同的 3 位虚构作者（J 剧画浓墨 / K 日食冷光 / L 酸性色彩），天空颜色和光线交给画风决定；J、L 像风格展示图不适合剧情游戏，K 保留 |
| `styles_edge.json`、`docs/style_edge.jpg` | 第九轮：适合剧情背景的克制个人画风（M 金茶与青影 / N 藏青细线 / O 阴天漫射光），空岛边缘鱼眼，1152×1152 |

```bash
python3 vn/gen.py list                       # 镜头清单
python3 vn/gen.py styles forecourt dusk      # 同一场景 × 全部候选画风 -> vn/out/_styles/.../sheet.jpg
python3 vn/gen.py styles forecourt,classroom dusk --set styles_anime.json --tag anime
python3 vn/gen.py run classroom --variants dusk
```

密钥：在 Claude 云端会话里由网络代理注入（不需要环境变量）；本地运行时设 `IMAGE_API_KEY`。

画风对照的经验：第一轮把画风放在一长段世界描述前面，12 种画风几乎全部收敛成同一种精致数字绘画（`docs/style_round1.jpg`）；第二轮改成「画风开头并结尾重申、场景一句话」，差别才明显（`docs/style_round2.jpg`）。
