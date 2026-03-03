---
name: manga-pipeline
description: 原作テキストから完成した漫画画像まで全工程を一括実行する。
「漫画を作って」「全部やって」等でトリガーされる。
---

# manga-pipeline: 原作 → 完成漫画 一括生成

## 実行手順

ユーザーから原作テキストとキャラ画像パスを受け取ったら、
以下を順番に実行すること。

### Step 1: カットリスト生成

`skills/manga-cutlist/SKILL.md` を読み、その指示に従って実行する。

### Step 2: 字コンテ生成

Step1の出力を使い、`skills/manga-storyboard/SKILL.md` を読んで実行する。

### Step 3 & 4: YAMLの並行生成

Step2の出力を使い、以下を**並行して**実行する：

- `skills/manga-art-prompt/SKILL.md` を読んで実行
- `skills/manga-panel-layout/SKILL.md` を読んで実行

### Step 5: コマ割り参照画像の生成

以下のコマンドを実行する：
python scripts/panel_renderer.py --dir output/panel_layouts --out output/panel_images

### Step 6: 漫画画像の一括生成

以下のコマンドを実行する：
python scripts/manga_generator.py \
 --batch output/art_prompts output/panel_images {character_image_path} \
 --out output/manga_pages
