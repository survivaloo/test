# Docker Desktop + WSL2 ネットワーク技術解説

## 全体アーキテクチャ図

```
┌─────────────────────────────────────────────────────────────────────┐
│  Windows Host  (192.168.1.85)                                       │
│  LAN: 192.168.1.0/24                                                │
│                                                                     │
│  ┌──────────────┐  ┌──────────────────────────────────────────────┐ │
│  │  LM Studio   │  │  Hyper-V 仮想マシン                          │ │
│  │  :1234       │  │                                              │ │
│  │  (Windows    │  │  ┌────────────────────────────────────────┐  │ │
│  │   ネイティブ) │  │  │  WSL2 - Ubuntu (172.26.107.133)       │  │ │
│  └──────┬───────┘  │  │  eth0: 172.26.107.133/20               │  │ │
│         │          │  │  GW: 172.26.96.1                       │  │ │
│         │          │  │  DNS: Tailscale (100.100.100.100)      │  │ │
│         │          │  │                                        │  │ │
│         │          │  │  ┌──────────────────┐                  │  │ │
│         │          │  │  │ GLM-OCR Server   │                  │  │ │
│         │          │  │  │ :9000            │                  │  │ │
│         │          │  │  └──────────────────┘                  │  │ │
│         │          │  └────────────────────────────────────────┘  │ │
│         │          │                                              │ │
│         │          │  ┌────────────────────────────────────────┐  │ │
│         │          │  │  WSL2 - docker-desktop (Docker Engine) │  │ │
│         │          │  │  192.168.65.0/24 (内部ネットワーク)     │  │ │
│         │          │  │                                        │  │ │
│         │          │  │   openwebui_default (172.18.0.0/16)    │  │ │
│         │          │  │  ┌────────────┐  ┌────────────┐       │  │ │
│         │          │  │  │ openwebui  │  │ searxng     │       │  │ │
│         │          │  │  │ 172.18.0.3 │←→│ 172.18.0.2 │       │  │ │
│         │          │  │  │ :8080      │  │ :8080→:8888│       │  │ │
│         │          │  │  └────────────┘  └────────────┘       │  │ │
│         │          │  │                                        │  │ │
│         │          │  │   notebooklm_default (172.19.0.0/16)   │  │ │
│         │          │  │  ┌─────────────────────────┐           │  │ │
│         │          │  │  │ notebooklm              │           │  │ │
│         │          │  │  │ 172.19.0.2              │           │  │ │
│         │          │  │  │ :8502, :5055, :8000     │           │  │ │
│         │          │  │  └─────────────────────────┘           │  │ │
│         │          │  │                                        │  │ │
│         │          │  │  host.docker.internal → 192.168.65.254 │  │ │
│         │          │  │  DNS: 127.0.0.11 (Docker内蔵)          │  │ │
│         │          │  └────────────────────────────────────────┘  │ │
│         │          └──────────────────────────────────────────────┘ │
└─────────┴───────────────────────────────────────────────────────────┘
```

---

## レイヤー解説

### Layer 1: Windows Host

- **物理マシン**。LAN IP は `192.168.1.85`
- LM Studio などの Windows ネイティブアプリはここで動作
- Hyper-V ハイパーバイザーで WSL2 の仮想マシンを管理

### Layer 2: Hyper-V 仮想ネットワーク

- WSL2 は Hyper-V の**軽量 VM** として動作（通常の VM より高速）
- Windows と WSL2 の間に仮想スイッチが存在
- WSL2 の IP（`172.26.107.133`）は起動ごとに変わる可能性あり
- デフォルトゲートウェイ `172.26.96.1` が Windows 側への出口

### Layer 3: WSL2 ディストリビューション

実は **3つの WSL2 ディストロ** が動いている：

| ディストロ | 役割 |
|---|---|
| **Ubuntu** | ユーザーが使う Linux 環境。Claude Code や GLM-OCR はここで動作 |
| **docker-desktop** | Docker Engine 本体が動く専用ディストロ |
| **docker-desktop-data** | Docker のイメージ・ボリュームデータを格納 |

### Layer 4: Docker 仮想ネットワーク

Docker Engine が作る仮想ブリッジネットワーク：

| ネットワーク | サブネット | コンテナ |
|---|---|---|
| bridge（デフォルト） | 172.17.0.0/16 | 個別に `docker run` したコンテナ |
| openwebui_default | 172.18.0.0/16 | openwebui (172.18.0.3), searxng (172.18.0.2) |
| notebooklm_default | 172.19.0.0/16 | notebooklm (172.19.0.2) |

---

## 通信経路の詳細

### パターン 1: コンテナ → 同じ Compose 内のコンテナ

```
openwebui → searxng
  http://searxng:8080
```

- 同じ Docker Compose ファイル内のコンテナは同じネットワーク（`openwebui_default`）に接続
- Docker の **内蔵 DNS**（`127.0.0.11`）がコンテナ名 → IP を解決
- `searxng` という名前で `172.18.0.2` に直接到達
- **最も高速・安定**

### パターン 2: コンテナ → Windows ホスト（LM Studio など）

```
openwebui → LM Studio
  http://192.168.1.85:1234     ← LAN IP 直指定
  http://host.docker.internal:1234  ← Docker が提供する特殊ホスト名
```

**192.168.1.85 の経路:**
```
コンテナ (172.18.0.3)
  → Docker ゲートウェイ (172.18.0.1)
  → Docker Engine の NAT
  → Hyper-V 仮想スイッチ
  → Windows (192.168.1.85)
  → LM Studio (:1234)
```

**host.docker.internal の経路:**
```
コンテナ (172.18.0.3)
  → Docker 内蔵 DNS が 192.168.65.254 に解決
  → Docker Desktop の内部プロキシ
  → Windows ホスト
  → LM Studio (:1234)
```

| 方法 | メリット | デメリット |
|---|---|---|
| `192.168.1.85` (LAN IP) | シンプル | IP 変更時に修正必要 |
| `host.docker.internal` | IP 変更に強い | Docker Desktop 専用（他環境では使えない） |

### パターン 3: WSL2 → コンテナ

```
WSL2 Ubuntu → openwebui
  http://localhost:8080
```

- Docker Desktop が WSL2 側に `localhost` のポートフォワーディングを設定
- コンテナの `-p 8080:8080` がこれに対応

### パターン 4: Windows ブラウザ → コンテナ

```
Windows Chrome → openwebui
  http://localhost:8080
```

- Docker Desktop が Windows 側にも `localhost` をフォワード
- WSL2 の vEthernet アダプタ経由でコンテナに到達

### パターン 5: LAN 内の他デバイス → コンテナ

```
スマホ/他PC → openwebui
  http://192.168.1.85:8080
```

- **デフォルトでは繋がらない場合がある**
- Windows のファイアウォールとポートフォワーディング設定が必要:

```powershell
# 管理者 PowerShell で実行
netsh interface portproxy add v4tov4 listenport=8080 listenaddress=0.0.0.0 connectport=8080 connectaddress=<WSL2_IP>
netsh advfirewall firewall add rule name="WSL2 Port 8080" dir=in action=allow protocol=TCP localport=8080
```

---

## DNS の流れ

```
コンテナ内
  → 127.0.0.11 (Docker 内蔵 DNS)
    ├── コンテナ名 (searxng, openwebui) → Docker ネットワーク内 IP
    ├── host.docker.internal → 192.168.65.254 (Docker Desktop プロキシ)
    └── 外部ドメイン → ホストの DNS に転送
                       → WSL2 の DNS (Tailscale: 100.100.100.100)
                         → 最終的にインターネットへ
```

---

## ボリュームとファイルシステム

### bind mount が壊れる理由

```
Windows NTFS (/mnt/c/...)
  ↕ 9P プロトコル（Plan 9 由来のファイル共有）
WSL2 Ubuntu の ext4 (/home/...)
  ↕ grpcfuse / bind mount
Docker Desktop VM (docker-desktop-data ディストロ)
  ↕ overlay2
コンテナ内ファイルシステム
```

- bind mount（`./data:/app/data`）はこの全レイヤーを通過する
- Docker Desktop の再起動でマウントが切れることがある
- SQLite のファイルロック（flock/fcntl）が正しく伝搬しない場合がある

### Named Volume が安定な理由

```
Docker Desktop VM 内のストレージ (/var/lib/docker/volumes/...)
  ↕ overlay2（直接アクセス）
コンテナ内ファイルシステム
```

- Docker Engine と同じディスク上にあるのでレイヤーが少ない
- ファイルロックも正常に動作
- `docker volume rm` しない限りデータは消えない

---

## 現在の構成サマリ

### サービス一覧

| サービス | ポート | データ保存 | 起動方法 |
|---|---|---|---|
| Open WebUI | :8080 | `openwebui-data` (Named Volume) | `docker compose up -d` |
| SearXNG | :8888 | `searxng-config`, `searxng-cache` (Named Volume) | 同上（OpenWebUI と同じ compose） |
| NotebookLM | :8502, :5055, :8000 | `notebook-data`, `notebook-surreal` (Named Volume) | `docker compose up -d` |
| LM Studio | :1234 | Windows ローカル | Windows GUI |
| GLM-OCR | :9000 | WSL2 ローカル | `./run.sh` |

### Docker Compose ファイル

```
/home/survivaloo/projects/OpenWebUI/docker-compose.yml
  → openwebui + searxng

/home/survivaloo/projects/NotebookLM/docker-compose.yml
  → notebooklm (open_notebook + SurrealDB)
```

### Named Volume 一覧

| Volume 名 | 用途 | external |
|---|---|---|
| openwebui-data | Open WebUI のDB・設定 | Yes |
| searxng-config | SearXNG の settings.yml | Yes |
| searxng-cache | SearXNG のキャッシュ | Yes |
| notebook-data | NotebookLM のデータ | Yes |
| notebook-surreal | SurrealDB のデータ | Yes |

### IP アドレス一覧

| 対象 | IP | 備考 |
|---|---|---|
| Windows Host (LAN) | 192.168.1.85 | LM Studio が稼働 |
| WSL2 Ubuntu | 172.26.107.133 | 起動ごとに変わる可能性あり |
| WSL2 Default GW | 172.26.96.1 | Windows 側への出口 |
| Docker bridge | 172.17.0.0/16 | デフォルトネットワーク |
| openwebui_default | 172.18.0.0/16 | openwebui + searxng |
| notebooklm_default | 172.19.0.0/16 | notebooklm |
| host.docker.internal | 192.168.65.254 | コンテナから Windows への特殊ホスト名 |
| Docker 内蔵 DNS | 127.0.0.11 | コンテナ内の名前解決 |
| Tailscale DNS | 100.100.100.100 | WSL2 の外部 DNS |

---

## トラブルシューティング

### コンテナから LM Studio に繋がらない

1. LM Studio のサーバーが起動しているか確認（Server トグル ON）
2. Listen address が `0.0.0.0` になっているか確認（`127.0.0.1` だと外部不可）
3. `docker exec openwebui curl http://192.168.1.85:1234/v1/models` で確認

### データが消えた

1. `docker volume ls` で Named Volume が存在するか確認
2. コンテナ内でファイルサイズを確認（ホストと一致するか）
3. bind mount を使っている場合は Named Volume に移行を推奨

### LAN から WSL2 のサービスにアクセスできない

Windows の管理者 PowerShell で:
```powershell
# WSL2 IP を確認
wsl hostname -I

# ポートフォワーディング追加
netsh interface portproxy add v4tov4 listenport=PORT listenaddress=0.0.0.0 connectport=PORT connectaddress=WSL2_IP

# ファイアウォールルール追加
netsh advfirewall firewall add rule name="WSL2 Port PORT" dir=in action=allow protocol=TCP localport=PORT
```
