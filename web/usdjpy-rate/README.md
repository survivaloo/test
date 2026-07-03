# マーケット指標 (Web版 / PWA)

Mac不要・Apple ID不要・スマホだけで動かせる、経済指標表示アプリのWeb版です。

- **USD/JPY**: [Frankfurter API](https://www.frankfurter.app/)からリアルタイム取得
- **日本国債30年金利**: 財務省公表データ(`market-data.json`経由、日次更新)
- **米国失業率**: 米国労働統計局(BLS)公表データ(`market-data.json`経由、月次更新)
- **米国30年国債(ドル建て)**: FRED(利回りDGS30)・Yahoo Finance(ZB先物)から取得し、
  DCFモデルで理論価格・修正デュレーションを算出(`market-data.json`経由、日次更新)
- **明日の価格予測(AI分析)**: FRB要人発言・入札需給・JGB波及効果などをベイズ統計で統合し、
  モンテカルロシミュレーションで算出した価格予測。定性情報の解釈が必要なため
  自動更新ではなく、分析セッションごとに手動更新するスナップショットです。

`market-data.json` は `scripts/fetch_market_data.py` を GitHub Actions
(`.github/workflows/update-market-data.yml`) で毎日自動実行して更新しています。
財務省・BLSのAPIはブラウザから直接叩くとCORSでブロックされるため、
ビルド時に取得したJSONを同一オリジンの静的ファイルとして配信する方式にしています。

> **注意**: 「明日の価格予測」は教育・分析目的の試験的なモデル出力であり、投資助言ではありません。

## 使い方(iPhoneのみでOK)

1. Safariで公開URLを開く
2. 画面下部の「共有」ボタン(四角に上矢印のアイコン)をタップ
3. 「ホーム画面に追加」を選択
4. ホーム画面にアイコンが追加され、以後はアプリのようにタップで起動可能

ネイティブのiOSアプリ(`ios/USDJPYRate/`)と見た目・機能はほぼ同じです。App Store経由でのインストールではないため審査や証明書は不要です。

## 公開先

GitHub Pagesで公開されています: https://survivaloo.github.io/test/
