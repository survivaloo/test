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
- **314A.T**: iシェアーズ ゴールドETF
- **424A.T**: グローバルX ゴールド ETF（為替ヘッジあり）
- **425A.T**: グローバルX ゴールド ETF
- **447A.T**: ステート・ストリート・スパイダーゴールドETF

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
**最も標準偏差が低いETF**: 424A.T（年率標準偏差 14.10%、為替ヘッジあり、信託報酬 0.1775%）

**為替ヘッジなしの場合**: 314A.T、425A.T（年率標準偏差 16.40%）

### 重要な発見
- 日本市場で為替ヘッジありのETFを選ぶと、米国市場より低い標準偏差を実現可能
- **424A.T（グローバルX）**: 最低標準偏差 + 東証最低水準の信託報酬（0.1775%）
- 為替ヘッジなしの場合、ドル円為替変動により標準偏差が約2.3%増加
- 流動性重視の場合は1540.T（純金上場信託、出来高850,000株/日）が最適
- 2025年に新規上場した424A.T、425A.T、447A.Tは低コストで注目

## 出力

- コンソール画面に詳細な分析結果を表示
- CSVファイルに結果を保存
  - `gold_etf_analysis_results.csv` (米国市場)
  - `japan_gold_etf_analysis_results.csv` (日本市場)
