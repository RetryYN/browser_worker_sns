"""
スクリーンショットクロップユーティリティ

Playwright MCP のスクリーンショットを記事用にトリミングする。
--trim-chrome は固定値ではなく、ピクセル走査でクローム境界を検出する。

使い方:
  python scripts/crop_screenshot.py input.png
  python scripts/crop_screenshot.py input.png --trim-chrome
  python scripts/crop_screenshot.py input.png --region 100,50,800,600
  python scripts/crop_screenshot.py input.png --ratio 16:9
  python scripts/crop_screenshot.py input.png --output article_ss.jpg
"""

import argparse
import sys
from pathlib import Path

from PIL import Image

# Windows cp932 でのUnicodeEncodeError回避
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("cp"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _detect_content_bounds(img: Image.Image) -> tuple[int, int, int, int]:
    """
    画像のピクセルを走査して、コンテンツ領域の境界を検出する。

    ブラウザクローム（タイトルバー、タブバー、ブックマークバー等）は
    通常コンテンツ領域と色の変化が大きい水平境界を持つ。
    上端・下端から走査し、行ごとの色変化が大きい境界を検出する。

    Returns: (left, top, right, bottom) — コンテンツ領域の座標
    """
    w, h = img.size

    # グレースケール変換して行ごとの平均輝度を計算
    gray = img.convert("L")
    pixels = list(gray.getdata())

    def row_avg(y: int) -> float:
        start = y * w
        return sum(pixels[start:start + w]) / w

    def row_variance(y: int) -> float:
        """行内のピクセル分散（均一なクローム vs 多様なコンテンツの判別）"""
        start = y * w
        row = pixels[start:start + w]
        avg = sum(row) / len(row)
        return sum((p - avg) ** 2 for p in row) / len(row)

    # 上端からの検出: 行間の輝度差 + 行内分散の変化で境界を探す
    # クローム部分は均一色（分散小）、コンテンツ部分は多様（分散大）
    scan_limit = min(h // 3, 300)  # 上から最大1/3 or 300pxまで走査

    top = 0
    prev_var = row_variance(0)
    prev_avg = row_avg(0)
    best_score = 0.0

    for y in range(1, scan_limit):
        curr_var = row_variance(y)
        curr_avg = row_avg(y)

        # スコア: 輝度のジャンプ × 分散の変化
        avg_jump = abs(curr_avg - prev_avg)
        var_jump = abs(curr_var - prev_var)
        # 正規化スコア（輝度差が大きい + 分散が急変 = 境界の可能性大）
        score = avg_jump + var_jump * 0.1

        if score > best_score and score > 5.0:  # 閾値: 明確な境界のみ
            best_score = score
            top = y

        prev_var = curr_var
        prev_avg = curr_avg

    # 下端からの検出（ステータスバー等）
    bottom = h
    best_score_bottom = 0.0
    prev_var = row_variance(h - 1)
    prev_avg = row_avg(h - 1)

    for y in range(h - 2, max(h - scan_limit, h // 2), -1):
        curr_var = row_variance(y)
        curr_avg = row_avg(y)

        avg_jump = abs(curr_avg - prev_avg)
        var_jump = abs(curr_var - prev_var)
        score = avg_jump + var_jump * 0.1

        if score > best_score_bottom and score > 5.0:
            best_score_bottom = score
            bottom = y + 1

        prev_var = curr_var
        prev_avg = curr_avg

    return (0, top, w, bottom)


def crop_chrome(img: Image.Image) -> tuple[Image.Image, dict]:
    """
    ブラウザクローム部分を画像解析で検出して除去する。

    Returns: (cropped_image, detection_info)
    """
    left, top, right, bottom = _detect_content_bounds(img)
    w, h = img.size

    info = {
        "original": f"{w}×{h}",
        "detected_top": top,
        "detected_bottom": bottom,
        "trimmed_top_px": top,
        "trimmed_bottom_px": h - bottom,
    }

    # 検出結果が妥当か確認（トリミングが画像の50%超えなら異常とみなして無操作）
    content_h = bottom - top
    if content_h < h * 0.5:
        print(f"[warn] detected content area too small ({content_h}px / {h}px). Skipping trim.")
        info["skipped"] = True
        return img, info

    cropped = img.crop((left, top, right, bottom))
    info["result"] = f"{cropped.size[0]}×{cropped.size[1]}"
    return cropped, info


def crop_region(img: Image.Image, region: str) -> Image.Image:
    """left,top,right,bottom で指定した矩形を切り出す。"""
    parts = [int(x.strip()) for x in region.split(",")]
    if len(parts) != 4:
        raise ValueError("--region は left,top,right,bottom の4値（カンマ区切り）で指定")
    left, top, right, bottom = parts
    return img.crop((left, top, right, bottom))


def crop_ratio(img: Image.Image, ratio: str) -> Image.Image:
    """指定アスペクト比にセンタークロップする（例: 16:9, 4:3, 1:1）。"""
    rw, rh = [int(x) for x in ratio.split(":")]
    target_ratio = rw / rh

    w, h = img.size
    current_ratio = w / h

    if current_ratio > target_ratio:
        new_w = int(h * target_ratio)
        offset = (w - new_w) // 2
        return img.crop((offset, 0, offset + new_w, h))
    else:
        new_h = int(w / target_ratio)
        offset = (h - new_h) // 2
        return img.crop((0, offset, w, offset + new_h))


def main():
    parser = argparse.ArgumentParser(description="スクリーンショットクロップ")
    parser.add_argument("input", help="入力画像パス")
    parser.add_argument("--trim-chrome", action="store_true",
                        help="ブラウザクローム（タイトルバー等）を画像解析で検出・除去")
    parser.add_argument("--region",
                        help="矩形切り出し: left,top,right,bottom")
    parser.add_argument("--ratio",
                        help="アスペクト比でセンタークロップ（例: 16:9）")
    parser.add_argument("--max-width", type=int, default=None,
                        help="最大幅を指定してリサイズ（比率維持）")
    parser.add_argument("--output", "-o", default=None,
                        help="出力パス（デフォルト: 入力ファイル名_cropped.jpg）")
    parser.add_argument("--quality", type=int, default=90,
                        help="JPEG品質（デフォルト: 90）")
    args = parser.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"[error] file not found: {src}")
        sys.exit(1)

    img = Image.open(src).convert("RGB")
    original_size = img.size

    # 処理チェーン: trim-chrome → region → ratio → max-width
    if args.trim_chrome:
        img, info = crop_chrome(img)
        if info.get("skipped"):
            print(f"[crop] chrome detection: no clear boundary found, kept original {original_size}")
        else:
            print(f"[crop] chrome detected: top={info['detected_top']}px, bottom_trim={info['trimmed_bottom_px']}px → {info['result']}")

    if args.region:
        img = crop_region(img, args.region)
        print(f"[crop] region: → {img.size}")

    if args.ratio:
        img = crop_ratio(img, args.ratio)
        print(f"[crop] ratio {args.ratio}: → {img.size}")

    if args.max_width and img.size[0] > args.max_width:
        ratio_val = args.max_width / img.size[0]
        new_h = int(img.size[1] * ratio_val)
        img = img.resize((args.max_width, new_h), Image.LANCZOS)
        print(f"[crop] resized: → {img.size}")

    # 出力
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = src.parent / f"{src.stem}_cropped.jpg"

    img.save(out_path, "JPEG", quality=args.quality)
    print(f"[crop] saved: {out_path} ({img.size[0]}×{img.size[1]})")


if __name__ == "__main__":
    main()
