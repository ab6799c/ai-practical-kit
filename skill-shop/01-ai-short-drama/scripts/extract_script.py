#!/usr/bin/env python3
"""
extract_script.py — 将 Obsidian 小说 Markdown 解析为结构化场景列表。

用法:
    python extract_script.py "D:\Obsidian Vault\第3集.md" --out novel_data/

输出:
    novel_data/scenes.json     — 场景列表
    novel_data/metadata.json   — 集信息
    novel_data/script.txt      — 纯文本剧本（预览用）
"""

import re
import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Windows GBK 兼容
if sys.stdout.encoding and sys.stdout.encoding.upper() in ('GBK', 'GB2312', 'CP936'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """解析 Markdown frontmatter (--- 包围的 YAML 风格元数据)"""
    fm = {}
    body = text
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', text, re.DOTALL)
    if m:
        raw = m.group(1)
        body = m.group(2)
        for line in raw.strip().split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                key = key.strip()
                val = val.strip()
                if val.startswith('[') and val.endswith(']'):
                    val = [v.strip().strip('"\'') for v in val[1:-1].split(',')]
                elif val.isdigit():
                    val = int(val)
                fm[key] = val
    return fm, body


def extract_dialogue_and_narration(text: str) -> list[dict]:
    """
    从文本中提取对白和旁白。
    对白: 被「」或 "" 包裹的内容。
    旁白: 其余叙事内容。

    返回: [{"type": "narration|dialogue", "text": "...", "speaker": "..."}, ...]
    """
    segments = []
    lines = text.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('---'):
            continue
        if line.startswith('>'):
            segments.append({"type": "note", "text": line.lstrip('> ').strip()})
            continue

        # 查找「」对白 (中文引号)
        pos = 0
        while pos < len(line):
            m1 = re.search(r'[「"]([^」"]+)[」"]', line[pos:])
            if m1:
                before = line[pos:pos + m1.start()].strip()
                if before:
                    segments.append({"type": "narration", "text": before, "speaker": None})
                dialogue_text = m1.group(1)
                pre_text = line[:pos + m1.start()].strip()
                speaker = None
                speaker_m = re.search(r'([\u4e00-\u9fff]{2,4})[说喊道问答叫]', pre_text[-12:] if len(pre_text) > 12 else pre_text)
                if speaker_m:
                    speaker = speaker_m.group(1)
                segments.append({"type": "dialogue", "text": dialogue_text, "speaker": speaker})
                pos += m1.start() + m1.end()
            else:
                rest = line[pos:].strip()
                if rest:
                    segments.append({"type": "narration", "text": rest, "speaker": None})
                break

    return segments


def split_scenes(text: str) -> list[str]:
    """按场景分隔符拆分文本。支持 ## 标题 / --- 分割线 / 空行段落。"""
    # 优先按 ## 标题拆分
    parts = re.split(r'\n(?=##\s)', text)
    if len(parts) <= 1:
        parts = re.split(r'\n---\s*\n', text)
    if len(parts) <= 1:
        # 按双空行分段落（段落即场景）
        parts = re.split(r'\n\n\n+', text)
    if len(parts) <= 1:
        parts = [text]
    parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 20]

    # 如果单个段落太长（>500字），继续细分
    final = []
    for p in parts:
        if len(p) > 500:
            # 按句号分段，每组约 80-150 字 = 一个镜头
            sentences = re.split(r'(?<=[。！？])', p)
            chunk = ""
            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                chunk += s
                if len(chunk) > 100:
                    final.append(chunk)
                    chunk = ""
            if chunk.strip():
                final.append(chunk)
        else:
            final.append(p)
    return final


def estimate_duration(segments: list[dict]) -> float:
    """估算旁白+对白的朗读时长（秒）。中文约 4 字/秒。"""
    total_chars = sum(len(s['text']) for s in segments if s['type'] in ('narration', 'dialogue'))
    return max(3.0, total_chars / 4.0)


def build_image_prompt(scene_title: str, segments: list[dict], scene_idx: int,
                       locations: list[str], characters: list[str]) -> str:
    """根据场景内容构建图像生成提示词。"""
    visual_clues = []
    for seg in segments:
        if seg['type'] == 'narration':
            visual_terms = re.findall(
                r'[\u4e00-\u9fff]{2,}(?:色|光|灯|暗|亮|影|暖|冷|旧|破|红|黑|白|金|房间|桌子|窗|墙|门|照片|相机|手机)',
                seg['text']
            )
            visual_clues.extend(visual_terms)

    loc_str = '、'.join(locations[:3]) if locations else '室内'
    char_str = '、'.join(characters[:3]) if characters else '人物'

    prompt = (
        f"场景{scene_idx}：{scene_title}。"
        f"角色：{char_str}。"
        f"地点：{loc_str}。"
        f"电影感镜头，{'; '.join(set(visual_clues[:8])) if visual_clues else '戏剧化打光，细节丰富'}。"
        f"竖屏构图 9:16，电影级质感，高细节，暗调氛围。"
    )
    return prompt


def extract_script(markdown_path: str) -> dict:
    """主函数：读取 Markdown → 返回结构化剧本"""
    path = Path(markdown_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")

    text = path.read_text(encoding='utf-8')
    fm, body = parse_frontmatter(text)

    episode = fm.get('episode', 0)
    title = fm.get('title', path.stem)
    all_chars = fm.get('characters', [])
    all_locs = fm.get('locations', [])

    raw_scenes = split_scenes(body)
    scenes = []

    for i, raw in enumerate(raw_scenes):
        title_m = re.match(r'##?\s*(.*)', raw)
        scene_title = title_m.group(1).strip() if title_m else f"场景{i+1}"

        segments = extract_dialogue_and_narration(raw)
        duration = estimate_duration(segments)

        scene_locs = list(all_locs) if all_locs else []
        scene_chars = list(all_chars) if all_chars else []
        for seg in segments:
            if seg['speaker'] and seg['speaker'] not in scene_chars:
                scene_chars.append(seg['speaker'])

        image_prompt = build_image_prompt(scene_title, segments, i+1, scene_locs, scene_chars)

        narration_text = ' '.join(s['text'] for s in segments if s['type'] == 'narration')
        dialogue_text = ' '.join(
            f"{s['speaker']}说：{s['text']}" if s['speaker'] else s['text']
            for s in segments if s['type'] == 'dialogue'
        )
        full_text = f"{narration_text} {dialogue_text}".strip()

        scenes.append({
            "id": f"scene-{i+1:02d}",
            "title": scene_title,
            "duration_seconds": round(duration, 1),
            "characters": scene_chars,
            "locations": scene_locs,
            "image_prompt": image_prompt,
            "narration": narration_text,
            "dialogue": dialogue_text,
            "full_text": full_text,
            "segments": segments,
            "raw": raw[:200] + "..." if len(raw) > 200 else raw,
        })

    total_duration = sum(s['duration_seconds'] for s in scenes)

    result = {
        "series": fm.get('series', fm.get('tags', ['小说'])[-1] if isinstance(fm.get('tags'), list) else '小说'),
        "title": title,
        "episode": episode,
        "episode_label": f"第{episode}集" if episode else title,
        "total_duration_seconds": round(total_duration, 1),
        "scene_count": len(scenes),
        "characters": all_chars,
        "locations": all_locs,
        "hook_text": f"未完待续——下一集更精彩 🔥",
        "scenes": scenes,
        "source_file": str(path),
        "extracted_at": datetime.now().isoformat(),
    }

    return result


def save_output(data: dict, out_dir: str):
    """保存为 JSON + TXT 预览"""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    (out / "scenes.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print(f"  [OK] scenes.json ({len(data['scenes'])} 场景)")

    meta = {k: data[k] for k in ['series', 'title', 'episode', 'episode_label',
                                  'total_duration_seconds', 'scene_count',
                                  'characters', 'locations', 'hook_text',
                                  'source_file', 'extracted_at']}
    (out / "metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print(f"  [OK] metadata.json")

    lines = [f"===== {data['episode_label']} =====",
             f"总时长: ~{data['total_duration_seconds']:.0f}s | {data['scene_count']} 场\n"]
    for s in data['scenes']:
        lines.append(f"[{s['id']}] {s['title']} ({s['duration_seconds']}s)")
        for seg in s['segments']:
            if seg['type'] == 'dialogue':
                sp = f"{seg['speaker']}：" if seg['speaker'] else ""
                lines.append(f"  「{sp}{seg['text']}」")
            elif seg['type'] == 'narration':
                lines.append(f"  {seg['text'][:80]}")
        lines.append("")
    (out / "script.txt").write_text('\n'.join(lines), encoding='utf-8')
    print(f"  [OK] script.txt")

    print(f"\n[Stats] 场景数: {data['scene_count']}")
    print(f"[Stats] 预估时长: ~{data['total_duration_seconds']:.0f}s")
    print(f"[Stats] 角色: {', '.join(data['characters'])}")
    print(f"[Stats] 场景: {', '.join(data['locations'])}")


def main():
    parser = argparse.ArgumentParser(description="Obsidian 小说 -> 结构化剧本")
    parser.add_argument("markdown", help="Obsidian Markdown 文件路径")
    parser.add_argument("--out", "-o", default="novel_data", help="输出目录")
    args = parser.parse_args()

    print(f"[Input] 读取: {args.markdown}")
    data = extract_script(args.markdown)

    print(f"[Extract] {data['episode_label']} ({data['total_duration_seconds']:.0f}s, {data['scene_count']} 场景)")
    save_output(data, args.out)

    print(f"\n--- 场景列表 ---")
    for s in data['scenes']:
        actors = ', '.join(s['characters']) if s['characters'] else '(旁白)'
        print(f"  [{s['id']}] {s['title']} ({s['duration_seconds']}s) — {actors}")


if __name__ == '__main__':
    main()
