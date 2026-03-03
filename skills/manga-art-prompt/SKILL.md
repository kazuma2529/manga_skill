---
name: manga-art-prompt
description: 字コンテを画像生成AI（Nano Banana 2 / Gemini）用の作画プロンプトYAMLに変換するスキル。「作画プロンプトを作って」「YAMLプロンプトに変換して」等のリクエストでトリガーされる。
---

# manga-art-prompt: 字コンテ → 作画用プロンプトYAML変換

字コンテの演出指示を、画像生成AI（Gemini / Nano Banana 2）が高精度で理解できるYAML形式に翻訳する。
ページ単位で1つのYAMLファイルを生成する。

## 入力

- manga-storyboard スキルで生成された字コンテ
- キャラクター設定（名前、外見の特徴）

## 出力

- ページごとに1つのYAMLファイルを出力する。
- **最新版ファイル名**: `output/art_prompts/page_[NN].yaml`（`NN` は2桁ゼロ埋め）

YAMLの構造は `references/yaml_template.yaml` を参照すること。

## 変換ルール

### comic_page（ページ全体の設定）
- `language`: "Japanese"（固定）
- `style`: 作品のジャンルに合わせる。例: "japanese shoujo manga, emotional, slice of life"
- `writing-mode`: "vertical-rl"（日本語縦書き、固定）
- `color_mode`: "白黒" または "カラー"（ユーザー指定に従う、デフォルトは白黒）
- `aspect_ratio`: "2:3"（縦長の漫画ページ、固定）

### instructions
以下の内容を含む全体指示文を生成する:
```
このYAMLは漫画ページの仕様です。添付の画像データ（キャラクター等、コマ割り画像）がある場合は、
それらを外見の基準として忠実に反映し、このプロンプトの指示に従ってページを生成してください。
```

### layout_constraints
以下の制約を記述する:
```
- 読み順は panel.number の昇順
- 日本語縦書きマンガ、右から左に読む
```

### character_infos
各キャラクターの情報を定義する:
- `name`: キャラ名（日本語）
- `base_prompt`: 外見を英語で記述するプロンプト

**base_prompt の書き方**:
- 性別、年齢、体型から始める: "girl, 25 years old, small chest"
- 髪型: "flipped hair, black hair, short hair" 等
- 服装: "long sleeve, white t shirt, black pants" 等
- 特徴: "(thick lips:1.1)" のように強調度を付けられる
- Stable Diffusion / NovelAI 系の記法を参考にする
- 全て英語カンマ区切り

### panels（各コマの詳細）

字コンテの各コマを以下の構造に変換する:

- `number`: コマ番号（1から連番）
- `page_position`: 字コンテの位置指定をそのまま使用（"top", "middle", "bottom" 等）
- `bleed`: 断ち切り方向の配列。なしの場合は空配列 `[]`
- `background`: 背景の説明（日本語OK）
- `description`: コマ全体の説明（日本語OK）
- `objects`: 背景に配置するオブジェクト（建物、小物など）
- `characters`: 各キャラの演技指示
  - `name`: キャラ名
  - `panel_position`: コマ内の位置（"center", "left", "right"）
  - `emotion`: 表情・感情（日本語OK、具体的に）
  - `facing`: 向き（"正面", "斜め", "横顔", "背面", "斜め下" 等）
  - `shot`: 画角（"バストアップ", "顔アップ", "ロングショット" 等）
  - `pose`: ポーズ（日本語で具体的に）
  - `scale`: サイズ指定（"小さめ" 等。通常は空文字）
  - `description`: 補足説明
  - `lines`: セリフ配列
    - `text`: セリフのテキスト
    - `char_text_position`: 吹き出しの位置（"right", "left", "center", "top", "bottom"）
    - `type`: "speech"（通常セリフ）, "shout"（叫び）, "whisper"（囁き）, "thought"（心の声）
- `effects`: 効果（"キラキラ効果", "集中線", "汗マーク" 等の配列）
- `monologues`: ナレーション配列
  - `text`: ナレーションのテキスト
  - `text_position`: 位置（"top-right", "top-left", "bottom-right", "bottom-left"）
  - `balloon_shape`: 枠の形状（"長方形" が基本）
- `camera_angle`: カメラアングル英語表記（"medium shot", "close-up", "wide shot", "extreme close-up", "long shot"）

### 画角の対応表
| 字コンテの画角     | camera_angle       |
| ------------------ | ------------------ |
| 顔アップ           | close-up           |
| バストアップ       | medium shot        |
| 膝上               | medium shot        |
| ロングショット     | long shot          |
| ワイドショット     | wide shot          |
| 極端なアップ       | extreme close-up   |

### セリフ位置の配置ルール
- 右から左に読むため、先に読ませたいセリフは右側（"right"）に配置
- キャラの口元に近い位置を選ぶ
- ナレーションはコマの角（"top-right" 等）に配置

## 注意事項

- 1ページごとに独立したYAMLファイルとして出力する
- 字コンテの情報を漏れなく変換する
- base_prompt は全ページで統一する（キャラの外見がブレないように）
- YAMLの文法エラーがないよう、クォーテーションとインデントに注意する

## ファイル出力仕様（重要）

このスキルは、**チャットにYAML本文を表示せず、`output/` 配下に必ずファイルとして保存する**。

### 作品タイトルと story_id の取得

- 入力として与えられる字コンテには、次のような行が含まれていると想定する:
  - `タイトル: 余命10年の僕が君に伝えたいこと`
- この行から作品タイトル文字列を取得し、`manga-cutlist` / `manga-storyboard` と同じルールで `story_id` を決定する:
  - `タイトル:` 以降をトリム
  - `/ \ : * ? " < > |` を `_` に置換
  - 先頭・末尾の空白やピリオドを削除
- `タイトル:` 行が見つからない場合は、`story_id = "untitled"` とする。

### ディレクトリ構成

- **最新版（`manga_generator.py` が読む想定のファイル）**:
  - ベースディレクトリ: `output/art_prompts/`
  - パス: `output/art_prompts/page_{NN}.yaml`（`NN` は2桁ゼロ埋め）
  - 同じページ番号で再実行した場合、ここは **上書きして最新状態を保つ**。
- **履歴（すべて残すアーカイブ）**:
  - ベースディレクトリ: `output/history/art_prompts/`
  - 作品ごとのディレクトリ: `output/history/art_prompts/{story_id}/`
- ディレクトリがなければ自動的に作成してから保存する。

### ファイル名とバージョン管理

- 1回の実行で、対象となる **全ページのYAMLを生成** し、それぞれを個別ファイルとして保存する。
- 1回の実行単位で共通のタイムスタンプ（`run_id`）を付与し、**履歴側では上書きせずにすべて残す**。
- `run_id` は `YYYYMMDD-HHMMSS` 形式のタイムスタンプを推奨する。
- 各ページファイルのパスは次の2系統とする:
  - 最新版: `output/art_prompts/page_{NN}.yaml`
  - 履歴: `output/history/art_prompts/{story_id}/page_{NN}_{run_id}.yaml`
  - `NN` は2桁ゼロ埋めのページ番号（例: 1ページ目 → `01`）

### チャット出力ポリシー

- YAML本文（`comic_page`, `panels` などの詳細構造）は **チャットに出力しない**。
- 代わりに、次のような **保存結果の要約のみ** を返す:
  - 作品タイトル
  - 対象ページ範囲（例: 1〜10ページ）
  - 生成したページ数
  - 保存されたファイルパスのパターン（先頭の1〜2件だけ具体的に示し、「…」で省略してよい）
- 例:
  - `作画用プロンプトYAMLを 10ページ分生成し、output/art_prompts/page_01.yaml 〜 page_10.yaml に保存し、履歴として output/history/art_prompts/余命10年の僕が君に伝えたいこと/page_01_20260303-235959.yaml などを作成しました。`

### 実装上の注意

- 1回の実行内で生成するすべてのページファイルに、同じ `run_id` を付与して「同一バージョン」のセットであることが分かるようにする。
- Cursorのファイル書き込み機能を用いて、上記パスにYAMLファイルを書き込むこと。
- 既存のYAMLファイルとパスが衝突しないよう、`run_id` により一意性を担保する。

