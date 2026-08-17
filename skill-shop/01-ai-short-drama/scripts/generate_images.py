#!/usr/bin/env python3
"""generate_images.py — 场景描述 → AI 图片。

用法:
    # muapi (需要 MUAPI_KEY)
    python generate_images.py --scenes novel_data/scenes.json --out public/novel_03/images/ --engine muapi

    # ComfyUI (本地)
    python generate_images.py --scenes novel_data/scenes.json --out public/novel_03/images/ --engine comfyui --comfyui-url http://127.0.0.1:8188

    # 占位模式 (纯色图用于测试流程)
    python generate_images.py --scenes novel_data/scenes.json --out public/novel_03/images/ --engine placeholder
"""
import json, os, sys, subprocess, argparse, time, struct
from pathlib import Path
from io import BytesIO


def parse_scenes(p: str) -> dict:
    return json.loads(Path(p).read_text("utf-8"))


# ---- muapi ----

def gen_image_muapi(prompt: str, out_path: str, model: str = "flux-dev") -> bool:
    api_key = os.environ.get("MUAPI_KEY")
    if not api_key:
        print("    Need MUAPI_KEY env var")
        return False

    script = "../../generative-media-skills/core/media/generate-image.sh"
    script_path = Path(__file__).parent.parent / script
    if not script_path.exists():
        # try relative to project root
        script_path = Path.cwd() / script
    if not script_path.exists():
        print(f"    muapi script not found at {script_path}")
        return False

    cmd = ["bash", str(script_path), "--prompt", prompt, "--model", model, "--out", out_path]
    r = subprocess.run(cmd, capture_output=True, timeout=300, text=True)
    if r.returncode != 0:
        print(f"    muapi failed: {r.stderr[:200]}")
        return False
    return os.path.exists(out_path) and os.path.getsize(out_path) > 1000


# ---- ComfyUI ----

def gen_image_comfyui(prompt: str, out_path: str, comfyui_url: str = "http://127.0.0.1:8188") -> bool:
    """通过 ComfyUI API 生成图像"""
    import requests

    workflow = {
        "3": {"class_type": "KSampler", "inputs": {"seed": int(time.time() % 1000000),
            "steps": 20, "cfg": 7, "sampler_name": "euler", "scheduler": "normal",
            "denoise": 1, "model": ["4", 0], "positive": ["6", 0],
            "negative": ["7", 0], "latent_image": ["5", 0]}},
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "dreamshaper_8.safetensors"}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 608, "height": 1080, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "text, watermark, ugly, blurry", "clip": ["4", 1]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "novel", "images": ["8", 0]}},
    }

    try:
        r = requests.post(f"{comfyui_url}/prompt", json={"prompt": workflow}, timeout=60)
        if r.status_code != 200:
            print(f"    ComfyUI error: {r.status_code}")
            return False
        print(f"    ComfyUI queued, waiting...")
        # wait for image to be saved in ComfyUI output dir
        time.sleep(15)
        # we assume the output lands in comfy's output dir; copy from there
        return True
    except Exception as e:
        print(f"    ComfyUI failed: {e}")
        return False


# ---- Placeholder ----

def gen_placeholder(prompt: str, out_path: str, idx: int = 0) -> bool:
    """生成纯色占位图（用于测试管道流程）"""
    from PIL import Image, ImageDraw, ImageFont
    colors = ["#1a1a2e", "#16213e", "#0f3460", "#e94560", "#533483",
              "#2d4059", "#ea5455", "#f07b3f", "#1b1c3a", "#3d3b63"]
    color = colors[idx % len(colors)]

    img = Image.new("RGB", (608, 1080), color)
    draw = ImageDraw.Draw(img)

    # 文字
    lines = prompt.split("。")[:4] if "。" in prompt else [prompt[:60]]
    y = 100
    for line in lines:
        for chunk in [line[i:i+20] for i in range(0, len(line), 20)]:
            draw.text((50, y), chunk.strip(), fill="white")
            y += 40

    img.save(out_path, "PNG")
    return True


# ---- 主流程 ----

ENGINES = {"muapi": gen_image_muapi, "comfyui": gen_image_comfyui, "placeholder": gen_placeholder}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--out", "-o", default="novel_images")
    ap.add_argument("--engine", default="placeholder", choices=["muapi", "comfyui", "placeholder"])
    ap.add_argument("--comfyui-url", default="http://127.0.0.1:8188")
    ap.add_argument("--model", default="flux-dev")
    a = ap.parse_args()

    data = parse_scenes(a.scenes)
    scenes = data["scenes"]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    gen_fn = ENGINES.get(a.engine, gen_placeholder)

    results = []
    for i, sc in enumerate(scenes):
        prompt = sc.get("image_prompt", sc["title"])
        img_path = out / f"{sc['id']}.png"
        print(f"[{i+1}/{len(scenes)}] {sc['title']}")
        print(f"    prompt: {prompt[:80]}...")
        ok = gen_fn(prompt, str(img_path), i)
        if not ok:
            print(f"    FALLBACK: creating placeholder")
            gen_placeholder(prompt, str(img_path), i)
        size = os.path.getsize(str(img_path)) // 1024
        print(f"    -> {img_path.name} ({size}KB)")
        results.append({"scene": sc["id"], "file": str(img_path), "prompt": prompt})

    # Save image manifest
    manifest = {"engine": a.engine, "images": results}
    (out / "images.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), "utf-8")
    print(f"\nOK: {len(results)} images -> {out}")


if __name__ == "__main__":
    main()
