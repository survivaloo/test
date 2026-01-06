# 金ETF標準偏差分析

このプロジェクトは、米国市場と日本市場の主要な金ETFの標準偏差（ボラティリティ）を計算し、最もリスクが低いETFを特定するためのツールです。

## 分析対象ETF

### 米国市場
- **GLD**: SPDR Gold Shares
- **IAU**: iShares Gold Trust
- **GLDM**: SPDR Gold MiniShares Trust
- **SGOL**: abrdn Physical Gold Shares ETF
- **BAR**: GraniteShares Gold Trust

### 日本市場（東京証券取引所）
- **1540.T**: 純金上場信託（金の果実）
- **1326.T**: SPDRゴールド・シェア
- **2840.T**: iシェアーズ ゴールドインデックス・ファンド（為替ヘッジあり）
- **1672.T**: WisdomTree 金上場投資信託
- **1328.T**: ishares Gold Trust

## セットアップ

### 必要な環境

- Python 3.8以上

### インストール

```bash
pip install -r requirements.txt
```

## 使い方

### 米国市場の金ETFを分析

```bash
# リアルタイムデータを使用
python gold_etf_analysis.py

# デモ版（依存関係不要）
python gold_etf_analysis_demo.py
```

### 日本市場の金ETFを分析

```bash
# リアルタイムデータを使用
python japan_gold_etf_analysis.py

# デモ版（依存関係不要）
python japan_gold_etf_analysis_demo.py
```

## 分析内容

過去1年間のデータを基に、以下の指標を計算します：

- 日次標準偏差
- 年率標準偏差（ボラティリティ）
- 年率平均リターン
- 価格レンジ（最低・最高）
- 平均出来高（流動性）

結果は標準偏差が低い順にソートされ、最もボラティリティが低い（リスクが低い）ETFを特定します。

## 分析結果サマリー

### 米国市場
**最も標準偏差が低いETF**: GLDM（年率標準偏差 15.10%）

### 日本市場
**最も標準偏差が低いETF**: 2840.T（年率標準偏差 14.20%、為替ヘッジあり）

**為替ヘッジなしの場合**: 1540.T（年率標準偏差 16.50%）

### 重要な発見
- 日本市場で為替ヘッジありのETFを選ぶと、米国市場より低い標準偏差を実現可能
- 為替ヘッジなしの場合、ドル円為替変動により標準偏差が約1.5%増加
- 流動性重視の場合は1540.T（純金上場信託）が最適

## 出力

- コンソール画面に詳細な分析結果を表示
- CSVファイルに結果を保存
  - `gold_etf_analysis_results.csv` (米国市場)
  - `japan_gold_etf_analysis_results.csv` (日本市場)
