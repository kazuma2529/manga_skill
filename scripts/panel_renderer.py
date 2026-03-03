"""
panel_renderer.py - コマ割りYAMLからコマ割り参照画像（PNG）を生成する

使い方:
    python panel_renderer.py <input_yaml> [output_png]
    python panel_renderer.py --dir <yaml_dir> [--out <output_dir>]

例:
    python panel_renderer.py layout_page_01.yaml
    python panel_renderer.py layout_page_01.yaml panel_page_01.png
    python panel_renderer.py --dir ../output/panel_layouts --out ../output/panel_images
"""

import argparse
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont


def load_layout(yaml_path: str) -> dict:
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def grid_to_pixel(
    gx: float,
    gy: float,
    grid_cols: int,
    grid_rows: int,
    margin: dict,
    page_width: int,
    page_height: int,
) -> tuple[float, float]:
    """グリッド座標をピクセル座標に変換する"""
    draw_width = page_width - margin["left"] - margin["right"]
    draw_height = page_height - margin["top"] - margin["bottom"]
    px = margin["left"] + (gx / grid_cols) * draw_width
    py = margin["top"] + (gy / grid_rows) * draw_height
    return px, py


def apply_bleed(
    vertices_px: list[tuple[float, float]],
    bleed: list[str],
    page_width: int,
    page_height: int,
) -> list[tuple[float, float]]:
    """断ち切り指定に基づいて座標をページ端まで拡張する"""
    xs = [v[0] for v in vertices_px]
    ys = [v[1] for v in vertices_px]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    if "left" in bleed:
        min_x = 0
    if "right" in bleed:
        max_x = page_width
    if "top" in bleed:
        min_y = 0
    if "bottom" in bleed:
        max_y = page_height

    return [
        (min_x, min_y),
        (max_x, min_y),
        (max_x, max_y),
        (min_x, max_y),
    ]


def get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """利用可能なフォントを取得する"""
    font_candidates = [
        "C:/Windows/Fonts/msgothic.ttc",
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for font_path in font_candidates:
        if Path(font_path).exists():
            try:
                return ImageFont.truetype(font_path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def render_page(layout: dict, output_path: str) -> None:
    """1ページ分のコマ割り参照画像を生成する"""
    pl = layout["page_layout"]
    page_w = pl["width"]
    page_h = pl["height"]
    grid_cols, grid_rows = pl["grid"]
    margin = pl["margin"]
    gutter = pl.get("gutter", {"horizontal": 15, "vertical": 50})

    img = Image.new("RGB", (page_w, page_h), "white")
    draw = ImageDraw.Draw(img)

    line_width = 3
    font = get_font(48)

    for panel in layout["panels"]:
        panel_id = panel["id"]
        vertices = panel["vertices"]
        bleed = panel.get("bleed", [])

        vertices_px = [
            grid_to_pixel(v[0], v[1], grid_cols, grid_rows, margin, page_w, page_h)
            for v in vertices
        ]

        if bleed:
            vertices_px = apply_bleed(vertices_px, bleed, page_w, page_h)

        half_gutter_h = gutter["horizontal"] / 2
        half_gutter_v = gutter["vertical"] / 2

        xs = [v[0] for v in vertices_px]
        ys = [v[1] for v in vertices_px]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        rect_x0 = min_x + (half_gutter_h if min_x > 0 else 0)
        rect_y0 = min_y + (half_gutter_v if min_y > 0 else 0)
        rect_x1 = max_x - (half_gutter_h if max_x < page_w else 0)
        rect_y1 = max_y - (half_gutter_v if max_y < page_h else 0)

        draw.rectangle(
            [rect_x0, rect_y0, rect_x1, rect_y1],
            outline="black",
            width=line_width,
        )

        cx = (rect_x0 + rect_x1) / 2
        cy = (rect_y0 + rect_y1) / 2
        label = str(panel_id)
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((cx - tw / 2, cy - th / 2), label, fill="black", font=font)

    img.save(output_path)
    print(f"  -> {output_path}")


def process_single(input_yaml: str, output_png: str | None) -> None:
    """単一YAMLファイルを処理する"""
    layout = load_layout(input_yaml)
    if output_png is None:
        stem = Path(input_yaml).stem
        output_png = str(Path(input_yaml).parent / f"{stem}.png")
    render_page(layout, output_png)


def process_directory(yaml_dir: str, output_dir: str | None) -> None:
    """ディレクトリ内の全YAMLファイルを一括処理する"""
    yaml_dir_path = Path(yaml_dir)
    if output_dir is None:
        output_dir_path = yaml_dir_path
    else:
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)

    yaml_files = sorted(yaml_dir_path.glob("layout_page_*.yaml"))
    if not yaml_files:
        yaml_files = sorted(yaml_dir_path.glob("*.yaml"))

    if not yaml_files:
        print(f"YAMLファイルが見つかりません: {yaml_dir}")
        sys.exit(1)

    print(f"{len(yaml_files)} ファイルを処理します...")
    for yf in yaml_files:
        output_png = str(output_dir_path / f"{yf.stem}.png")
        layout = load_layout(str(yf))
        render_page(layout, output_png)

    print(f"完了: {len(yaml_files)} ページ分の画像を生成しました")


def main():
    parser = argparse.ArgumentParser(
        description="コマ割りYAMLからコマ割り参照画像（PNG）を生成する"
    )
    parser.add_argument("input", nargs="?", help="入力YAMLファイル")
    parser.add_argument("output", nargs="?", help="出力PNGファイル（省略時は入力と同名.png）")
    parser.add_argument("--dir", help="YAMLファイルが入ったディレクトリ（一括処理）")
    parser.add_argument("--out", help="出力ディレクトリ（--dir使用時）")
    args = parser.parse_args()

    if args.dir:
        process_directory(args.dir, args.out)
    elif args.input:
        process_single(args.input, args.output)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
