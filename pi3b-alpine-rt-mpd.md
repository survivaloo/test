# Raspberry Pi 3B+ Alpine Linux + RT カーネル + MPD 構築計画

## 概要

Pi 5 上の Claude Code を活用して、Pi 3B+ 用のオーディオ専用 OS を構築する。
Alpine Linux（超軽量）+ PREEMPT_RT カーネル（リアルタイム）+ MPD（Music Player Daemon）で、
ビットパーフェクト・低ジッターの音楽再生環境を実現する。

## ハードウェア

- **ビルド環境**: Raspberry Pi 5（Claude Code 実行）
- **ターゲット**: Raspberry Pi 3B+（BCM2837B0, Cortex-A53 1.4GHz, 1GB RAM）
- **出力**: USB DAC 接続

## 構成

```
Alpine Linux (~50MB 最小インストール)
  + linux-rt カーネル (PREEMPT_RT)
  + mpd (Music Player Daemon)
  + alsa-utils
  + 不要サービス全停止
  → USB DAC へビットパーフェクト出力
```

## なぜ Alpine Linux か

| 要素 | 説明 |
|---|---|
| 超軽量 | ~50MB、常駐プロセス最小限 → CPU/メモリの競合がほぼない |
| パッケージ管理 | `apk add mpd alsa-utils` で一発インストール |
| BusyBox ベース | 内部的に BusyBox を使っているので BusyBox の利点はそのまま |
| musl libc | glibc より軽量でシンプル |
| RT カーネル対応 | PREEMPT_RT カーネルのビルド実績あり |

※ BusyBox 単体でやる場合、MPD の依存ライブラリ（10〜15個）を全て手動クロスコンパイルする必要があり、労力に見合わない。音質差はゼロ。

## 手順

### Step 1: Pi 3B+ 用 SD カード作成

1. Alpine Linux aarch64 をダウンロード
2. SD カードに書き込み
3. Pi 3B+ で初期起動・初期設定

### Step 2: RT カーネルのビルド（Pi 5 上で実施）

1. Pi 3B+ 用の Linux カーネルソースを取得
2. PREEMPT_RT パッチを適用（Linux 6.12 以降はメインラインに統合済み）
3. `CONFIG_PREEMPT_RT=y` を設定してクロスコンパイル
4. ビルドしたカーネルを Pi 3B+ に転送・インストール

### Step 3: MPD インストール・設定

```sh
apk add mpd alsa-utils
```

`/etc/mpd.conf` の設定:
- ALSA 出力（ビットパーフェクト）
- リアルタイムスケジューリング有効化
- リサンプリング無効（ビットパーフェクト）

### Step 4: 不要サービスの無効化

Alpine の最小構成からさらに削る:
- ネットワーク（SSH + MPD クライアント接続のみ残す）
- syslog を最小に
- cron 無効化
- swap 無効化

### Step 5: チューニング

- MPD プロセスを `SCHED_FIFO` で実行（RT カーネルで本来の性能発揮）
- CPU governor を `performance` に固定
- USB DAC に対する IRQ アフィニティ設定
- 不要なカーネルモジュール無効化

## RT カーネルの効果

```
通常カーネル: 音楽データ → MPD → ALSA → DAC
              ↑ 他プロセスに割り込まれてジッター発生

RT カーネル:   音楽データ → MPD(RT優先度) → ALSA → DAC
              ↑ 割り込みなし、μs 単位で応答保証
```

## 参考リンク

- Alpine Linux: https://alpinelinux.org/
- MPD: https://www.musicpd.org/
- PREEMPT_RT: https://wiki.linuxfoundation.org/realtime/preempt_rt_versions
- Alpine RT kernel for RPi: https://github.com/alpine-digital-research/linux-rt-rpi
- MPD User Manual (RT scheduling): https://mpd.readthedocs.io/en/stable/user.html
- Bitperfect MPD + ALSA: https://www.24bit96.com/hifi-music-server/bitperfect-linux-with-mpd.html
