---
name: drama-prompt-library
description: 短剧/AI视频画风提示词库。做角色图/场景图/道具图提示词、定项目画风、定题材节奏时查。自带 Q版扁平风 完整画风锚定模块，可直接复制进生图 prompt。
---

# 短剧提示词库（drama-prompt-library）

把"该用什么画风、prompt 怎么锚定"变成查表题。

## 何时用
- 给 ComfyUI/FLUX/智谱 cogview/Wan 写**角色/场景/道具**图提示词
- 定项目**画风**与**题材节奏**
- 生成图角色/场景跨镜头不一致，需要风格锚定

## 何时不用
- 视频生成 API 调用、剧本正文写作、纯文生图闲聊

## 快速选画风（速查）

| 题材需求 | 画风方向 | 锚定要点 |
|---|---|---|
| Q版搞笑 / 轻动画 | **2D 扁平风**（本 skill 自带完整模块） | 纯色色块、无阴影渐变、几何造型 |
| 国漫 | 国风 2D | 水墨留白、传统纹样、青绿配色 |
| 90年代日漫 | 复古赛璐璐 | 平涂+胶片颗粒+复古调色 |
| 电影感真人 | 实拍都市 | 自然光、生活流、高动态范围 |
| 仙侠/赛博国风 | 3D 国风赛博 | 传统纹样×霓虹 |

## 自带模块：2D 扁平风（Q版首选）

完整画风锚定提示词 + 角色生成 4 规则 + 情绪色盘 → 打开 `references/flat-design-style.md`，把"风格基因"段抄进每条 image_prompt 开头即可。

## 扩展画风（本机素材，按需取用）

本机装有完整 11 画风 × 15 题材提示词库（`D:\NewProject\Toonflow\data\skills\`，1.48MB），本 skill 默认自包含不依赖它；有本机素材时优先按"快速选画风"表读对应目录：
- 角色图 → `<画风>/art_prompt/art_character.md`
- 场景图 → `<画风>/art_prompt/art_scene.md`
- 分镜 → `<画风>/driector_skills/director_storyboard.md`
- 题材节奏 → `story_skills/<题材>/driector_skills/director_planning_narrative.md`

**铁律**：一次最多读 1 个画风目录 + 1 个题材目录，勿整库读。

## 关联
- 分镜表铁律（拆分/连续性/景别）→ 见 [[storyboard-master]] 或本包内 storyboard-master/SKILL.md
- 阿里 Pixelle 引擎的 14 段管线提示词设计可参考本机 `_drama_extract/pixelle_prompts.md`
