"""
manga_generator.py - Gemini API（画像生成モデル）で漫画画像を自動生成する

使い方:
    python manga_generator.py <art_prompt_yaml> <panel_image> <character_image> [output_png]
    python manga_generator.py --batch <prompts_dir> <panels_dir> <character_image> [--out <output_dir>]

環境変数 / .env:
    プロジェクト直下に .env を置くか、環境変数 GEMINI_API_KEY を設定する。
    .env 例:
        GEMINI_API_KEY=your-api-key-here

例:
    python manga_generator.py page_01.yaml panel_01.png character.png
    python manga_generator.py --batch art_prompts/ panel_images/ character.png --out manga_pages/
"""

import argparse
import base64
import os
import sys
import time
from io import BytesIO
from pathlib import Path

import yaml
from PIL import Image


def _load_env_from_dotenv() -> None:
    """プロジェクト直下の .env から環境変数を読み込む（あれば）"""
    # このファイルは scripts/ 配下にある想定なので、1つ上のディレクトリをプロジェクトルートとみなす
    project_root = Path(__file__).resolve().parents[1]
    dotenv_path = project_root / ".env"

    if not dotenv_path.exists():
        return

    try:
        for line in dotenv_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            # 既に環境変数が設定されている場合は .env 側で上書きしない
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        # 読み込み失敗時は静かに無視し、通常の環境変数だけを見る
        return


def get_client():
    """Gemini APIクライアントを取得する"""
    try:
        from google import genai
    except ImportError:
        print("google-genai パッケージが必要です。以下でインストールしてください:")
        print("  pip install google-genai")
        sys.exit(1)

    # まずは .env を読んでから環境変数を確認する
    _load_env_from_dotenv()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY が設定されていません。")
        print("プロジェクト直下に .env を作成して、次のように記述してください:")
        print("  GEMINI_API_KEY=your-api-key-here")
        print("もしくは OS の環境変数として GEMINI_API_KEY を設定してください。")
        print("APIキーは Google AI Studio (https://aistudio.google.com/) で取得できます。")
        sys.exit(1)

    return genai.Client(api_key=api_key)


def load_image_bytes(image_path: str) -> tuple[bytes, str]:
    """画像ファイルを読み込んでバイト列とMIMEタイプを返す"""
    path = Path(image_path)
    suffix = path.suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    mime_type = mime_map.get(suffix, "image/png")

    with open(path, "rb") as f:
        return f.read(), mime_type


def build_prompt_text(yaml_data: dict) -> str:
    """YAML データからGemini用のプロンプトテキストを構築する"""
    cp = yaml_data.get("comic_page", yaml_data)

    lines = []
    lines.append("以下の仕様に基づいて、漫画のページ画像を1枚生成してください。")
    lines.append("")

    if "instructions" in cp:
        lines.append(cp["instructions"])
        lines.append("")

    lines.append(f"スタイル: {cp.get('style', 'japanese manga')}")
    lines.append(f"カラーモード: {cp.get('color_mode', '白黒')}")
    lines.append(f"アスペクト比: {cp.get('aspect_ratio', '2:3')}")
    lines.append(f"言語: {cp.get('language', 'Japanese')}")
    lines.append(f"書字方向: {cp.get('writing-mode', 'vertical-rl')}")
    lines.append("")

    if "layout_constraints" in cp:
        lines.append("レイアウト制約:")
        lines.append(cp["layout_constraints"])
        lines.append("")

    if "character_infos" in cp:
        lines.append("キャラクター設定:")
        for char in cp["character_infos"]:
            lines.append(f"  - {char['name']}: {char.get('base_prompt', '')}")
        lines.append("")

    if "panels" in cp:
        lines.append("コマ構成:")
        for panel in cp["panels"]:
            pnum = panel.get("number", "?")
            pos = panel.get("page_position", "")
            bleed = panel.get("bleed", [])
            bg = panel.get("background", "")
            desc = panel.get("description", "")
            cam = panel.get("camera_angle", "")

            lines.append(f"  --- コマ{pnum} (位置:{pos}, カメラ:{cam}) ---")
            if bleed:
                lines.append(f"  断ち切り: {', '.join(bleed)}")
            if bg:
                lines.append(f"  背景: {bg}")
            if desc:
                lines.append(f"  説明: {desc}")

            for char in panel.get("characters", []):
                char_lines = []
                char_lines.append(f"    キャラ: {char.get('name', '?')}")
                char_lines.append(f"    位置: {char.get('panel_position', '')}")
                char_lines.append(f"    感情: {char.get('emotion', '')}")
                char_lines.append(f"    向き: {char.get('facing', '')}")
                char_lines.append(f"    画角: {char.get('shot', '')}")
                char_lines.append(f"    ポーズ: {char.get('pose', '')}")
                if char.get("scale"):
                    char_lines.append(f"    スケール: {char['scale']}")
                if char.get("description"):
                    char_lines.append(f"    補足: {char['description']}")
                lines.extend(char_lines)

                for line in char.get("lines", []):
                    line_type = line.get("type", "speech")
                    text = line.get("text", "")
                    tpos = line.get("char_text_position", "")
                    lines.append(f"    セリフ({line_type}, {tpos}):「{text}」")

            for mono in panel.get("monologues", []):
                text = mono.get("text", "")
                tpos = mono.get("text_position", "")
                shape = mono.get("balloon_shape", "長方形")
                lines.append(f"    ナレーション({tpos}, {shape}):「{text}」")

            effects = panel.get("effects", [])
            if effects:
                lines.append(f"    効果: {', '.join(effects)}")
            lines.append("")

    lines.append("添付のコマ割り参照画像に合わせてコマの配置を行い、")
    lines.append("添付のキャラクター参照画像に合わせてキャラクターの外見を描いてください。")
    lines.append("日本語のセリフは正確に、縦書きで吹き出し内に配置してください。")

    return "\n".join(lines)


def generate_manga_page(
    client,
    prompt_yaml_path: str,
    panel_image_path: str,
    character_image_path: str,
    output_path: str,
    model: str = "gemini-3-pro-image-preview",
) -> bool:
    """1ページ分の漫画画像を生成する"""
    from google.genai.types import GenerateContentConfig, Modality, Part

    with open(prompt_yaml_path, "r", encoding="utf-8") as f:
        yaml_data = yaml.safe_load(f)

    prompt_text = build_prompt_text(yaml_data)

    char_bytes, char_mime = load_image_bytes(character_image_path)
    panel_bytes, panel_mime = load_image_bytes(panel_image_path)

    contents = [
        "キャラクター参照画像:",
        Part.from_bytes(data=char_bytes, mime_type=char_mime),
        "コマ割り参照画像:",
        Part.from_bytes(data=panel_bytes, mime_type=panel_mime),
        prompt_text,
    ]

    config = GenerateContentConfig(
        response_modalities=[Modality.IMAGE, Modality.TEXT],
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data:
                image = Image.open(BytesIO(part.inline_data.data))
                image.save(output_path)
                print(f"  -> {output_path}")
                return True

        print(f"  画像が生成されませんでした: {prompt_yaml_path}")
        for part in response.candidates[0].content.parts:
            if part.text:
                print(f"  レスポンス: {part.text[:200]}")
        return False

    except Exception as e:
        print(f"  エラー: {e}")
        return False


def process_single(
    prompt_yaml: str,
    panel_image: str,
    character_image: str,
    output_png: str | None,
    model: str,
) -> None:
    """単一ページを処理する"""
    client = get_client()

    if output_png is None:
        stem = Path(prompt_yaml).stem
        output_png = str(Path(prompt_yaml).parent / f"manga_{stem}.png")

    print(f"生成中: {prompt_yaml}")
    generate_manga_page(client, prompt_yaml, panel_image, character_image, output_png, model)


def process_batch(
    prompts_dir: str,
    panels_dir: str,
    character_image: str,
    output_dir: str | None,
    model: str,
    delay: float = 2.0,
) -> None:
    """全ページを一括処理する"""
    client = get_client()

    prompts_path = Path(prompts_dir)
    panels_path = Path(panels_dir)

    if output_dir is None:
        out_path = prompts_path.parent / "manga_pages"
    else:
        out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    prompt_files = sorted(prompts_path.glob("page_*.yaml"))
    if not prompt_files:
        prompt_files = sorted(prompts_path.glob("*.yaml"))

    if not prompt_files:
        print(f"プロンプトYAMLが見つかりません: {prompts_dir}")
        sys.exit(1)

    panel_files = sorted(panels_path.glob("*.png"))
    panel_map = {f.stem: f for f in panel_files}

    print(f"{len(prompt_files)} ページを処理します...")
    print(f"モデル: {model}")
    print(f"出力先: {out_path}")
    print()

    success_count = 0
    for i, pf in enumerate(prompt_files):
        stem = pf.stem
        layout_stem = stem.replace("page_", "layout_page_")
        panel_file = panel_map.get(layout_stem) or panel_map.get(stem)

        if panel_file is None:
            candidates = list(panels_path.glob(f"*{stem.split('_')[-1]}*"))
            if candidates:
                panel_file = candidates[0]

        if panel_file is None:
            print(f"  スキップ: {stem} に対応するコマ割り画像が見つかりません")
            continue

        output_png = str(out_path / f"manga_{stem}.png")
        print(f"[{i+1}/{len(prompt_files)}] {pf.name}")

        ok = generate_manga_page(
            client, str(pf), str(panel_file), character_image, output_png, model
        )
        if ok:
            success_count += 1

        if i < len(prompt_files) - 1:
            time.sleep(delay)

    print()
    print(f"完了: {success_count}/{len(prompt_files)} ページ生成成功")


def main():
    parser = argparse.ArgumentParser(
        description="Gemini API（Nano Banana 2）で漫画画像を自動生成する"
    )

    parser.add_argument("prompt_yaml", nargs="?", help="作画プロンプトYAMLファイル")
    parser.add_argument("panel_image", nargs="?", help="コマ割り参照画像（PNG）")
    parser.add_argument("character_image", nargs="?", help="キャラクター参照画像（PNG）")
    parser.add_argument("output", nargs="?", help="出力PNGファイル（省略時は自動命名）")

    parser.add_argument("--batch", nargs=3, metavar=("PROMPTS_DIR", "PANELS_DIR", "CHAR_IMG"),
                        help="一括処理: プロンプトDir パネルDir キャラ画像")
    parser.add_argument("--out", help="出力ディレクトリ（--batch使用時）")
    parser.add_argument("--model", default="gemini-3-pro-image-preview",
                        help="使用するGeminiモデル（デフォルト: gemini-3-pro-image-preview）")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="一括処理時のリクエスト間隔（秒、デフォルト: 2.0）")

    args = parser.parse_args()

    if args.batch:
        prompts_dir, panels_dir, char_img = args.batch
        process_batch(prompts_dir, panels_dir, char_img, args.out, args.model, args.delay)
    elif args.prompt_yaml and args.panel_image and args.character_image:
        process_single(args.prompt_yaml, args.panel_image, args.character_image, args.output, args.model)
    else:
        parser.print_help()
        print()
        print("使用例:")
        print("  単一ページ:")
        print("    python manga_generator.py page_01.yaml panel_01.png character.png")
        print()
        print("  一括処理:")
        print("    python manga_generator.py --batch art_prompts/ panel_images/ character.png --out manga_pages/")
        sys.exit(1)


if __name__ == "__main__":
    main()
