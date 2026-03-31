# Browser Windows App Runner - 企画書

## Context

ブラウザ上でWindows PEバイナリ（メモ帳 notepad.exe）をOS無しで直接実行するプロジェクト。
コンセプトは「ブラウザ版Wine」— フルOSエミュレーション（v86等）ではなく、PE解析 + x86エミュレーション + Win32 APIシム層で軽量に実現する。

## アーキテクチャ概要

```
┌──────────────────────────────────────────────────┐
│  ブラウザ (HTML5 + TypeScript)                    │
│                                                   │
│  ┌───────────┐  ┌───────────┐  ┌──────────────┐ │
│  │ PE Parser  │→│ PE Loader  │→│ Unicorn.js   │ │
│  │ (ヘッダ    │  │ (セクション │  │ x86 WASM     │ │
│  │  解析)     │  │  マッピング │  │ エミュレータ │ │
│  └───────────┘  │  IAT構築)  │  └──────┬───────┘ │
│                  └───────────┘         │          │
│                           CALL [stub addr] 検知   │
│                                        ↓          │
│  ┌───────────────────────────────────────────────┐│
│  │  API Registry (stub addr → JS handler)        ││
│  │  ┌─────────┬────────┬───────┬──────────────┐ ││
│  │  │kernel32 │user32  │gdi32  │comdlg32 etc. │ ││
│  │  └─────────┴────────┴───────┴──────────────┘ ││
│  └───────────────────────────────────────────────┘│
│                        │                          │
│                        ↓                          │
│  ┌───────────────────────────────────────────────┐│
│  │  GUI レンダラー                                ││
│  │  Window Manager (HWND→DOM) + Canvas (GDI描画) ││
│  │  メニュー (HTML) + Editコントロール (textarea) ││
│  └───────────────────────────────────────────────┘│
└──────────────────────────────────────────────────┘
```

## 重要な設計判断

### 1. Unicorn.js を採用（自作x86インタプリタではなく）
- Unicorn Engine のWASMコンパイル版で、完全なx86命令セットを正確にエミュレート
- 自作は数週間かかる上にバグが多い。PoC では正確性を優先
- ~19MB だがWASMで十分な実行速度

### 2. IAT スタブによるAPI呼び出しインターセプト
- PEのImport Address Tableに「マジックアドレス」(0x70000000〜) を書き込む
- 各Win32 API関数に一意のスタブアドレスを割り当て、そこに `0xCC` (INT3) を配置
- `UC_HOOK_CODE` (またはINT3フック) でCPUがスタブアドレスに到達したことを検知
- stdcall規約に従いスタックから引数を読み取り、EAXに戻り値をセットし、EIPをリターンアドレスに復帰

### 3. GetMessage ブロッキング問題の解決
Win32の `GetMessage` は同期的にブロックするが、ブラウザはシングルスレッド。解決策:
```
GetMessage呼出し → キューが空なら:
  1. CPU実行を停止 (emu_stop)
  2. ブラウザのイベントループに制御を返す
  3. DOMイベント発生 → Win32メッセージに変換 → キューに追加
  4. MSG構造体をメモリに書き込み、EAX=1, EIPをリターンアドレスに設定
  5. CPU実行を再開 (emu_start)
```

### 4. ハイブリッドレンダリング (DOM + Canvas)
- ウィンドウ枠・タイトルバー・メニュー → **DOM/CSS** (ヒットテスト・ドラッグが無料)
- クライアント領域のGDI描画 → **Canvas 2D API**
- Editコントロール → **textarea** (ブラウザのテキスト入力機能を活用)

### 5. バッチ実行方式（Web Worker不要）
- `emu_start` の `count` パラメータで一定命令数(例: 10000)ごとに実行
- `setTimeout(0)` でブラウザに制御を返し、UIフリーズを防止
- SharedArrayBuffer/COOP/COEP不要でデプロイが簡単

## ディレクトリ構成

```
browser-windows-runner/
├── index.html                  # メインページ（ファイルドロップUI）
├── style.css                   # Windows Classic風スタイル
├── package.json                # esbuild ビルド設定
├── tsconfig.json               # TypeScript設定
├── src/
│   ├── app.ts                  # メインオーケストレータ
│   ├── pe/
│   │   ├── pe-parser.ts        # PE形式パーサー (DOS/NT/Section/Import/Resource)
│   │   ├── pe-loader.ts        # PEローダー (メモリマッピング + IAT構築)
│   │   └── pe-types.ts         # PE構造体の型定義
│   ├── cpu/
│   │   ├── cpu-engine.ts       # Unicorn.jsラッパー (mem_map, hooks, batch実行)
│   │   ├── cpu-types.ts        # レジスタ定数, メモリパーミッション
│   │   └── stack.ts            # stdcallスタック引数読み書きヘルパー
│   ├── win32/
│   │   ├── api-registry.ts     # stub addr → JSハンドラ中央ディスパッチ
│   │   ├── kernel32.ts         # kernel32.dll シム (~30関数)
│   │   ├── user32.ts           # user32.dll シム (~25関数)
│   │   ├── gdi32.ts            # gdi32.dll シム (~15関数)
│   │   ├── comdlg32.ts         # 開く/保存ダイアログ → HTML file picker
│   │   ├── comctl32.ts         # InitCommonControlsEx等スタブ
│   │   ├── shell32.ts          # シェルAPIスタブ
│   │   └── ntdll.ts            # 低レベルNTスタブ
│   ├── gui/
│   │   ├── window-manager.ts   # HWND→DOM管理, ウィンドウ作成/破棄
│   │   ├── message-queue.ts    # メッセージキュー + stop/resume制御
│   │   ├── gdi-canvas.ts       # GDI描画 → Canvas 2D API
│   │   ├── menu-renderer.ts    # Win32メニュー → HTMLドロップダウン
│   │   └── controls.ts         # Editコントロール, ボタン, ステータスバー
│   └── env/
│       ├── memory.ts           # アドレス空間レイアウト管理
│       ├── handles.ts          # 汎用ハンドルテーブル (HWND,HDC,HFONT等)
│       ├── strings.ts          # ANSI/Unicode文字列 ↔ JS String変換
│       └── teb-peb.ts          # TEB/PEB最小構造体セットアップ
└── lib/
    ├── unicorn-x86.js          # Unicorn.js x86 WASMビルド
    └── unicorn-x86.wasm        # WASMバイナリ
```

## メモリレイアウト

| アドレス範囲 | 用途 |
|---|---|
| `0x00010000 - 0x0001FFFF` | PEB/TEB |
| `0x00100000 - 0x001FFFFF` | スタック (1MB, ESP=0x001FFFF0から下に成長) |
| `0x00200000 - 0x002FFFFF` | ヒープ (HeapAllocバンプアロケータ) |
| `0x00300000 - 0x003FFFFF` | 文字列/データスクラッチ |
| `0x00400000+` | PE イメージ (ImageBase) |
| `0x70000000 - 0x70100000` | APIスタブ領域 (16byte間隔) |

## 実装する Win32 API (最小セット)

### kernel32.dll (~30関数)
GetModuleHandleA/W, GetCommandLineA/W, GetStartupInfoA/W, ExitProcess,
HeapCreate/Alloc/Free/ReAlloc, GetProcessHeap, VirtualAlloc/Free,
LocalAlloc/Free, GlobalAlloc/Free, GetLastError, SetLastError,
lstrlenA/W, lstrcpyA/W, MultiByteToWideChar, WideCharToMultiByte,
LoadLibraryA/W, GetProcAddress, GetVersionExA/W, GetSystemMetrics,
InitializeCriticalSection/Enter/Leave/Delete, CreateFileA/W, ReadFile,
WriteFile, CloseHandle, SetUnhandledExceptionFilter

### user32.dll (~25関数)
RegisterClassExA/W, CreateWindowExA/W, ShowWindow, UpdateWindow,
GetMessageA/W, TranslateMessage, DispatchMessageA/W, DefWindowProcA/W,
PostQuitMessage, SendMessageA/W, PostMessageA/W,
LoadIconA/W, LoadCursorA/W, LoadMenuA/W, LoadAcceleratorsA/W,
SetMenu, GetClientRect, BeginPaint, EndPaint, InvalidateRect,
MessageBoxA/W, SetWindowTextA/W, GetDC, ReleaseDC, SetFocus, LoadStringA/W

### gdi32.dll (~15関数)
CreateFontIndirectA/W, SelectObject, DeleteObject,
TextOutA/W, DrawTextA/W, GetTextMetricsA/W,
SetTextColor, SetBkColor, SetBkMode,
CreateSolidBrush, FillRect, GetStockObject,
CreateDCA/W, DeleteDC

## 段階的デモ目標

| 段階 | 成果物 | 主な作業 |
|------|--------|----------|
| **1** | PE解析ビューア | PE Parser, ファイルドロップUI |
| **2** | x86コード実行確認 | Unicorn.js統合, 手書きx86コード実行 |
| **3** | API呼出し検知デモ | PE Loader, APIスタブ, kernel32基本関数 |
| **4** | 空ウィンドウ表示 | user32 (CreateWindow), Window Manager, メッセージループ |
| **5** | メモ帳の外観再現 | メニュー, Editコントロール, GDI描画 |
| **6** | テキスト入力動作 | メッセージ処理完全実装, キーボードイベント変換 |

## 対象notepad.exe

- **Windows XP SP3版** を推奨 (PE32 i386, 最もシンプル)
- CRT初期化が比較的単純、モダンAPIへの依存が少ない
- エントリポイントは `mainCRTStartup` → CRT初期化 → `WinMain`

## 使用技術

- **TypeScript** + **esbuild** (高速バンドル)
- **Unicorn.js** (x86 WASM エミュレータ)
- **HTML5 Canvas** (GDI描画)
- **ES Modules** + バンドル出力
- 静的サイトとしてデプロイ可能 (サーバーサイド不要)

## 制限事項（PoC範囲）

- 32bit PE (PE32) のみ、64bit非対応
- FPU/SSE命令はUnicorn.jsが対応するが、API側の浮動小数点は最小限
- ファイルI/Oは仮想ファイルシステム (localStorage)
- ネットワーク・レジストリ・プロセス管理は未実装
- 実行速度はネイティブの1/100〜1/1000程度

## 検証方法

1. `npm run build` でバンドル
2. `npx serve dist/` でローカルHTTPサーバー起動
3. notepad.exe (Windows XP版) をドラッグ＆ドロップ
4. PE解析結果が画面に表示されることを確認
5. コンソールにWin32 APIコールのログが出力されることを確認
6. ウィンドウが描画され、メニュー・テキスト入力領域が表示されることを確認
