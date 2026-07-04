# マーケット指標 (Web版 / PWA)

Mac不要・Apple ID不要・スマホだけで動かせる、経済指標表示アプリのWeb版です。

- **USD/JPY**: [Frankfurter API](https://www.frankfurter.app/)からリアルタイム取得
- **日本国債30年金利**: 財務省公表データ(`market-data.json`経由、日次更新)
- **米国失業率**: 米国労働統計局(BLS)公表データ(`market-data.json`経由、月次更新)
- **日本国債30年(ドル建て)**: 財務省(JGB30年利回り)・Frankfurter API(USD/JPY)から取得し、
  DCFモデルでJPY建て理論価格・修正デュレーションを算出した上でUSD/JPYレートを用いて
  米ドル換算価値(額面1万円あたり)を算出(`market-data.json`経由、日次更新)
- **明日の価格予測(AI分析)**: 入札結果・財政/金融政策を巡る不透明感・FRB要人発言などを
  JGB利回り変化とUSD/JPY変化それぞれについてベイズ統計で統合し、実測相関を用いた
  モンテカルロシミュレーションで米ドル換算価値の予測分布を算出。定性情報の解釈が必要な
  ため自動更新ではなく、分析セッションごとに手動更新するスナップショットです。

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
