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

## 開き方・実行方法(シミュレータ)

1. Mac上でXcodeをインストールしてください。
2. `USDJPYRate.xcodeproj` をXcodeで開きます。

   ```bash
   open ios/USDJPYRate/USDJPYRate.xcodeproj
   ```

3. Xcode上でシミュレータを選択し、再生ボタン(▶)を押してビルド・実行します。

## 実機(お使いのiPhone)にインストールする方法

必要なもの: Mac、Xcode、iPhone本体、USB-C/Lightningケーブル、Apple ID(無料のもので可)。

1. **iPhoneをMacに接続する**
   ケーブルで接続し、iPhoneに「このコンピュータを信頼しますか？」と出たら「信頼」をタップしてパスコードを入力します。

2. **Xcodeで実行先を実機に切り替える**
   Xcode上部の実行先選択(シミュレータ名が表示されている部分)をクリックし、接続したiPhoneを選択します。

3. **署名(Signing)を設定する**
   - 左側ナビゲータで「USDJPYRate」プロジェクト → TARGETSの「USDJPYRate」を選択
   - 「Signing & Capabilities」タブを開く
   - 「Team」で自分のApple IDを選択(未登録なら「Add an Account...」からサインイン)
   - 「Bundle Identifier」が他人と重複する場合は `com.example.usdjpyrate` を `com.yourname.usdjpyrate` のような一意な値に変更する

4. **ビルド＆インストール**
   Xcode左上の再生ボタン(▶)または `⌘R` を押すと、ビルドされてiPhoneに自動インストール・起動します。

5. **「信頼されていないデベロッパ」エラーが出た場合**
   iPhoneの「設定」→「一般」→「VPNとデバイス管理」を開き、対象のデベロッパ(自分のApple ID)を選んで「"〇〇" を信頼」をタップします。その後ホーム画面のアイコンから起動できます。

6. **補足**
   無料のApple IDで署名した場合、証明書は7日間で失効します。期限が切れたら再度Macに接続し `⌘R` で入れ直してください。

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
