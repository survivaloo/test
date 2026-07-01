# USDJPYRate (テスト用iOSアプリ)

ドル円(USD/JPY)の為替レートを表示する、シンプルなSwiftUI製のテスト用iPhoneアプリです。

## 特徴

- [Frankfurter API](https://www.frankfurter.app/)(APIキー不要・無料)から最新のUSD/JPYレートを取得
- プルリフレッシュ・更新ボタンで最新レートを再取得
- 取得に失敗した場合はエラーメッセージを表示
- 取得日時を表示

## 動作環境

- Xcode 15以降
- iOS 16.0以降
- インターネット接続(レート取得のため)

## 開き方・実行方法

1. Mac上でXcodeをインストールしてください。
2. `USDJPYRate.xcodeproj` をXcodeで開きます。

   ```bash
   open ios/USDJPYRate/USDJPYRate.xcodeproj
   ```

3. Xcode上でシミュレータ(またはお使いのiPhone実機)を選択し、再生ボタン(▶)を押してビルド・実行します。
4. 実機で実行する場合は、Signing & Capabilities で自分のApple IDのチームを選択してください(無料のApple IDで問題ありません)。

## ファイル構成

```
USDJPYRate/
├── USDJPYRate.xcodeproj/        # Xcodeプロジェクトファイル
└── USDJPYRate/
    ├── USDJPYRateApp.swift            # アプリのエントリーポイント
    ├── ContentView.swift              # レート表示画面(SwiftUI)
    ├── ExchangeRateViewModel.swift    # レート取得ロジック(Frankfurter API)
    ├── Assets.xcassets/               # アイコン・カラー設定
    └── Preview Content/               # SwiftUIプレビュー用アセット
```

## 今後の拡張アイデア

- 過去のレート推移をグラフ表示
- 他の通貨ペアへの対応
- ウィジェット対応
- プッシュ通知でレート急変を通知
