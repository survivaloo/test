# 金ETF標準偏差分析

このプロジェクトは、主要な金ETFの標準偏差（ボラティリティ）を計算し、最もリスクが低いETFを特定するためのツールです。

## 分析対象ETF

- **GLD**: SPDR Gold Shares
- **IAU**: iShares Gold Trust
- **GLDM**: SPDR Gold MiniShares Trust
- **SGOL**: abrdn Physical Gold Shares ETF
- **BAR**: GraniteShares Gold Trust

## セットアップ

### 必要な環境

- Python 3.8以上

### インストール

```bash
pip install -r requirements.txt
```

## 使い方

```bash
python gold_etf_analysis.py
```

## 分析内容

過去1年間のデータを基に、以下の指標を計算します：

- 日次標準偏差
- 年率標準偏差（ボラティリティ）
- 年率平均リターン
- 価格レンジ（最低・最高）

結果は標準偏差が低い順にソートされ、最もボラティリティが低い（リスクが低い）ETFを特定します。

## 出力

- コンソール画面に詳細な分析結果を表示
- `gold_etf_analysis_results.csv`にCSV形式で結果を保存
