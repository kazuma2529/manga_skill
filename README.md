## AI漫画自動生成パイプライン（やさしい説明）

このプロジェクトは、**「長い文章（原作テキスト）」から、AIの力を使って「漫画のページ画像（PNG）」を自動で作るための仕組み**です。

- 4つの **Cursor Agent Skill**（文章を分解したり、ネームを作ったりする役目）
- 2つの **Pythonスクリプト**（画像を実際に描かせる役目）

を組み合わせて動きます。

---

## 全体の流れ（まずざっくり）

文章から最終的な漫画画像ができるまでの「一本道」はこうなります。

1. **原作テキスト**（あなたが書いた文章）
2. `manga-cutlist`  
   → 文章を「カットリスト」（どんなコマが必要かのリスト）にする
3. `manga-storyboard`  
   → カットリストを「字コンテ」（ページ・コマごとの細かい指示）にする
4. `manga-art-prompt`  
   → 字コンテを、画像生成用の「作画プロンプトYAML」にする
5. `manga-panel-layout`  
   → 字コンテを、コマの位置や大きさを書いた「コマ割りYAML」にする
6. `panel_renderer.py`  
   → コマ割りYAMLから、「コマ割りだけ描いた白黒の参照画像（PNG）」を作る
7. `manga_generator.py`（Gemini API）  
   → キャラ画像 + コマ割り画像 + 作画プロンプトYAML から  
    **完成した漫画ページ画像（PNG）** を作る

図にすると、次のような流れです。

```text
文章（原作テキスト）
  │
  ▼ Skill 1: manga-cutlist
カットリスト（Markdown）
  │
  ▼ Skill 2: manga-storyboard
字コンテ（Markdown）
  │
  ├─▼ Skill 3: manga-art-prompt
  │   作画用プロンプト（YAML / ページごと）
  │
  └─▼ Skill 4: manga-panel-layout
      コマ割りYAML（ページごと）
        │
        ▼ panel_renderer.py
      コマ割り参照画像（PNG）

キャラ参照画像 + コマ割り参照画像 + 作画用プロンプト
  │
  ▼ manga_generator.py（Gemini API）
完成した漫画画像（PNG / ページごと）
```

---

## 事前準備（はじめにやること）

### 1. Python のライブラリを入れる

`scripts/requirements.txt` に必要なライブラリがまとまっています。

```bash
pip install -r scripts/requirements.txt
```

---

### 2. Gemini API キーを用意する

1. ブラウザで Google の `https://aistudio.google.com/` にアクセスして、Gemini の **APIキー** を発行します。
2. プロジェクト直下（`manga_skill/` の中）に `.env` というファイルを作り、次の1行だけを書きます。

```bash
GEMINI_API_KEY=your-api-key-here
```

- `.env.example` にひな形（サンプル）が入っています。
- もし OS の環境変数で `GEMINI_API_KEY` をすでに設定している場合は、そちらが優先されます。

---

## 実行手順（ゆっくり・詳しく）

ここからは、**「自分が何をするか」「裏で何が起きているか」「どんなファイルができるか」**を、ステップごとに説明します。

### Step 0: 入力の準備

- **原作テキスト**
  - `input/text/` フォルダに、元になる文章のテキストファイル（`.txt` など）を置きます。
  - 先頭付近に、次のようなタイトル行を書いておくと便利です。
    - `タイトル: 余命10年の僕が君に伝えたいこと`
  - この「タイトル」から、あとで自動的に `story_id`（作品ごとのID兼ファイル名のもと）が作られます。

- **キャラクター参照画像**
  - `input/characters/` フォルダに、キャラクターの画像（PNG など）を1枚以上置きます。
  - 例: `input/characters/character.png`

---

### Step 1: カットリストを作る（manga-cutlist）

- **あなたがやること**
  - Cursor で `@manga-cutlist` スキルを添付し、原作テキストを貼り付けて、こうお願いします。

    > この文章からカットリストを作ってください。

- **裏で何が起きているか**
  - 原作テキストを読んで、
    - どんな場面があるか
    - 誰がしゃべるか
    - どんな順番で見せるか  
      を、**「カット」という単位**で細かく分けていきます。
  - 「1カット = だいたい1コマで表現できるまとまり」というイメージです。
  - シーンの切り替え（回想/場面転換）なども、読者が混乱しないように丁寧に挿入されます。

- **できあがるファイル**
  - `output/cutlist/{story_id}.md`  
    （既にある場合は上書きされます）

※ スキルの仕様上、**カットリスト全文はチャットにはベタっと出さず、必ずファイルに保存**されます。

---

### Step 2: 字コンテを作る（manga-storyboard）

- **あなたがやること**
  - Cursor で `@manga-storyboard` スキルを添付し、Step 1 でできたカットリストを渡して、こうお願いします。

    > このカットリストから字コンテを作ってください。

- **裏で何が起きているか**
  - カットリストの「カット」を、**ページ・コマごとの具体的な指示**に変換します。
  - 例:
    - 「1ページ目・1コマ目・右上・バストアップ・こういう表情・このセリフ…」
  - 日本式マンガの基本（右上から読み始めて左下に終わる、1ページ3〜5コマくらい、見せ場は大きく）などを守りながら組み立てます。
  - ここがいわゆる「ネーム」に相当し、**ここで内容を納得するまで直すのがおすすめ**です。

- **できあがるファイル**
  - `output/storyboard/{story_id}.md`  
    （既にある場合は上書きされます）

※ ここでも、**本文はファイルに保存され、チャットにはサマリーだけ**が返るようになっています。

---

### Step 3: 作画用プロンプトYAMLを作る（manga-art-prompt）

- **あなたがやること**
  - Cursor で `@manga-art-prompt` スキルを添付し、字コンテとキャラ設定を渡します。

    例）

    > この字コンテから作画用プロンプトYAMLをページごとに生成してください。  
    > キャラクター: ○○ - 黒髪ショート、20代女性、カジュアルな服装

- **裏で何が起きているか**
  - 字コンテに書かれた情報（コマの位置、キャラの表情・ポーズ・セリフなど）を、  
    **画像生成AIが読みやすいYAML形式**に翻訳します。
  - 1ページにつき 1 つ、`page_01.yaml` のようなファイルを作ります。
  - `comic_page` / `panels` / `character_infos` などの項目に、
    - どんな画風か（例: “japanese shoujo manga”）
    - 縦書き／右から左に読む
    - 各コマの説明・キャラの感情・セリフ  
      が詰め込まれます。

- **できあがるファイル**
  - `output/art_prompts/page_01.yaml`
  - `output/art_prompts/page_02.yaml`
  - …  
    （後で `manga_generator.py` が読むファイル。既にある場合は上書きされます）

---

### Step 4: コマ割りYAMLを作る（manga-panel-layout）

- **あなたがやること**
  - Cursor で `@manga-panel-layout` スキルを添付し、字コンテを渡して、こうお願いします。

    > この字コンテからコマ割り用YAMLをページごとに生成してください。

- **裏で何が起きているか**
  - コマの「位置」情報（top / middle-right / bottom-left など）から、  
    **ページ全体を 6×6 グリッドに区切ったときの座標データ**を作ります。
  - 例：
    - ページの上 1/3 を使うコマ
    - 真ん中を左右に分けるコマ
    - 下を左右に分けるコマ
  - これが、あとで `panel_renderer.py` が読む「設計図」になります。

- **できあがるファイル**
  - `output/panel_layouts/layout_page_01.yaml`
  - `output/panel_layouts/layout_page_02.yaml`
  - …  
    （後で `panel_renderer.py` が読むファイル。既にある場合は上書きされます）

---

### Step 5: コマ割り参照画像（枠線だけの画像）を作る

ここから Python スクリプトの出番です。

- **あなたがやること**
  - ターミナル（PowerShell など）で、プロジェクト直下に移動して次を実行します。

```bash
python scripts/panel_renderer.py --dir output/panel_layouts --out output/panel_images
```

- **裏で何が起きているか**
  - `output/panel_layouts` フォルダの `layout_page_*.yaml` を全部読み込み、
    - ページサイズ（1000×1500ピクセル）
    - 6×6 のグリッド
    - margin / gutter（余白やコマの間のすき間）  
      を使って、**黒い枠線だけの「コマ割り参照画像」**を描きます。
  - 各コマには番号が書かれているので、「ここが1コマ目、ここが2コマ目」というのがひと目で分かります。

- **できあがるファイル**
  - `output/panel_images/layout_page_01.png`
  - `output/panel_images/layout_page_02.png`
  - …  
    （既にある場合は上書きされます）

---

### Step 6: 最終的な漫画ページ画像を生成する（manga_generator.py）

#### 単一ページだけ試す場合

- **あなたがやること**

```bash
python scripts/manga_generator.py \
  output/art_prompts/page_01.yaml \
  output/panel_images/layout_page_01.png \
  input/characters/character.png \
  output/manga_pages/manga_page_01.png
```

引数の意味はこの順番です。

1. `output/art_prompts/page_01.yaml`  
   → Step 3 で作った「作画用プロンプトYAML」
2. `output/panel_images/layout_page_01.png`  
   → Step 5 で作った「コマ割り参照画像」
3. `input/characters/character.png`  
   → キャラクターの見た目の基準になる画像
4. `output/manga_pages/manga_page_01.png`  
   → 出力したいファイル名（省略すると自動命名）

- **裏で何が起きているか**
  - `.env`（もしくは環境変数）から `GEMINI_API_KEY` を読み取って、Gemini のクライアントを作る。
  - YAML を読んで、Gemini に渡す **日本語の説明テキスト（プロンプト）** を組み立てる。
  - キャラ画像・コマ割り画像・テキストの3つをまとめて Gemini に送り、
    - 「このキャラの見た目」
    - 「このコマ割りのレイアウト」
    - 「この内容・セリフ」  
      に従った **漫画ページ画像1枚** を生成してもらう。
  - 戻ってきた画像データを `output/manga_pages/manga_page_01.png` に保存する。

---

#### 全ページをまとめて生成したい場合

- **あなたがやること**

```bash
python scripts/manga_generator.py \
  --batch output/art_prompts output/panel_images input/characters/character.png \
  --out output/manga_pages
```

- **裏で何が起きているか**
  - `output/art_prompts` 内の `page_*.yaml` を全部探す。
  - 各ページに対して、対応するコマ割り画像（`layout_page_XX.png` など）を探す。
  - 1ページずつ、Gemini にリクエストを送り、
    - `output/manga_pages/manga_page_01.png`
    - `output/manga_pages/manga_page_02.png`
    - …  
      のようなファイルとして保存する。
  - ページとページの間には、`--delay` で指定した秒数だけ待つ（デフォルト2秒）。

- **オプション**
  - `--model`  
    デフォルトは `gemini-3-pro-image-preview`。  
    他の対応モデルを試したいときはここを変えます。
  - `--delay`  
    一括処理で API を叩く間隔（秒）。デフォルトは `2.0`。

---

### 一括実行させたい場合

@manga-pipeline  
input/text/story_ikuma.md のテキストから漫画を作ってください。
キャラ画像: input/characters/character.png

---

## フォルダ構成（ざっくり意味だけ）

```text
manga_skill/
├── skills/                  # 4つの Cursor Agent Skill（文章→漫画用データ変換）
│   ├── manga-cutlist/       # 原作テキスト → カットリスト
│   ├── manga-storyboard/    # カットリスト → 字コンテ
│   ├── manga-art-prompt/    # 字コンテ → 作画プロンプトYAML（ページごと）
│   └── manga-panel-layout/  # 字コンテ → コマ割りYAML（ページごと）
│
├── scripts/
│   ├── panel_renderer.py    # コマ割りYAML → コマ割り参照画像（PNG）
│   ├── manga_generator.py   # Gemini API で最終漫画画像を生成
│   └── requirements.txt     # 必要なPythonライブラリ
│
├── input/
│   ├── text/                # 原作テキストの置き場所
│   └── characters/          # キャラ参照画像の置き場所
│
├── output/
│   ├── cutlist/             # カットリスト
│   ├── storyboard/          # 字コンテ
│   ├── art_prompts/         # 作画用プロンプトYAML
│   ├── panel_layouts/       # コマ割りYAML
│   ├── panel_images/        # コマ割り参照画像（PNG）
│   └── manga_pages/         # 完成した漫画ページ（PNG）
│
└── README.md
```
