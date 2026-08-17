---
name: novel-to-video
description: |
  将 Obsidian 小说/剧本一键转化为竖屏短剧视频。
  触发词：「/novel-to-video」「小说转视频」「第N集做成视频」「把小说拍成短剧」。
  工作流：读取 Obsidian Vault → 提取场景/角色/对白 → 生成图像 → TTS 配音 → Remotion 合成 → 输出 MP4。
---

# /novel-to-video — 小说一键转短剧

> 把 Obsidian 里的故事，变成一条竖屏短视频。

## 架构概览

```
你说 "/novel-to-video 第3集"
    │
    ▼
Step 1: 读取 Obsidian Vault/第N集.md
    │  提取: 角色、场景、叙事、对白
    ▼
Step 2: 拆分为场景列表（scene plan）
    │  每个场景: 场景描述 + 角色 + 旁白/对白 + 时长
    ▼
Step 3: 生成图像（muapi FLUX / ComfyUI）
    │  每个场景 → 1 张图（1920×1080，竖屏裁剪）
    ▼
Step 4: 生成配音（MiniMax TTS / Edge TTS 备用）
    │  旁白 + 对白 → voiceover.wav + 字幕.srt
    ▼
Step 5: 生成 Remotion 合成文件
    │  NovelVideoComposition.tsx + Root.tsx 注册
    ▼
Step 6: Remotion 渲染 → 输出 mp4
    │  输出: remotion/public/novel_{slug}/
    │         remotion/out/novel_{slug}.mp4
    ▼
Step 7: 自动发布（可选）
    │  social-auto-upload
```

## 核心脚本

| 脚本 | 功能 |
|------|------|
| `scripts/extract_script.py` | 读取 Obsidian Markdown → 结构化场景列表 |
| `scripts/generate_images.py` | 场景描述 → AI 图片 |
| `scripts/generate_audio.py` | 旁白/对白 → TTS + 字幕 SRT |
| `scripts/create_composition.py` | 场景 → Remotion TSX 文件 + Root.tsx 注册 |
| `scripts/render_video.py` | 执行 Remotion 渲染 |

## Remotion 合成模板

| 文件 | 说明 |
|------|------|
| `templates/NovelVideoComposition.tsx` | 正文合成组件（图片+配音+字幕） |
| `templates/NovelScenePlayer.tsx` | 单场景播放器（Ken Burns 缩放 + 转场） |
| `templates/TitleCard.tsx` | 片头（标题 + 角标 + 粒子动画） |
| `templates/HookScreen.tsx` | 片尾预告钩子 |

## 强制检查门

进入以下任一关键步骤前，先逐项自检对应清单；任一未满足即停止执行，向用户索要补齐后再继续。未通过检查门不得进入下一步。

### Step 1 前（提取脚本）
- [ ] 原稿 `D:\Obsidian Vault\第N集.md` 存在且可读
- [ ] 原稿 frontmatter 的 `episode`、`characters`、`locations` 均非空
- [ ] 场景已用 `##` 或 `---` 分隔，无未分隔的连续正文
- [ ] 对白用双引号成对包裹，无孤儿引号
- [ ] `extract_script.py` 输出 `scenes.json`，`scenes` 数组非空

### Step 2 前（生成图像）
- [ ] `MUAPI_KEY` 已导出且余额可用，或 ComfyUI 本地服务端口已启动
- [ ] 输出目录 `public/novel_XX/images/` 已创建
- [ ] 每个场景的 `image_prompt` 非空，无 `{占位符}` 残留

### Step 3 前（配音+字幕）
- [ ] `public/novel_XX/scenes.json` 已生成且字段完整
- [ ] TTS 通道可用：MiniMax API Key 已导出，或 Edge TTS 未限流

### Step 5 前（渲染）
- [ ] `voiceover.wav` 与 `字幕.srt` 均已生成
- [ ] 字幕总时长与配音时长误差在 0.5 秒内
- [ ] `NovelEpisode_XX.tsx` 已生成并在 `Root.tsx` 注册
- [ ] `remotion/node_modules` 存在，`npx remotion compositions` 能列出该集

## 工作流执行

### Step 1: 提取脚本

```bash
python scripts/extract_script.py "D:\Obsidian Vault\第3集.md" --out public/novel_03/
```

输出 JSON:
```json
{
  "title": "第3集",
  "episode": 3,
  "series": "第七秒记忆",
  "scenes": [
    {
      "id": "scene-01",
      "location": "林夏公寓",
      "characters": ["林夏"],
      "narration": "林夏翻开相机里的照片...",
      "dialogue": "这不可能是我的拍的...",
      "image_prompt": "温暖色调的loft公寓，一面墙贴满照片和便利贴...",
      "duration_seconds": 8
    }
  ],
  "hook_text": "赵铭的手机里，存着一条十年前的消息..."
}
```

### Step 2: 生成图像

```bash
# 方案A: muapi (需要 MUAPI_KEY)
bash ../../generative-media-skills/core/media/generate-image.sh \
  --prompt "$SCENE_PROMPT" \
  --model flux-dev \
  --out public/novel_03/scene-01.png

# 方案B: ComfyUI (本地, 免费)
python scripts/generate_images.py \
  --scenes public/novel_03/scenes.json \
  --out public/novel_03/images/ \
  --engine comfyui
```

### Step 3: 生成配音 + 字幕

```bash
python scripts/generate_audio.py \
  --scenes public/novel_03/scenes.json \
  --out public/novel_03/ \
  --tts edge   # 或 minimax
```

输出:
- `public/novel_03/voiceover.wav` — 完整配音
- `public/novel_03/字幕.srt` — 字幕文件

### Step 4: 生成 Remotion 合成

```bash
python scripts/create_composition.py \
  --scenes public/novel_03/scenes.json \
  --out-dir remotion/src/ \
  --novel-dir public/novel_03/
```

自动:
- 生成 `remotion/src/NovelEpisode_03.tsx`
- 更新 `remotion/src/Root.tsx` 注册新 Composition

### Step 5: 渲染

```bash
cd remotion && npx remotion render NovelEpisode_03 out/novel_03.mp4
```

或者一键:

```bash
python scripts/render_video.py --episode 3
```

## 输出模板（可直接套用）

### scenes.json 场景计划模板

复制以下结构到 `public/novel_XX/scenes.json`，逐项填写，字段缺一不可：

```json
{
  "title": "第N集",
  "episode": 0,
  "series": "剧名",
  "hook_text": "片尾钩子，一句话点出反转",
  "scenes": [
    {
      "id": "scene-01",
      "location": "场景地点",
      "characters": ["角色A", "角色B"],
      "narration": "旁白文本，无引号",
      "dialogue": "对白文本",
      "image_prompt": "主体 + 环境 + 光线 + 画风",
      "duration_seconds": 8
    }
  ]
}
```

### 字幕 SRT 模板

`public/novel_XX/字幕.srt` 按此格式逐段书写：

```
1
00:00:00,000 --> 00:00:04,000
林夏翻开相机里的照片

2
00:00:04,000 --> 00:00:08,000
这不可能是我的拍的
```

每段时间轴必须与 `voiceover.wav` 对齐，误差超过 0.5 秒即视为渲染缺陷。

### Remotion Composition 注册模板

`remotion/src/Root.tsx` 追加新集数时按此格式书写：

```tsx
<Composition
  id="NovelEpisode_XX"
  component={NovelEpisode_XX}
  durationInFrames={场景总时长秒数 * 30}
  fps={30}
  width={1080}
  height={1920}
/>
```

### 集数输出命名

| 产物 | 路径 |
|------|------|
| 场景图 | `public/novel_XX/images/scene-01.png` |
| 配音 | `public/novel_XX/voiceover.wav` |
| 字幕 | `public/novel_XX/字幕.srt` |
| 合成组件 | `remotion/src/NovelEpisode_XX.tsx` |
| 成片 | `remotion/out/novel_XX.mp4` |

`XX` 必须为两位补零集数（`03` 而非 `3`），目录与文件名保持一致。

## 前置条件

- Node.js ≥ 18, Remotion 4.0 (已安装)
- Python 3.10+ (已安装)
- 图像生成: muapi.ai API KEY (`MUAPI_KEY`) 或 ComfyUI 本地运行
- TTS: MiniMax API Key 或 Edge TTS (零配置免费)
- Obsidian Vault 位于 `D:\Obsidian Vault\`

## 技能自身运行失败路径

执行过程中出现以下情形时按对应降级处置执行，不得静默跳过或伪造产物：

1. `extract_script.py` JSON 解析报错 → 降级处置：根据报错行号定位场景分隔符或孤儿引号，修正原稿后重跑；原稿缺 frontmatter 时先补齐 `episode`、`characters`、`locations` 再重跑。
2. 图像后端超时或 `MUAPI_KEY` 无余额 → 降级处置：切换方案B ComfyUI 本地引擎；ComfyUI 不可用时改用 `--engine sd15` 后备引擎。图像生成失败不中断流程，但该场景图必须重试到成功，不得用空图占位。
3. TTS 失败（Edge 限流 / MiniMax 欠费）→ 降级处置：先切换另一条 TTS 通道；两条通道均失败时用 `espeak` 生成占位音频，同时把该场景标记为「待补配音」，渲染继续但片尾字幕须注明待补。
4. Remotion 渲染中途崩溃 → 降级处置：读取错误栈定位失败帧与场景，修正 `scenes.json` 中该场景的时长或图片路径，清空 `remotion/out/` 同名残片后重跑；同一错误连续出现 3 次即终止，向用户汇报完整错误日志与最近一次成功输出。

## 小说格式约定

Obsidian 中的每集需包含 frontmatter:

```markdown
---
episode: 3
characters: ["林夏", "程远", "赵铭"]
locations: ["林夏公寓", "赵铭办公室"]
tags: ["悬疑", "对峙"]
---

# 第3集

正文内容...

**场景标记**：用 "##" 或 "---" 分隔场景。
**对白标记**：双引号包裹为角色对白。
**旁白/叙事**：无引号内容为旁白。

## 高风险行动黑名单

以下操作一律绝对禁止。触发任一条即立即终止当前流程，停止一切写入与渲染，向用户报告触发条目；未经用户明确确认，不得自行回滚或继续。

1. 绝对禁止删除、覆盖或移动 `D:\Obsidian Vault\` 下的任何原稿、章节文件或 frontmatter。违反处置：立即终止，报告触发条目与受影响文件，等待用户确认后再处理。
2. 绝对禁止执行 `git reset --hard`、`git clean -f`、`git rm` 等破坏性 Git 命令。违反处置：立即终止，不自行恢复任何提交或工作区改动，报告后交给用户处理。
3. 绝对禁止整体覆写 `remotion/src/Root.tsx`；注册新集数必须经 `create_composition.py` 增量追加。违反处置：立即终止并停止写入，报告被覆写的 Composition 注册项清单，交由用户决定重建方式。
4. 绝对禁止在未确认 `MUAPI_KEY` 余额与配额的情况下批量生成超过 20 张图。违反处置：立即终止图像任务，报告已消耗调用次数与剩余配额。
5. 绝对禁止在渲染中断后不清理残片直接重跑 `npx remotion render`。违反处置：立即终止，先清空 `remotion/out/` 同名残片，再重新执行渲染。
