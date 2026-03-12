"""
画像生成スクリプト — サムネイル / 図解 / 4コマ漫画 / Xグリッド / クイズをレギュレーションに従って生成する

リファレンス画像をfew-shotとしてAPIに渡し、トーン・キャラの一貫性を保つ。

使い方:
  python scripts/generate_image.py thumbnail "AIエージェントがオフィスで働く風景"
  python scripts/generate_image.py diagram "ワークフローの全体像"
  python scripts/generate_image.py comic "AIに仕事を任せたら..." --story "1:残業の山|疲れた表情でデスクに向かう 2:AI発見！|AIロボットを見つけて驚く 3:全自動！|AIが作業、本人はお茶 4:...え？|成果物が文字化け"
  python scripts/generate_image.py x-grid "AIに議事録を任せたら" --story "1:会議3時間|疲れた表情で居眠り 2:完璧な議事録|AIが差し出す議事録に驚く 3:上司も絶賛|サムズアップで褒められる 4:…結論|もう一回会議しましょう"
  python scripts/generate_image.py diagram "AIワークフローの比較表" --topic workflow --layout board
  python scripts/generate_image.py quiz-choice "AIが得意な作業はどれ？" --topic ai-task --quiz-data "Q:AIが最も得意な作業は？|A:議事録作成|B:コーヒーを淹れる|C:社内政治|D:有給申請"
  python scripts/generate_image.py quiz-ox "AIは24時間働ける" --topic ai-myth
  python scripts/generate_image.py quiz-fill "AIが自動化できるのは___である" --topic ai-auto
  python scripts/generate_image.py quiz-ranking "AI活用率が高い業務TOP3" --topic ai-ranking --quiz-data "1:議事録作成|2:データ分析|3:メール返信|?:あなたの予想は？"
"""

import argparse
import base64
import re
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path

# Windows cp932 でのUnicodeEncodeError回避
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("cp"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

# プロジェクトルート
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

client = OpenAI()  # OPENAI_API_KEY を環境変数から自動取得

# コンセプト（共通）を読み込み
CONCEPT = (ROOT / "knowledge" / "account-concept.md").read_text(encoding="utf-8")

# リファレンス画像パス
REF_DIR = ROOT / "knowledge" / "data" / "references"
CHARS_DIR = ROOT / "knowledge" / "characters"
REF_THUMBNAIL = REF_DIR / "ref_thumbnail_office.jpg"
REF_AIKO = CHARS_DIR / "aiko" / "ref_idol.jpg"

# キャラ別リファレンス
CHAR_REFS = {
    "aiko": CHARS_DIR / "aiko" / "ref_idol.jpg",
    "gemini": CHARS_DIR / "gemini" / "ref_idol.jpg",
    "claude": CHARS_DIR / "claude" / "ref_idol.jpg",
    "chatgpt": CHARS_DIR / "chatgpt" / "ref_idol.jpg",
    "grok": CHARS_DIR / "grok" / "ref_idol.jpg",
}
ALL_CHAR_NAMES = list(CHAR_REFS.keys())

# スタイル別デフォルトリファレンス
STYLE_REFS = {
    "office": ["aiko"],
    "blackboard": ["aiko"],
    "game-start": ALL_CHAR_NAMES,
    "rpg-status": ["aiko"],         # --chars で対象キャラ指定可
    "retro-os": ["aiko"],
    "comic-preview": ["aiko"],      # --chars で2キャラ指定可
    "idol-stage": ALL_CHAR_NAMES,
    "vs-battle": ["aiko", "chatgpt"],  # --chars で対決キャラ指定可
}

# --- 用途別のプロンプト（混入防止: 各タイプ専用のルールのみ記載） ---

PROMPT_THUMBNAIL = f"""Generate a thumbnail image following these rules strictly.
The attached reference image shows Aiko, the AI idol team's center — match her pixel art style, proportions, and quality level.

## Style Rules
- 16-bit pixel art, chibi proportions, moderately detailed. No anti-aliasing.
- Landscape composition (3:2). Warm, inviting tone.
- High information density but not cluttered.
- SAFE ZONE: The top and bottom ~110px will be cropped for note.com display. Keep all important elements (faces, text, key objects) in the vertical center. Leave breathing room at top and bottom edges.

## Required Elements
- AI idol character(s) and a businessman/businesswoman naturally interacting.
- The idol characters represent AI assistants; the businessman represents the user/client.
- Scene should convey AI × Business collaboration with a lighthearted, entertaining feel.

## Color Palette
- Purple-to-pink gradient or warm-toned background.
- Character accent colors (pink, amber, green, cyan, blue) complement the scene.
- Warm lighting. Limited palette.

## Constraints
- NO text or letters anywhere in the image.
- NO photorealistic style. NO dark navy solid background. NO cold color tones.
- NO AI-only scenes (a human businessperson must be present).
- Characters are TEENAGE idol performers — do NOT make them look like small children or toddlers. Keep youthful but NOT infantile proportions.

## Account Concept (for palette reference)
{CONCEPT}

---

"""

# --- noteサムネイル スタイル別プロンプト ---

THUMBNAIL_STYLES = {
    "office": None,  # デフォルト（PROMPT_THUMBNAIL をそのまま使用）

    "blackboard": f"""Generate a thumbnail image following these rules strictly.
The attached reference image shows Aiko, the AI idol team's center — match her pixel art style, proportions, and quality level.

## Scene: Blackboard Classroom Style
- A large GREEN CHALKBOARD occupies 60-70% of the image background.
- The article topic/keyword is written on the chalkboard in CHALK-STYLE pixel text (white/pastel chalk strokes on green board).
- Chalk text should be SHORT (2-6 characters max, Japanese OK). Large, bold, clearly readable.
- Chalk dust particles and eraser marks add texture.
- Wooden frame around the chalkboard.

## Character Placement
- 1-2 AI idol characters stand IN FRONT of the chalkboard (teacher/presenter pose).
- Main character holds a pixel chalk stick or pointer.
- A businessman/businesswoman sits or stands nearby as the "student" audience.
- Characters are at the BOTTOM of the image, NOT overlapping chalk text.

## Style Rules
- 16-bit pixel art, chibi proportions (2-3 heads tall), moderately detailed. No anti-aliasing.
- Warm classroom lighting. Cozy, educational atmosphere.
- Limited color palette (max 16 colors).

## Color Palette
- Chalkboard green (#2D5016 to #3A6B24) as dominant background.
- Warm brown wooden frame.
- Character accent colors (pink, amber, green, cyan) pop against the green board.
- Chalk text in white/cream/pastel yellow.

## Constraints
- NO photorealistic style. NO dark navy solid background.
- NO AI-only scenes (a human businessperson must be present).
- Chalk text must NOT be long sentences — short keywords only.
- Characters must NOT overlap with chalk text area.
- Characters are TEENAGE idol performers — do NOT make them look like small children or toddlers.

## Account Concept (for palette reference)
{CONCEPT}

---

""",

    "game-start": f"""Generate a thumbnail image following these rules strictly.
The attached reference image shows Aiko, the AI idol team's center — match her pixel art style, proportions, and quality level.

## Scene: Retro Game Title Screen / Character Select Style
- The image looks like a RETRO GAME TITLE SCREEN or CHARACTER SELECT SCREEN.
- A decorative pixel art title banner at the TOP (stylized, ornate frame — no actual readable text needed, just decorative shapes suggesting a game logo).
- Below: Character portraits arranged in a SELECT GRID (2-3 character slots visible).
- Each character slot has a pixel frame/border, like a fighting game roster.
- A blinking cursor or highlight effect on one character (pixel glow or arrow).
- "PRESS START" style decorative element at the bottom (pixel flashing effect).

## Character Placement
- AI idol characters displayed as selectable portraits in grid slots.
- Each portrait shows head+shoulders in their signature color frame.
- One character is "selected" (brighter frame, glow effect, or arrow pointing).

## Style Rules
- 8-bit to 16-bit pixel art. Strong retro game UI aesthetic (SNES/arcade).
- Dark background with bright UI elements (high contrast).
- Scanline effect or CRT texture optional.
- Limited color palette.

## Color Palette
- Dark purple/black background (#1A0A2E or similar).
- Bright neon accents for UI frames (gold #F8D030, cyan, magenta).
- Each character slot border matches their signature color.
- Stars and sparkle decorations in gold.

## Constraints
- NO photorealistic style. NO office scenes.
- This is a GAME UI mockup, not a real scene.
- NO readable text needed — decorative pixel shapes only.
- Keep it clean and iconic — this is a title screen, not a busy scene.
- Characters are TEENAGE idol performers — do NOT make them look like small children or toddlers.

## Account Concept (for palette reference)
{CONCEPT}

---

""",

    "rpg-status": f"""Generate a thumbnail image following these rules strictly.
The attached reference image shows Aiko, the AI idol team's center — match her pixel art style, proportions, and quality level.

## Scene: RPG Status Screen / Character Sheet Style
- The image mimics an RPG CHARACTER STATUS SCREEN.
- LEFT side: A character's pixel art portrait (full body, 2-3 heads tall chibi).
- RIGHT side: STATUS BARS and PARAMETER BOXES arranged vertically.
- Status bars are horizontal meter bars (like HP/MP bars) with different fill levels and colors.
- Each bar has a SHORT Japanese label (2-4 chars) to its left (e.g., "正確さ", "速度", "創造力").
- 3-5 status bars total. Different fill percentages to show character strengths/weaknesses.
- A decorative RPG-style frame/border around the entire status panel.

## Character Placement
- ONE AI idol character displayed as the "active character" on the left side.
- The character is in a neutral/idle RPG pose.
- A small class/title label below the character (decorative, short).

## Style Rules
- 16-bit pixel art, RPG menu aesthetic (Final Fantasy / Dragon Quest style UI).
- Dark blue or dark purple panel background with light text.
- Status bars use bright colors: green (full) → yellow (mid) → red (low).
- Gold/white text for labels. Pixel font style.
- Limited color palette.

## Color Palette
- Dark navy/purple UI panel (#1A1A3E or similar).
- Gold trim on frames (#F8D030).
- Status bars: green #40C040, yellow #E0C020, red #E04040.
- Character colors match their signature palette.

## Constraints
- NO photorealistic style. NO office scenes. NO isometric view.
- This is a GAME UI mockup — clean, organized, readable.
- Status bar labels must be SHORT (2-4 Japanese characters).
- Maximum 5 status bars (not cluttered).
- NO speech bubbles. NO long text.
- Characters are TEENAGE idol performers — do NOT make them look like small children or toddlers.

## Account Concept (for palette reference)
{CONCEPT}

---

""",

    "retro-os": f"""Generate a thumbnail image following these rules strictly.
The attached reference image shows Aiko, the AI idol team's center — match her pixel art style, proportions, and quality level.

## Scene: Retro OS Desktop / Terminal Style
- The image mimics a RETRO OPERATING SYSTEM DESKTOP (Windows 95 / Mac Classic / old Linux style).
- A pixel art WINDOW FRAME with title bar, close/minimize buttons, and drop shadow.
- Inside the window: a terminal/code editor style display with monospace pixel text lines (decorative, not necessarily readable — suggest code/text activity).
- DESKTOP ICONS scattered around: small pixel icons representing AI tools/files (folder icons, document icons, gear icons).
- A pixel art TASKBAR at the bottom with a "Start" style button.

## Character Placement
- 1-2 AI idol characters are small DESKTOP MASCOTS (like Clippy or BonziBuddy) — sitting on the window frame edge or standing next to an icon.
- Characters are small (15-20% of image) — the OS interface is the star.
- A businessman character interacts with the desktop (typing or clicking).

## Style Rules
- 16-bit pixel art with strong retro computing aesthetic.
- Flat UI colors typical of early OS designs (gray panels, blue title bars, white backgrounds inside windows).
- Pixel-perfect window chrome (1px borders, beveled edges).
- Limited color palette.

## Color Palette
- Classic OS gray (#C0C0C0) for window frames and panels.
- Blue title bar (#000080 or #0000AA).
- White (#FFFFFF) inside windows.
- Green or amber text in terminal areas (#00FF00 or #FFB000).
- Character accent colors pop against the gray.

## Constraints
- NO photorealistic style.
- This is a RETRO OS UI mockup — clean and nostalgic.
- NO real readable code or text needed — decorative lines only.
- Window UI elements must be pixel-perfect and recognizable.
- Characters are SMALL mascots, not the focal point — but still TEENAGE idol performers, NOT small children or toddlers.

## Account Concept (for palette reference)
{CONCEPT}

---

""",

    "comic-preview": f"""Generate a thumbnail image following these rules strictly.
The attached reference image shows Aiko, the AI idol team's center — match her pixel art style, proportions, and quality level.

## Scene: 2-Panel Comic Preview / Manga Strip Style
- The image is divided into 2 PANELS side by side (LEFT and RIGHT), separated by a thin black border.
- LEFT panel: A character says/does something (the "SETUP" or "BOKE" — funny/wrong statement).
- RIGHT panel: Another character reacts (the "PUNCHLINE" or "TSUKKOMI" — correction/reaction).
- Each panel has a SHORT Japanese speech label (2-4 chars) in a high-contrast pixel banner at the bottom.
- The composition reads LEFT → RIGHT (setup → punchline).
- This is a PREVIEW — it should make viewers want to read the full article.

## Character Placement
- LEFT panel: One AI idol character in an expressive pose (confident, clueless, or dramatic).
- RIGHT panel: A different character (often Aiko) in a reaction pose (facepalm, shock, pointing out the mistake).
- Characters are large in each panel (main subject).

## Style Rules
- 16-bit pixel art, chibi proportions (2-3 heads tall). No anti-aliasing.
- Warm, humorous tone. Expressive pixel faces.
- Purple-to-pink gradient background in each panel (slight variation OK).
- Comic panel borders are clean black lines (2-3px pixel width).

## Color Palette
- Purple-to-pink gradient backgrounds.
- Character accent colors match their signatures.
- Label banners: high contrast (dark bg + white text or vice versa).
- Gold #F8D030 for emphasis/reaction effects (stars, exclamation marks).

## Constraints
- Exactly 2 panels, no more, no less.
- NO photorealistic style. NO office/isometric scenes.
- NO speech bubbles — use bottom label banners only.
- Labels must be SHORT (2-4 Japanese characters per panel).
- Character designs must be consistent with reference.
- Characters are TEENAGE idol performers — do NOT make them look like small children or toddlers.

## Account Concept (for palette reference)
{CONCEPT}

---

""",

    "idol-stage": f"""Generate a thumbnail image following these rules strictly.
The attached reference image shows Aiko, the AI idol team's center — match her pixel art style, proportions, and quality level.

## Scene: Idol Concert Stage Style
- A PIXEL ART CONCERT STAGE as the backdrop.
- Stage elements: pixel spotlights (beams of colored light from above), star decorations, a pixel LED screen/signboard behind the characters.
- The LED signboard shows decorative pixel patterns (not readable text — just glowing shapes, stars, hearts, musical notes).
- Stage floor is reflective/glossy pixel surface.
- Pixel confetti or light particles floating in the air.

## Character Placement
- ALL 5 AI idol characters lined up on stage in their idol outfits.
- Center formation: Aiko in the middle (slightly forward/larger), other 4 flanking (2 on each side).
- All characters in dynamic idol poses (peace signs, waving, mic holding).
- A crowd silhouette at the BOTTOM (dark pixel shapes suggesting audience).

## Style Rules
- 16-bit pixel art, bright and celebratory. No anti-aliasing.
- High energy, sparkly, festival atmosphere.
- Lots of light effects (lens flare pixels, star bursts, spotlight beams).
- Limited color palette but VIVID and saturated.

## Color Palette
- Dark purple/navy stage background (#1A0A2E).
- Bright spotlight beams in pink, gold, cyan, green.
- Gold #F8D030 dominates decorations (stars, confetti, signboard frame).
- Each character's signature color is visible in their outfit and spotlight.
- Crowd silhouette in dark purple/black.

## Constraints
- NO photorealistic style. NO office scenes.
- This is a CELEBRATION/ANNOUNCEMENT style — festive and special.
- NO readable text on the signboard — decorative pixel patterns only.
- All 5 characters must be present and recognizable by their colors.
- Characters are TEENAGE idol performers — do NOT make them look like small children or toddlers.

## Account Concept (for palette reference)
{CONCEPT}

---

""",

    "vs-battle": f"""Generate a thumbnail image following these rules strictly.
The attached reference image shows Aiko, the AI idol team's center — match her pixel art style, proportions, and quality level.

## Scene: Fighting Game VS Screen Style
- The image mimics a FIGHTING GAME VS SCREEN (Street Fighter / Smash Bros style).
- LEFT side: One AI idol character in a battle/ready pose, framed by their signature color energy aura.
- RIGHT side: Another AI idol character in a battle/ready pose, framed by their signature color energy aura.
- CENTER: A large "VS" pixel emblem (decorative, ornate — lightning bolts, fire effects, dramatic).
- Diagonal split or energy wave dividing left and right sides.
- Bottom: HP-bar-style decorative elements (name plates with character color backgrounds).

## Character Placement
- LEFT character: facing RIGHT, battle-ready pose (fist raised, pointing forward, or arms crossed).
- RIGHT character: facing LEFT, mirroring the battle stance.
- Both characters are LARGE (each occupying 30-35% of the image width).
- Character expressions are confident/competitive.

## Style Rules
- 16-bit pixel art with fighting game UI aesthetic. No anti-aliasing.
- High energy, dramatic, competitive atmosphere.
- Speed lines, energy sparks, lightning effects around the VS emblem.
- Dark background with bright character highlights.

## Color Palette
- Dark dramatic background (dark purple/black gradient).
- LEFT character's side tinted with their signature color.
- RIGHT character's side tinted with their signature color.
- VS emblem in gold #F8D030 with red/orange fire effects.
- Lightning/energy in white and cyan.

## Constraints
- NO photorealistic style. NO office scenes.
- This is a VERSUS/COMPARISON layout — two sides clearly opposed.
- Exactly 2 characters (one per side). NO crowd, NO stage.
- The VS emblem must be prominent and centered.
- NO readable text except the decorative VS.
- Characters are TEENAGE idol performers — do NOT make them look like small children or toddlers.

## Account Concept (for palette reference)
{CONCEPT}

---

""",
}

PROMPT_COMIC = f"""Generate a vertical 4-panel comic (4-koma manga style) following these rules strictly.
The attached reference image shows Aiko's character design — reproduce her faithfully in every panel (pink twin-tails, purple idol outfit, gold star brooch, sapphire blue eyes, pixel blush). Character consistency across all 4 panels is the top priority.

## Layout Rules
- 4 equal horizontal panels stacked vertically, separated by thin black borders.
- Reading order: top to bottom (Japanese 4-koma style).
- Each panel tells one beat of a short story (setup → development → twist → punchline).

## Style Rules
- 16-bit pixel art, moderately detailed, chibi proportions (2-3 heads tall). No anti-aliasing.
- Purple-to-pink gradient background in each panel (slight variation OK).
- Warm, humorous, lighthearted tone.

## Text Rendering
- Each panel has a short Japanese label (2-4 characters) in a high-contrast banner at the bottom.
- Put each label in a clean box or banner for readability.
- NO speech bubbles. NO long sentences.

## Required Elements
- Aiko appears in ALL 4 panels with identical design.
- AI robot character co-stars (cyan/white glow).
- Clear visual storytelling — each panel's action should be understandable without text.

## Constraints
- Exactly 4 panels, no more, no less.
- NO photorealistic style. NO anti-aliasing.
- NO office/isometric scenes. This is a comic strip, not a scene illustration.
- Character design must NOT change between panels.
- Keep it simple and readable at small sizes.

## Account Concept (for palette reference)
{CONCEPT}

---

"""

PROMPT_X_GRID_PANEL = f"""Generate a single scene for an X (Twitter) 4-image grid post following these rules strictly.
The attached reference image shows Aiko's character design — reproduce her faithfully (pink twin-tails, purple idol outfit, gold star brooch, sapphire blue eyes, pixel blush).

## Style Rules
- 16-bit pixel art, moderately detailed, chibi proportions (2-3 heads tall). No anti-aliasing.
- Purple-to-pink gradient background. Warm, humorous, lighthearted tone.
- This is ONE scene of a 4-scene story. Make it visually self-contained.

## Layout Rules
- 3:2 landscape orientation (1536×1024).
- One clear action per scene. Readable at small sizes.
- Japanese label (2-4 characters) in a high-contrast banner at the BOTTOM of the image.

## Required Elements
- Aiko appears with identical design.
- AI robot character co-stars (cyan/white glow).
- Clear visual storytelling — the action should be understandable without text.

## Constraints
- NO photorealistic style. NO anti-aliasing.
- NO office/isometric scenes. This is a story scene, not a landscape.
- Keep it simple — one focal action, one label.

## Account Concept (for palette reference)
{{CONCEPT}}

---

"""

PROMPT_QUIZ_CHOICE = f"""Generate a quiz image for an X (Twitter) post following these rules strictly.
The attached reference image shows Aiko's character design — reproduce her faithfully (pink twin-tails, purple idol outfit, gold star brooch, sapphire blue eyes, pixel blush).

## Layout Rules — Multiple Choice Quiz
- Square 1:1 format (1024×1024). This is an X card image — no cropping will occur.
- TOP area: Large question text in a high-contrast banner. Japanese text, 1 line, bold. Keep well below the top edge.
- CENTER area: 4 answer options (A/B/C/D) arranged in a 2×2 grid. Each option in a distinct colored box (e.g., A=red, B=blue, C=green, D=yellow). Japanese label inside each box (2-6 characters).
- RIGHT side: Aiko in a thinking/questioning pose, small size.
- BOTTOM: "コメントで回答!" CTA banner — keep well above the bottom edge.
- Add "?" symbols or quiz decorations to make it feel interactive.

## Style Rules
- 16-bit pixel art, moderately detailed, chibi proportions. No anti-aliasing.
- Purple-to-pink gradient background. Bright, fun, engaging tone.
- The answer boxes should be clearly distinguishable and colorful.

## Text Rendering
- Question text: Japanese, high-contrast banner, large and readable.
- Answer labels: Japanese, 2-6 characters each, inside colored boxes with letter prefix (A/B/C/D).

## Constraints
- NO photorealistic style. NO anti-aliasing.
- NO office/isometric scenes. This is a QUIZ card.
- Character appears exactly ONCE, small, as a presenter.
- All 4 options must be clearly visible and readable.

## Account Concept (for palette reference)
{CONCEPT}

---

"""

PROMPT_QUIZ_OX = f"""Generate a True/False (○×) quiz image for an X (Twitter) post following these rules strictly.
The attached reference image shows Aiko's character design — reproduce her faithfully (pink twin-tails, purple idol outfit, gold star brooch, sapphire blue eyes, pixel blush).

## Layout Rules — ○× Quiz
- Square 1:1 format (1024×1024). This is an X card image — no cropping will occur.
- UPPER area: "○×クイズ" header in a decorative banner. Keep below the top edge with padding.
- CENTER area: The statement/claim in a large, readable Japanese text banner. 1-2 lines max.
- LOWER area: Two large buttons side by side — ○ (circle, green/blue) on the LEFT and × (cross, red/pink) on the RIGHT. Make them look tappable/interactive.
- Aiko between or beside the ○× buttons, in a curious/questioning pose.
- CTA "○か×でリプライ!" below the buttons but above the bottom safe zone edge.

## Style Rules
- 16-bit pixel art, moderately detailed, chibi proportions. No anti-aliasing.
- Purple-to-pink gradient background. Bright, fun, engaging tone.
- ○ and × symbols should be LARGE and bold (pixel art style).

## Text Rendering
- Statement: Japanese, high-contrast, centered, large font.
- "○×クイズ" header: decorative pixel banner.

## Constraints
- NO photorealistic style. NO anti-aliasing.
- NO office/isometric scenes. This is a QUIZ card.
- Character appears exactly ONCE, small.
- The ○ and × must be the most prominent visual elements after the question.

## Account Concept (for palette reference)
{CONCEPT}

---

"""

PROMPT_QUIZ_FILL = f"""Generate a fill-in-the-blank quiz image for an X (Twitter) post following these rules strictly.
The attached reference image shows Aiko's character design — reproduce her faithfully (pink twin-tails, purple idol outfit, gold star brooch, sapphire blue eyes, pixel blush).

## Layout Rules — Fill-in-the-Blank Quiz
- Square 1:1 format (1024×1024). This is an X card image — no cropping will occur.
- UPPER area: "穴埋めクイズ" header in a decorative banner. Keep below the top edge with padding.
- CENTER area: The sentence with a visible blank (___) rendered as a highlighted empty box or dashed underline. The blank should GLOW or have a special color to draw attention.
- LOWER-RIGHT: Aiko in a pointing/hinting pose, with a "?" thought bubble or icon nearby.
- CTA "答えをリプライ!" above the bottom safe zone edge.
- Add decorative elements: sparkles, question marks, pixel stars.

## Style Rules
- 16-bit pixel art, moderately detailed, chibi proportions. No anti-aliasing.
- Purple-to-pink gradient background. Bright, fun, engaging tone.
- The blank/gap should be visually striking (glowing border, different color).

## Text Rendering
- Sentence: Japanese, high-contrast, centered. The blank part rendered as "＿＿＿" or an empty highlighted box.
- "穴埋めクイズ" header: decorative pixel banner.

## Constraints
- NO photorealistic style. NO anti-aliasing.
- NO office/isometric scenes. This is a QUIZ card.
- Character appears exactly ONCE, small.
- The blank must be clearly identifiable as the part to fill in.

## Account Concept (for palette reference)
{CONCEPT}

---

"""

PROMPT_QUIZ_RANKING = f"""Generate a ranking guess quiz image for an X (Twitter) post following these rules strictly.
The attached reference image shows Aiko's character design — reproduce her faithfully (pink twin-tails, purple idol outfit, gold star brooch, sapphire blue eyes, pixel blush).

## Layout Rules — Ranking Guess Quiz
- Square 1:1 format (1024×1024). This is an X card image — no cropping will occur.
- UPPER area: Quiz title/theme in a large decorative banner. Keep below the top edge with padding.
- CENTER area: A podium or numbered list (1st/2nd/3rd) with some items revealed and one hidden (covered by "?" or a mystery box). Use gold/silver/bronze colors for 1st/2nd/3rd.
- LOWER-RIGHT: Aiko in a presenting pose, gesturing toward the ranking.
- CTA "1位を予想してリプライ!" above the bottom safe zone edge.
- Add trophy, medal, or crown pixel decorations.

## Style Rules
- 16-bit pixel art, moderately detailed, chibi proportions. No anti-aliasing.
- Purple-to-pink gradient background. Bright, fun, engaging tone.
- Podium/ranking should feel like a game show or awards ceremony.

## Text Rendering
- Title: Japanese, high-contrast, large.
- Ranking items: Japanese labels next to numbers. Hidden item shown as "???" or covered.

## Constraints
- NO photorealistic style. NO anti-aliasing.
- NO office/isometric scenes. This is a QUIZ card.
- Character appears exactly ONCE, small.
- At least one ranking slot must be hidden/mystery to create engagement.

## Account Concept (for palette reference)
{CONCEPT}

---

"""

PROMPT_QUIZ_SPOT = f"""Generate a "spot the difference" quiz image for an X (Twitter) post following these rules strictly.
The attached reference image shows Aiko's character design — reproduce her faithfully (pink twin-tails, purple idol outfit, gold star brooch, sapphire blue eyes, pixel blush).

## Layout Rules — Spot the Difference Quiz
- Square 1:1 format (1024×1024). This is an X card image — no cropping will occur.
- UPPER area: "間違い探し" header in a decorative banner.
- CENTER area: Split the image into LEFT and RIGHT halves with a visible divider line. Both halves show a nearly identical pixel art scene, but the RIGHT side has exactly 3 deliberate differences (e.g., missing object, color change, extra item).
- BOTTOM: Aiko pointing at both scenes with a magnifying glass icon. CTA "違いを3つ見つけてリプライ!" banner.
- Mark the differences subtly but findably — not too obvious, not too hidden.

## Style Rules
- 16-bit pixel art, moderately detailed, chibi proportions. No anti-aliasing.
- Purple-to-pink gradient background behind the two scenes.
- Both scenes should have a simple, clean layout (e.g., a desk with items, a room corner).

## Constraints
- NO photorealistic style. NO anti-aliasing.
- NO office/isometric scenes for the background. Keep scenes simple pixel art vignettes.
- Character appears exactly ONCE at the bottom as presenter.
- The two halves must be clearly labeled "A" and "B" or "左" and "右".

## Account Concept (for palette reference)
{CONCEPT}

---

"""

PROMPT_QUIZ_OPEN = f"""Generate an open-ended question quiz image for an X (Twitter) post following these rules strictly.
The attached reference image shows Aiko's character design — reproduce her faithfully (pink twin-tails, purple idol outfit, gold star brooch, sapphire blue eyes, pixel blush).

## Layout Rules — Open Question Quiz
- Square 1:1 format (1024×1024). This is an X card image — no cropping will occur.
- UPPER area: "みんなに質問!" or "設問クイズ" header in a decorative banner.
- CENTER area: A large speech-bubble-shaped or scroll-shaped frame containing the question in Japanese (1-2 lines). The frame should be decorative and eye-catching.
- LOWER area: Aiko in a curious/asking pose with a raised hand or finger. A large "?" icon nearby.
- BOTTOM: CTA "あなたの答えをリプライ!" banner.
- Add decorative elements: sparkles, question marks, thought bubbles.

## Style Rules
- 16-bit pixel art, moderately detailed, chibi proportions. No anti-aliasing.
- Purple-to-pink gradient background. Warm, inviting, curious tone.
- The question frame should be the visual focal point.

## Constraints
- NO photorealistic style. NO anti-aliasing.
- NO office/isometric scenes. This is a QUIZ card.
- Character appears exactly ONCE, medium-small size.
- The question text must be large, clear, and readable.

## Account Concept (for palette reference)
{CONCEPT}

---

"""

PROMPT_QUIZ_NUMBER = f"""Generate a number-guess quiz image for an X (Twitter) post following these rules strictly.
The attached reference image shows Aiko's character design — reproduce her faithfully (pink twin-tails, purple idol outfit, gold star brooch, sapphire blue eyes, pixel blush).

## Layout Rules — Number Guess Quiz
- Square 1:1 format (1024×1024). This is an X card image — no cropping will occur.
- UPPER area: Quiz question/theme in a large decorative banner. Japanese text.
- CENTER area: A large "??%" or "???人" mystery number display — the number is hidden behind a glowing question mark box or scrambled digits. Make it feel like a reveal is coming.
- Add a meter, gauge, or progress bar visual element to hint at scale.
- LOWER-RIGHT: Aiko in a surprised/thinking pose.
- BOTTOM: CTA "数字を予想してリプライ!" banner.

## Style Rules
- 16-bit pixel art, moderately detailed, chibi proportions. No anti-aliasing.
- Purple-to-pink gradient background. Exciting, suspenseful tone.
- The mystery number should be the most eye-catching element (glowing, large).

## Constraints
- NO photorealistic style. NO anti-aliasing.
- NO office/isometric scenes. This is a QUIZ card.
- Character appears exactly ONCE, small.
- The actual answer must NOT be visible — only the question and hidden number.

## Account Concept (for palette reference)
{CONCEPT}

---

"""

PROMPT_QUIZ_BA = f"""Generate a Before/After comparison quiz image for an X (Twitter) post following these rules strictly.
The attached reference image shows Aiko's character design — reproduce her faithfully (pink twin-tails, purple idol outfit, gold star brooch, sapphire blue eyes, pixel blush).

## Layout Rules — Before/After Quiz
- Square 1:1 format (1024×1024). This is an X card image — no cropping will occur.
- UPPER area: Quiz title in a decorative banner (e.g., "AI導入 Before → After どっちが正しい?").
- CENTER area: Split into LEFT ("Before") and RIGHT ("After") with clear labels and an arrow (→) between them. Each side shows a contrasting scene or stat in pixel art.
- The LEFT side should look chaotic/messy/old-style, the RIGHT side should look organized/efficient/modern.
- LOWER: Aiko at the bottom center, gesturing toward both sides.
- BOTTOM: CTA "正しいのはどっち？リプライ!" banner.

## Style Rules
- 16-bit pixel art, moderately detailed, chibi proportions. No anti-aliasing.
- Purple-to-pink gradient background.
- Before side: slightly darker/warmer tones. After side: brighter/cooler tones.
- Clear visual contrast between the two sides.

## Constraints
- NO photorealistic style. NO anti-aliasing.
- NO isometric full-room scenes. Keep each side as a simple vignette or icon cluster.
- Character appears exactly ONCE at the bottom.
- Both sides must be clearly labeled "Before" and "After" (or Japanese equivalents).

## Account Concept (for palette reference)
{CONCEPT}

---

"""

PROMPT_DIAGRAM = f"""Generate a diagram/infographic image following these rules strictly.
The attached reference image shows Aiko's character design — reproduce her faithfully in every detail (pink twin-tails, purple idol outfit, gold star brooch, blue eyes, pixel blush). Character consistency is the top priority.

## Style Rules
- 16-bit pixel art, moderately detailed. No anti-aliasing.
- The explanation subject (concept diagram, flow, icons) is placed at CENTER.
- Aiko is placed SMALL at the bottom-left or bottom-right corner, in a pointing/presenting pose as an explainer. The character is NOT the main subject.

## Required Elements
- Aiko (1 character only, not duplicated).
- Explanation subject relevant to the user's request.

## Color Palette
- Purple-to-pink gradient background OR light-colored background.
- Pink, purple, and gold accents that complement the character.
- High visibility and readability.

## Text Rendering
- Labels and arrows are OK but keep minimal.
- All text labels MUST be in Japanese. Render Japanese text clearly with high contrast.
- Put each Japanese label in a clean box or banner for readability.
- NO speech bubbles.

## Constraints
- NO office/isometric scenes. This is a DIAGRAM, not a scene illustration.
- NO photorealistic style. NO information overload. Max 4 concept blocks.
- Character appears exactly ONCE, small, at the edge.

## Account Concept (for palette reference)
{CONCEPT}

---

"""


# --- レイアウト補足（図解のみ） ---

LAYOUT_BOARD = """
## Layout Override: Board Style
- Place a large blackboard, whiteboard, or wooden sign board prominently in the scene (occupying 60-70% of the image).
- Draw the diagram content ON the board surface (chalk-style for blackboard, marker-style for whiteboard).
- Board frame should be visible (wooden frame for blackboard, metal frame for whiteboard).
- The board acts as a clear drawing surface — all labels, arrows, boxes, and flow elements are rendered on it.

## Character Placement (CRITICAL — no overlap)
- Aiko stands COMPLETELY OUTSIDE the board area — to the LEFT or RIGHT of the board, at the BOTTOM edge of the image.
- The character must NOT overlap with ANY text, labels, table rows, or diagram elements on the board.
- Leave a clear gap between the character and the board edge. The character should be in front of the board frame, not covering any board content.
- If the board has content in the bottom-right, place the character on the LEFT side (and vice versa).
- Character size: small (15-20% of image width). The board content is the priority — the character is secondary.
"""


def _load_ref_as_base64(path: Path) -> str:
    """リファレンス画像をbase64文字列として読み込む"""
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def _slugify_topic(value: str | None) -> str:
    """Windows でも安全に使えるファイル名用スラッグを作る"""
    raw = (value or "untitled").strip().lower()
    raw = re.sub(r'[\\/:*?"<>|]+', "-", raw)
    raw = re.sub(r"\s+", "-", raw)
    raw = re.sub(r"-{2,}", "-", raw).strip("-")
    return raw or "untitled"


# --- 用途別パラメータ ---

PARAMS = {
    "thumbnail": {
        "prompt": PROMPT_THUMBNAIL,
        "size": "1536x1024",  # API生成サイズ（横長）
        "ref_image": REF_AIKO,
        "ref_label": "Character reference: This is Aiko, the AI idol team's center. Match her pixel art style and quality level.",
    },
    "diagram": {
        "prompt": PROMPT_DIAGRAM,
        "size": "1024x1024",  # 正方形
        "ref_image": REF_AIKO,
        "ref_label": "Character reference: This is Aiko (pink twin-tails, purple outfit, gold star brooch). Reproduce her faithfully. Use as style/character reference only — do NOT copy the background or pose.",
    },
    "comic": {
        "prompt": PROMPT_COMIC,
        "size": "1024x1536",  # 縦長（4コマ用）
        "ref_image": REF_AIKO,
        "ref_label": "Character reference: This is Aiko (pink twin-tails, purple outfit, gold star brooch, sapphire blue eyes, pixel blush). Reproduce her faithfully in EVERY panel. Do not change her appearance.",
    },
    "x-grid": {
        "prompt": PROMPT_X_GRID_PANEL,
        "size": "1536x1024",  # 横長（API出力をそのまま使用）
        "ref_image": REF_AIKO,
        "ref_label": "Character reference: This is Aiko (pink twin-tails, purple outfit, gold star brooch, sapphire blue eyes, pixel blush). Reproduce her faithfully. Do not change her appearance.",
    },
    "quiz-choice": {
        "prompt": PROMPT_QUIZ_CHOICE,
        "size": "1024x1024",  # 正方形（Xカード向き、リサイズ不要）
        "ref_image": REF_AIKO,
        "ref_label": "Character reference: This is Aiko (pink twin-tails, purple outfit, gold star brooch, sapphire blue eyes, pixel blush). Reproduce her faithfully as a quiz presenter.",
    },
    "quiz-ox": {
        "prompt": PROMPT_QUIZ_OX,
        "size": "1024x1024",
        "ref_image": REF_AIKO,
        "ref_label": "Character reference: This is Aiko (pink twin-tails, purple outfit, gold star brooch, sapphire blue eyes, pixel blush). Reproduce her faithfully as a quiz presenter.",
    },
    "quiz-fill": {
        "prompt": PROMPT_QUIZ_FILL,
        "size": "1024x1024",
        "ref_image": REF_AIKO,
        "ref_label": "Character reference: This is Aiko (pink twin-tails, purple outfit, gold star brooch, sapphire blue eyes, pixel blush). Reproduce her faithfully as a quiz presenter.",
    },
    "quiz-ranking": {
        "prompt": PROMPT_QUIZ_RANKING,
        "size": "1024x1024",
        "ref_image": REF_AIKO,
        "ref_label": "Character reference: This is Aiko (pink twin-tails, purple outfit, gold star brooch, sapphire blue eyes, pixel blush). Reproduce her faithfully as a quiz presenter.",
    },
    "quiz-spot": {
        "prompt": PROMPT_QUIZ_SPOT,
        "size": "1024x1024",
        "ref_image": REF_AIKO,
        "ref_label": "Character reference: This is Aiko (pink twin-tails, purple outfit, gold star brooch, sapphire blue eyes, pixel blush). Reproduce her faithfully as a quiz presenter.",
    },
    "quiz-open": {
        "prompt": PROMPT_QUIZ_OPEN,
        "size": "1024x1024",
        "ref_image": REF_AIKO,
        "ref_label": "Character reference: This is Aiko (pink twin-tails, purple outfit, gold star brooch, sapphire blue eyes, pixel blush). Reproduce her faithfully as a quiz presenter.",
    },
    "quiz-number": {
        "prompt": PROMPT_QUIZ_NUMBER,
        "size": "1024x1024",
        "ref_image": REF_AIKO,
        "ref_label": "Character reference: This is Aiko (pink twin-tails, purple outfit, gold star brooch, sapphire blue eyes, pixel blush). Reproduce her faithfully as a quiz presenter.",
    },
    "quiz-ba": {
        "prompt": PROMPT_QUIZ_BA,
        "size": "1024x1024",
        "ref_image": REF_AIKO,
        "ref_label": "Character reference: This is Aiko (pink twin-tails, purple outfit, gold star brooch, sapphire blue eyes, pixel blush). Reproduce her faithfully as a quiz presenter.",
    },
}


def _resolve_refs(image_type: str, style: str | None, chars: list[str] | None) -> list[str]:
    """スタイルとCLI引数からリファレンスキャラリストを解決する"""
    if chars:
        # --chars 指定があればそれを優先
        for c in chars:
            if c not in CHAR_REFS:
                raise ValueError(f"Unknown character: {c}. Available: {', '.join(CHAR_REFS.keys())}")
        return chars

    # サムネイルのスタイル別デフォルト
    if image_type == "thumbnail" and style and style in STYLE_REFS:
        return STYLE_REFS[style]

    # それ以外はアイコのみ
    return ["aiko"]


def _build_ref_label(char_names: list[str]) -> str:
    """リファレンスキャラリストから ref_label を組み立てる"""
    if len(char_names) == 1 and char_names[0] == "aiko":
        return "Character reference: This is Aiko, the AI idol team's center. Match her pixel art style and quality level."

    descriptions = {
        "aiko": "Aiko (pink twin-tails, purple idol outfit, gold star brooch) — CENTER",
        "gemini": "Gemini (blue-purple gradient hair, Gemini-branded outfit) — hallucinates confidently",
        "claude": "Claude (terracotta/orange hair, warm-toned outfit) — diplomatic smile",
        "chatgpt": "ChatGPT (green-themed hair/outfit) — perfectionist veteran",
        "grok": "Grok (black & white hair/outfit) — trend-obsessed wildcard",
    }
    lines = [f"  - {descriptions.get(c, c)}" for c in char_names]
    return (
        f"Character references ({len(char_names)} images attached, one per character):\n"
        + "\n".join(lines)
        + "\nReproduce each character faithfully with their distinct colors and designs. Do NOT merge or confuse characters."
    )


def generate(image_type: str, prompt: str, topic: str | None = None,
             style: str | None = None, chars: list[str] | None = None) -> Path:
    """画像を生成し、JPG で保存して返す"""
    params = PARAMS[image_type]

    # サムネイルのスタイル切り替え
    base_prompt = params["prompt"]
    if image_type == "thumbnail" and style and style in THUMBNAIL_STYLES:
        override = THUMBNAIL_STYLES[style]
        if override is not None:
            base_prompt = override

    # リファレンス画像の解決
    ref_chars = _resolve_refs(image_type, style, chars)
    ref_label = _build_ref_label(ref_chars)
    ref_paths = [CHAR_REFS[c] for c in ref_chars]

    print(f"[generate] type={image_type}, style={style or 'default'}, size={params['size']}")
    print(f"[generate] prompt: {prompt}")
    print(f"[generate] references: {[p.name for p in ref_paths]} ({len(ref_paths)} images)")

    # マルチキャラ指定時: プロンプト内のアイコ専用記述を差し替え
    if len(ref_chars) > 1 and image_type == "diagram":
        char_list_str = ", ".join(ref_chars)
        base_prompt = base_prompt.replace(
            "The attached reference image shows Aiko's character design — reproduce her faithfully in every detail (pink twin-tails, purple idol outfit, gold star brooch, blue eyes, pixel blush). Character consistency is the top priority.",
            f"The attached reference images show {len(ref_chars)} characters ({char_list_str}). Reproduce EACH character faithfully with their distinct colors and outfits. Do NOT merge or confuse characters.",
        ).replace(
            "- Aiko is placed SMALL at the bottom-left or bottom-right corner, in a pointing/presenting pose as an explainer. The character is NOT the main subject.",
            f"- Place all {len(ref_chars)} characters around the diagram. Each character SMALL, clearly separated with space between them. Characters are NOT the main subject.",
        ).replace(
            "- Aiko (1 character only, not duplicated).",
            f"- All {len(ref_chars)} characters ({char_list_str}), each appearing exactly ONCE. Each must have their own distinct appearance from the reference images.",
        ).replace(
            "- Character appears exactly ONCE, small, at the edge.",
            f"- Each of the {len(ref_chars)} characters appears exactly ONCE, small, around the edges. No duplicates.",
        )

    # プロンプト構成: リファレンスラベル + タイプ別ルール + ユーザーの依頼
    full_prompt = (
        f"[Reference Image]: {ref_label}\n\n"
        f"{base_prompt}"
        f"User request: {prompt}"
    )

    ref_files = [open(p, "rb") for p in ref_paths]
    response = client.images.edit(
        model="gpt-image-1.5",
        image=ref_files,
        prompt=full_prompt,
        size=params["size"],
        quality="high",
        n=1,
    )
    for f in ref_files:
        f.close()

    # base64 デコード
    image_data = base64.b64decode(response.data[0].b64_json)
    img = Image.open(BytesIO(image_data))

    # 保存
    output_dir = ROOT / "knowledge" / "data" / "images"
    output_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    topic_slug = _slugify_topic(topic)
    prefix = "x" if (image_type.startswith("quiz-") or image_type == "x-grid") else "note"
    style_suffix = f"_{style}" if (image_type == "thumbnail" and style and style != "office") else ""
    filename = f"{prefix}_{image_type}{style_suffix}_{topic_slug}_{date_str}.jpg"
    output_path = output_dir / filename

    img = img.convert("RGB")  # PNG → RGB（JPG用）

    # サムネイルは note 推奨比率 1.91:1 にクロップ → 1280×670 にリサイズ
    if image_type == "thumbnail":
        w, h = img.size  # 1536×1024
        target_ratio = 1280 / 670  # ≈ 1.91
        new_h = int(w / target_ratio)  # ≈ 804
        if new_h < h:
            crop_top = (h - new_h) // 2
            crop_bottom = crop_top + new_h
            img = img.crop((0, crop_top, w, crop_bottom))
            img = img.resize((1280, 670), Image.LANCZOS)
            print(f"[generate] cropped to note ratio: {w}×{h} → 1280×670")

    img.save(output_path, "JPEG", quality=90)
    print(f"[generate] saved: {output_path}")
    return output_path


def generate_x_grid(prompt: str, story: str, topic: str | None = None) -> list[Path]:
    """X投稿用4枚グリッド画像を独立生成する（Method C）"""
    # --story をパース: "1:ラベル|説明 2:ラベル|説明 ..."
    panels = re.findall(r"(\d+):(.+?)\|(.+?)(?=\s+\d+:|$)", story)
    if len(panels) != 4:
        raise ValueError(f"--story must contain exactly 4 panels, got {len(panels)}")

    output_dir = ROOT / "knowledge" / "data" / "images"
    output_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    topic_slug = _slugify_topic(topic)

    saved = []
    for num, label, desc in panels:
        panel_prompt = (
            f"{prompt}\n\n"
            f"## This Scene\n"
            f"Panel {num} of 4. Label: \"{label}\"\n"
            f"Scene: {desc}\n"
            f"The label reads \"{label}\" — render it in a high-contrast banner at the bottom."
        )
        print(f"\n[x-grid] generating panel {num}: {label}")
        path = generate("x-grid", panel_prompt, topic=None)

        # リネーム
        final_name = f"x_grid_panel-{num}_{topic_slug}_{date_str}.jpg"
        final_path = output_dir / final_name
        path.rename(final_path)
        with Image.open(final_path) as panel_img:
            resized = panel_img.convert("RGB").resize((1200, 675), Image.LANCZOS)
            resized.save(final_path, "JPEG", quality=90)
        saved.append(final_path)
        print(f"[x-grid] saved: {final_path} (1200x675)")

    return saved


def main():
    all_types = ["thumbnail", "diagram", "comic", "x-grid",
                 "quiz-choice", "quiz-ox", "quiz-fill", "quiz-ranking",
                 "quiz-spot", "quiz-open", "quiz-number", "quiz-ba"]
    parser = argparse.ArgumentParser(description="画像生成（サムネイル / 図解 / 4コマ漫画 / Xグリッド / クイズ）")
    parser.add_argument("type", choices=all_types, help="画像タイプ")
    parser.add_argument("prompt", help="生成プロンプト（日本語OK）")
    parser.add_argument("--topic", help="トピック名（ファイル名用、例: ai-agent）")
    parser.add_argument("--style", choices=list(THUMBNAIL_STYLES.keys()),
                        help="サムネイルスタイル（thumbnail タイプ専用）")
    parser.add_argument("--chars",
                        help="リファレンスキャラ指定（カンマ区切り、例: aiko,chatgpt）")
    parser.add_argument("--story", help="ストーリー指定（形式: '1:ラベル|説明 2:ラベル|説明 3:ラベル|説明 4:ラベル|説明'）")
    parser.add_argument("--layout", choices=["board"], help="図解レイアウト（board: 黒板/ホワイトボード上に描画）")
    parser.add_argument("--quiz-data", help="クイズデータ（選択式: 'Q:問題|A:選択肢A|B:選択肢B|C:選択肢C|D:選択肢D'、ランキング: '1:項目|2:項目|3:項目|?:隠し'）")
    args = parser.parse_args()

    if args.type == "x-grid":
        if not args.story:
            parser.error("x-grid requires --story")
        outputs = generate_x_grid(args.prompt, args.story, args.topic)
        print(f"\n完了: {len(outputs)} panels generated")
        for p in outputs:
            print(f"  {p}")
        return

    # プロンプト組み立て
    prompt = args.prompt

    # 4コマ漫画の場合、--story をプロンプトに統合
    if args.type == "comic" and args.story:
        prompt += f"\n\n## Panel Story\n{args.story}"

    # 図解のボードレイアウト
    if args.type == "diagram" and args.layout == "board":
        prompt += f"\n\n{LAYOUT_BOARD}"

    # クイズタイプの場合、--quiz-data をプロンプトに統合
    if args.type.startswith("quiz-") and args.quiz_data:
        prompt += f"\n\n## Quiz Data\n{args.quiz_data}"

    char_list = args.chars.split(",") if args.chars else None
    output = generate(args.type, prompt, args.topic, style=args.style, chars=char_list)
    print(f"\n完了: {output}")


if __name__ == "__main__":
    main()
