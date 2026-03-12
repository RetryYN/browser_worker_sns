"""
キャラクターリファレンス画像生成 — Aikoのスタイルをfew-shotで渡して質感を統一する

使い方:
  python scripts/generate_character_ref.py gemini
  python scripts/generate_character_ref.py claude
  python scripts/generate_character_ref.py chatgpt
  python scripts/generate_character_ref.py grok
  python scripts/generate_character_ref.py all
"""

import argparse
import base64
import sys
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

# Windows cp932 対策
sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
client = OpenAI()

AIKO_REF = ROOT / "knowledge" / "characters" / "aiko" / "ref_idol.jpg"
CHARS_DIR = ROOT / "knowledge" / "characters"

# 各キャラのプロンプト（ブランドカラー準拠 + スタイル統一指示）
CHARACTER_PROMPTS = {
    "aiko": """Generate a single character reference image in coarse pixel art style.

## CRITICAL: Style Matching
The first attached image shows the STYLE REFERENCE (another team member). Match the EXACT pixel art style — same coarse pixel density, same chunky pixel blocks, same chibi proportions (2-3 heads tall), same shading technique, same limited color palette, same overall quality. Use LARGE visible pixels with NO anti-aliasing and NO smooth gradients.

## Character: Aiko (Center / Leader)
- Hair: Pink twin-tails with yellow ribbons
- Eyes: Big sapphire-blue eyes, pixel blush on cheeks
- Accessories: Gold star brooch, clipboard in one hand
- Outfit: Purple idol stage outfit with gold star accents
- Pose: Full-body standing, confident smile, pointing forward with one hand
- Background: Simple solid purple-to-pink gradient, clean, NO text, NO UI, NO stage, NO audience, NO spotlights

## Constraints
- Single character ONLY. NO other characters.
- Coarse pixel art, chibi proportions, large visible pixels, no anti-aliasing, no smooth gradients
- Background MUST be a simple solid gradient — NOT a concert stage or detailed scene
- Match the style reference exactly — same pixel density, same chunky blocks, same shading, same level of detail
""",
    "gemini": """Generate a single character reference image in coarse pixel art style.

## CRITICAL: Style Matching
The first attached image shows the STYLE REFERENCE (Aiko). Match her EXACT pixel art style — same coarse pixel density, same chunky pixel blocks, same chibi proportions (2-3 heads tall), same shading technique, same limited color palette, same overall quality. The new character must look like she belongs in the same team/game as Aiko. Use LARGE visible pixels with NO anti-aliasing and NO smooth gradients.

## Character: Gemini
- Hair: Blue-to-purple gradient hair (Gemini brand colors #4285F4 to #7B1FA2). NOT pink.
- Eyes: Purple eyes
- Accessories: Star hair clips
- Outfit: Blue-purple gradient idol dress with star motifs
- Pose: Full-body standing, cute idol pose
- Background: Simple solid purple-to-pink gradient, clean, NO text, NO UI

## Constraints
- Single character ONLY. NO other characters.
- Coarse pixel art, chibi proportions, large visible pixels, no anti-aliasing, no smooth gradients
- Match Aiko's style exactly — same pixel density, same chunky blocks, same shading, same level of detail
""",
    "claude": """Generate a single character reference image in coarse pixel art style.

## CRITICAL: Style Matching
The first attached image shows the STYLE REFERENCE (Aiko). Match her EXACT pixel art style — same coarse pixel density, same chunky pixel blocks, same chibi proportions (2-3 heads tall), same shading technique, same limited color palette, same overall quality. The new character must look like she belongs in the same team/game as Aiko. Use LARGE visible pixels with NO anti-aliasing and NO smooth gradients.

## Character: Claude
- Hair: Chestnut-brown semi-long wavy hair with a golden bookmark-shaped hair clip
- Eyes: Warm amber eyes, gentle smile
- Accessories: Book charm necklace
- Outfit: Terracotta and cream elegant idol dress (Anthropic brand color #D97757)
- NO GLASSES.
- Pose: Full-body standing, cute idol pose
- Background: Simple solid purple-to-pink gradient, clean, NO text, NO UI

## Constraints
- Single character ONLY. NO other characters.
- Coarse pixel art, chibi proportions, large visible pixels, no anti-aliasing, no smooth gradients
- Match Aiko's style exactly — same pixel density, same chunky blocks, same shading, same level of detail
- NO GLASSES
""",
    "chatgpt": """Generate a single character reference image in coarse pixel art style.

## CRITICAL: Style Matching
The first attached image shows the STYLE REFERENCE (Aiko). Match her EXACT pixel art style — same coarse pixel density, same chunky pixel blocks, same chibi proportions (2-3 heads tall), same shading technique, same limited color palette, same overall quality. The new character must look like she belongs in the same team/game as Aiko. Use LARGE visible pixels with NO anti-aliasing and NO smooth gradients.

## Character: ChatGPT
- Hair: Dark green long hair (darker shade of OpenAI green, NOT bright green) with flower-shaped hair pin
- Eyes: Blue eyes
- Accessories: Small star pin on collar
- Outfit: Dark green and black idol stage costume, sleek and sophisticated
- Pose: Full-body standing, cute idol pose
- FRAMING: The ENTIRE character from head to toe must fit within the image with generous margin on all sides. Do NOT crop any part of the body. Leave space above head and below feet.
- Background: Simple solid purple-to-pink gradient, clean, NO text, NO UI

## Constraints
- Single character ONLY. NO other characters.
- Coarse pixel art, chibi proportions, large visible pixels, no anti-aliasing, no smooth gradients
- Match Aiko's style exactly — same pixel density, same chunky blocks, same shading, same level of detail
- FULL BODY must be visible — no cropping
""",
    "grok": """Generate a single character reference image in coarse pixel art style.

## CRITICAL: Style Matching
The first attached image shows the STYLE REFERENCE (Aiko). Match her EXACT pixel art style — same coarse pixel density, same chunky pixel blocks, same chibi proportions (2-3 heads tall), same shading technique, same limited color palette, same overall quality. The new character must look like she belongs in the same team/game as Aiko. Use LARGE visible pixels with NO anti-aliasing and NO smooth gradients.

## Character: Grok
- Hair: BLACK ponytail with WHITE streak highlights (X/Twitter brand black and white). NOT blue.
- Eyes: Dark eyes
- Accessories: Chain necklace, stud earrings
- Outfit: BLACK and WHITE rock-style idol costume with chain accessories
- Pose: Full-body standing, cute idol pose
- Background: Simple solid purple-to-pink gradient, clean, NO text, NO UI

## Constraints
- Single character ONLY. NO other characters.
- Coarse pixel art, chibi proportions, large visible pixels, no anti-aliasing, no smooth gradients
- Match Aiko's style exactly — same pixel density, same chunky blocks, same shading, same level of detail
""",
}


# 絵文字アイコン用プロンプト（顔アップ、各キャラの特徴を凝縮）
EMOJI_PROMPTS = {
    "aiko": "Pink twin-tail hair with yellow star ribbons. Big sapphire-blue eyes, pixel blush on cheeks. Gold star accessory. Purple collar/neckline visible.",
    "gemini": "Blue-to-purple gradient hair with star hair clips. Purple eyes. Blue-purple collar/neckline visible.",
    "claude": "Chestnut-brown wavy hair with golden bookmark-shaped hair clip. Warm amber eyes, gentle smile. Terracotta collar/neckline visible. NO GLASSES.",
    "chatgpt": "Dark green long hair with flower-shaped hair pin. Blue eyes. Dark green collar/neckline visible.",
    "grok": "Black hair with white streak highlights, ponytail visible behind. Dark eyes, confident smirk. Chain necklace. Black collar/neckline visible.",
}


def generate_emoji(name: str) -> Path:
    """キャラの顔アップ絵文字アイコンを生成（透過PNG）"""
    face_desc = EMOJI_PROMPTS[name]
    output_path = CHARS_DIR / name / "emoji.png"

    # スタイル参照にはそのキャラのref_idol.jpgを使う
    ref_path = CHARS_DIR / name / "ref_idol.jpg"

    print(f"[emoji] generating {name}...")
    print(f"[emoji] ref: {ref_path.name}")

    ref_file = open(ref_path, "rb")
    prompt = (
        f"[Reference Image]: This is the character's full-body reference. "
        f"Generate a FACE CLOSE-UP emoji icon of this SAME character.\n\n"
        f"Generate a single character face emoji icon in coarse pixel art style.\n\n"
        f"## Design\n"
        f"- Extreme close-up of face and upper shoulders ONLY. No body, no hands, no full figure.\n"
        f"- {face_desc}\n"
        f"- Expression: cheerful, friendly smile\n"
        f"- Circular composition — the face fills most of the frame\n"
        f"- Background: transparent (no background)\n\n"
        f"## Style\n"
        f"- Coarse pixel art, large visible pixels, chunky pixel blocks\n"
        f"- No anti-aliasing, no smooth gradients\n"
        f"- Simple, bold, readable at very small sizes (32x32 to 128x128)\n"
        f"- Match the reference image's pixel art style exactly\n\n"
        f"## Constraints\n"
        f"- Single face ONLY. NO full body. NO other characters.\n"
        f"- NO text, NO UI elements\n"
        f"- Designed to work as a small icon/emoji\n"
    )

    response = client.images.edit(
        model="gpt-image-1.5",
        image=[ref_file],
        prompt=prompt,
        size="1024x1024",
        quality="high",
        n=1,
    )
    ref_file.close()

    image_data = base64.b64decode(response.data[0].b64_json)
    img = Image.open(BytesIO(image_data))
    # PNG で保存（透過対応）
    img.save(output_path, "PNG")
    print(f"[emoji] saved: {output_path}")
    return output_path


def generate_character(name: str) -> Path:
    """スタイル参照画像をfew-shotで渡してキャラリファレンスを生成"""
    prompt = CHARACTER_PROMPTS[name]
    output_path = CHARS_DIR / name / "ref_idol.jpg"

    # aiko自身を生成する場合は別キャラをスタイル参照にする
    if name == "aiko":
        fallback_ref = CHARS_DIR / "claude" / "ref_idol.jpg"
        if fallback_ref.exists():
            style_ref_path = fallback_ref
            ref_label = (
                "[Image 1 - STYLE REFERENCE]: This is another team member. "
                "Match the EXACT pixel art style, proportions, shading, and quality level. "
                "Generate a DIFFERENT character (described below) in the SAME style."
            )
        elif AIKO_REF.exists():
            style_ref_path = AIKO_REF
            ref_label = (
                "[Image 1 - REFERENCE]: This is Aiko's previous reference image. "
                "Preserve the same identity, style, proportions, shading, and overall quality "
                "while refreshing the render."
            )
        else:
            raise FileNotFoundError(
                "No style reference found for Aiko. Expected either "
                "'knowledge/characters/claude/ref_idol.jpg' or "
                "'knowledge/characters/aiko/ref_idol.jpg'."
            )
    else:
        style_ref_path = AIKO_REF
        ref_label = (
            "[Image 1 - STYLE REFERENCE]: This is Aiko, the team leader. "
            "Match her EXACT pixel art style, proportions, shading, and quality level. "
            "Generate a DIFFERENT character (described below) in the SAME style."
        )

    print(f"[chargen] generating {name}...")
    print(f"[chargen] style ref: {style_ref_path.name}")

    ref_file = open(style_ref_path, "rb")
    full_prompt = f"{ref_label}\n\n{prompt}"

    response = client.images.edit(
        model="gpt-image-1.5",
        image=[ref_file],
        prompt=full_prompt,
        size="1024x1024",
        quality="high",
        n=1,
    )
    ref_file.close()

    image_data = base64.b64decode(response.data[0].b64_json)
    img = Image.open(BytesIO(image_data))
    img = img.convert("RGB")
    img.save(output_path, "JPEG", quality=90)
    print(f"[chargen] saved: {output_path}")
    return output_path


def main():
    names = list(CHARACTER_PROMPTS.keys())
    parser = argparse.ArgumentParser(description="キャラクターリファレンス生成")
    parser.add_argument("character", choices=names + ["all"], help="キャラ名 or all")
    parser.add_argument("--emoji", action="store_true", help="絵文字アイコンを生成")
    args = parser.parse_args()

    targets = names if args.character == "all" else [args.character]
    for name in targets:
        if args.emoji:
            path = generate_emoji(name)
        else:
            path = generate_character(name)
        print(f"  -> {path}\n")


if __name__ == "__main__":
    main()
