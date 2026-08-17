#!/usr/bin/env python3
"""create_composition.py — 生成小说的 Remotion 视频组件 + Root.tsx 注册。"""
import json, re, argparse
from pathlib import Path


def parse_scenes(p):
    return json.loads(Path(p).read_text("utf-8"))


def generate_tsx(data, novel_dir):
    """生成 NovelEpisode_N.tsx — 纯视频组件（不含 Composition 注册）"""
    ep = data['episode']
    el = data.get('episode_label', f'第{ep}集')
    title = data.get('title', f'第{ep}集')
    series = data.get('series', '小说')
    hook = data.get('hook_text', '未完待续')
    scenes = data['scenes']
    nd = novel_dir.replace('public/', '').replace('public\\', '').strip('/').strip('\\')
    entries = []
    for s in scenes:
        df = max(30, int(s['duration_seconds'] * 30))
        img = f"{nd}/images/{s['id']}.png"
        entries.append({"id": s['id'], "title": s['title'], "frames": df, "img": img})
    total = sum(e['frames'] for e in entries) + 70
    comp_id = f"NovelEpisode_{ep}"
    sj = json.dumps(entries, ensure_ascii=False, indent=2)
    audio = f"{nd}/voiceover.wav"
    srt = f"{nd}/字幕.srt"
    return f'''import {{ NovelVideoComposition, type NovelSceneConfig, NOVEL_FPS }} from "../../.claude/skills/novel-to-video/templates/NovelVideoComposition";

// {el} - {title}
export const EPISODE = {ep};
export const TITLE = "{title}";
export const EP_LABEL = "{el}";
export const SERIES = "{series}";
export const HOOK_TEXT = "{hook}";
export const AUDIO_FILE = "{audio}";
export const SRT_FILE = "{srt}";
export const TOTAL_DURATION = {total};

export const SCENES: NovelSceneConfig[] = {sj};

export {{ NOVEL_FPS }} from "../.claude/skills/novel-to-video/templates/NovelVideoComposition";

export const {comp_id}: React.FC = () => (
  <NovelVideoComposition
    title={{TITLE}}
    epLabel={{EP_LABEL}}
    seriesName={{SERIES}}
    scenes={{SCENES}}
    audioFile={{AUDIO_FILE}}
    srtFile={{SRT_FILE}}
    hookText={{HOOK_TEXT}}
    totalDurationInFrames={{TOTAL_DURATION}}
  />
);
''', comp_id, total


def update_root(root_path, comp_id, total_dur):
    """在 Root.tsx 中添加 import 和 Composition 注册"""
    p = Path(root_path)
    if not p.exists():
        print(f"  WARNING: {root_path} not found")
        return False
    c = p.read_text("utf-8")

    # Check if already registered
    if f'id="{comp_id}"' in c:
        print(f"  {comp_id} already in Root.tsx")
        return True

    # Add import
    imp = f'import {{ {comp_id}, TOTAL_DURATION, NOVEL_FPS }} from "./{comp_id}";'
    if imp not in c:
        li = list(re.finditer(r'^import .+;$', c, re.MULTILINE))
        pos = li[-1].end() if li else 0
        c = c[:pos] + '\n' + imp + c[pos:]

    # Add Composition registration before </>
    comp_tag = f'''      <Composition
        id="{comp_id}"
        component={{{comp_id}}}
        durationInFrames={{TOTAL_DURATION}}
        fps={{NOVEL_FPS}}
        width={{1080}}
        height={{1920}}
      />'''
    c = c.replace("</>", f"{comp_tag}\n    </>")
    p.write_text(c, "utf-8")
    print(f"  Root.tsx -> {comp_id}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", "-e", type=int, required=True)
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--novel-dir", required=True)
    ap.add_argument("--out-dir", default="remotion/src")
    ap.add_argument("--root", default="remotion/src/Root.tsx")
    a = ap.parse_args()

    data = parse_scenes(a.scenes)
    tsx, cid, total = generate_tsx(data, a.novel_dir)

    out_path = Path(a.out_dir) / f"{cid}.tsx"
    out_path.write_text(tsx, "utf-8")
    print(f"  {cid}.tsx")

    update_root(a.root, cid, total)
    print(f"\nRender: cd remotion && npx remotion render {cid} out/{cid}.mp4")


if __name__ == "__main__":
    main()
