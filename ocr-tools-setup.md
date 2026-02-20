# OCR ツール セットアップ記録

## 1. GLM-OCR Local Console

### 概要

- **モデル**: zai-org/GLM-OCR
- **フレームワーク**: FastAPI + Web UI（シングルページ HTML）
- **ライセンス**: MIT
- **場所**: `/home/survivaloo/GLM-OCR-server/`
- **URL**: http://192.168.1.85:9000
- **API Docs**: http://192.168.1.85:9000/docs

### 動作環境

- Python 3.10+
- Windows または Linux/macOS
- CUDA 使用時は対応 GPU + ドライバ（現在は CPU モードで動作中）

### ファイル構成

```
GLM-OCR-server/
├── app/
│   ├── main.py                    # FastAPI メインアプリ（39KB）
│   ├── layout_ppdoclayoutv3.py    # レイアウト解析モジュール
│   └── static/                    # 静的ファイル
├── models/
│   ├── hf_cache/                  # モデルキャッシュ
│   └── hf_home/                   # HuggingFace Home
├── .venv/                         # Python 仮想環境
├── .env                           # 環境設定
├── run.sh                         # Linux 起動スクリプト
├── run.bat                        # Windows 起動スクリプト
├── README.md
└── LICENSE
```

### 設定（.env）

```env
HOST=0.0.0.0
PORT=9000
# TORCH_CHANNEL=cu126   # GPU使用時
```

主な設定値:
- `HOST`: バインドアドレス（デフォルト `0.0.0.0`）
- `PORT`: 起動ポート（デフォルト `8000`、現在 `9000` に変更済み）
- `TORCH_CHANNEL`: PyTorch 配布チャネル（`cu126`, `cpu` など）

### 起動方法

```bash
cd /home/survivaloo/GLM-OCR-server
./run.sh
```

初回起動時に以下が自動インストールされる:
- PyTorch（CPU or CUDA）
- FastAPI, uvicorn, Pillow, pypdfium2, accelerate
- PaddleOCR（レイアウト解析用、オプション）
- transformers（開発版、HuggingFace git から）

### 機能一覧

| 機能 | 説明 |
|---|---|
| **Text OCR** | 画像/PDF からテキスト抽出 |
| **Table OCR** | 表構造の認識 |
| **Formula OCR** | 数式認識 |
| **JSON 抽出** | JSON Schema を指定して構造化データ抽出 |
| **レイアウト OCR** | PP-DocLayoutV3 による領域分割OCR（段組み・縦書き対応） |
| **PDF 入力** | pypdfium2 でページ単位に画像化してOCR |
| **進捗表示** | リアルタイムで処理状況を表示 |
| **中断機能** | 実行中のOCRを途中で停止可能 |
| **改行処理** | none / paragraph（段落整形）/ compact（改行除去） |

### API エンドポイント

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/api/status` | CUDA 可否、モデル ID、キャッシュディレクトリを返す |
| POST | `/api/analyze` | OCR 実行（マルチパートフォーム） |
| GET | `/api/progress/{request_id}` | 進捗状態を取得 |
| POST | `/api/cancel/{request_id}` | 中断要求 |

### `/api/analyze` パラメータ

| パラメータ | 必須 | デフォルト | 説明 |
|---|---|---|---|
| file | Yes | - | 画像/PDF ファイル |
| device | No | auto | auto / cuda / cpu |
| dpi | No | 220 | PDF レンダリング DPI |
| task | No | text | text / table / formula / extract_json |
| linebreak_mode | No | none | none / paragraph / compact |
| schema | extract_json 時 | - | 出力 JSON Schema |
| max_new_tokens | No | 1024 | 生成トークン上限 |
| temperature | No | 0 | 生成のランダム性（0 = 決定的） |
| use_layout | No | false | レイアウト解析の ON/OFF |
| layout_backend | No | ppdoclayoutv3 | レイアウト解析エンジン |
| reading_order | No | auto | auto / ltr_ttb / rtl_ttb / vertical_rl |
| region_padding | No | 12 | 領域の余白（px） |
| max_regions | No | 200 | 1ページの領域上限 |
| region_parallelism | No | 1 | 同時推論数 |

### 現在のステータス

```json
{
  "cuda_available": false,
  "device_default": "cpu",
  "model": "zai-org/GLM-OCR",
  "model_cache_dir": "/home/survivaloo/GLM-OCR-server/models/hf_cache"
}
```

---

## 2. YomiToku（参考：日本語特化 OCR）

https://kotaro-kinoshita.github.io/yomitoku/installation/

### 概要

日本語に特化した AI-OCR ライブラリ。レイアウト解析、テキスト検出、文字認識を統合的に提供。

### システム要件

- Python 3.10+
- PyTorch
- GPU 推奨（VRAM 8GB 以上）、CPU でも動作可能
- 軽量モデルは CPU でも高速

### インストール方法

#### PyPI から

```bash
pip install yomitoku
```

#### uv を使用（推奨）

```bash
git clone <yomitoku repo>
cd yomitoku

# CPU
uv sync

# GPU
uv sync --extra gpu
```

※ GPU 使用時は `pyproject.toml` の CUDA バージョンを自分の環境に合わせて修正（デフォルト CUDA 12.4）

#### Docker

```bash
# ビルド
docker build -t yomitoku .

# GPU 使用
docker run -it --gpus all -v $(pwd):/workspace --name yomitoku yomitoku /bin/bash

# CPU 使用
docker run -it -v $(pwd):/workspace --name yomitoku yomitoku /bin/bash
```

### オフライン環境での利用

1. 初回実行時に Hugging Face Hub からモデルが自動ダウンロードされる
2. 事前に `download_model` コマンドでダウンロード可能
3. `KotaroKinoshita` ディレクトリをカレントディレクトリに配置すればオフライン実行可能

### GLM-OCR との比較

| | GLM-OCR | YomiToku |
|---|---|---|
| 対応言語 | 多言語 | 日本語特化 |
| モデル | GLM ベース（VLM） | 独自モデル群 |
| 方式 | Vision-Language Model で直接 OCR | レイアウト解析 + テキスト検出 + 文字認識 |
| 導入 | run.sh で自動セットアップ | pip install |
| GPU | 推奨（CPU も可） | 推奨（VRAM 8GB+、CPU も可） |
