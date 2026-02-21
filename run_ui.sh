#!/bin/bash
# 金ETFポートフォリオ運用支援アプリ - UIサーバー起動スクリプト
#
# スマホ・タブレットからアクセスするには：
# 1. このスクリプトを実行: ./run_ui.sh
# 2. 表示されたネットワークURLをスマホのブラウザで開く

echo "================================================"
echo "金ETFポートフォリオ運用支援アプリ - Web UI"
echo "================================================"
echo ""

# Streamlitがインストールされているか確認
if ! command -v streamlit &> /dev/null; then
    echo "⚠️  Streamlitがインストールされていません。"
    echo ""
    echo "インストールコマンド:"
    echo "  pip install streamlit"
    echo ""
    echo "または"
    echo "  pip install -r requirements.txt"
    echo ""
    exit 1
fi

echo "🚀 サーバーを起動しています..."
echo ""
echo "📱 スマホ・タブレットからアクセスするには："
echo "   ブラウザで「Network URL」をコピーして開いてください"
echo ""
echo "🖥️  このPCからアクセスするには："
echo "   ブラウザで「Local URL」を開いてください"
echo ""
echo "================================================"
echo ""

# Streamlitサーバーを起動（ネットワークアクセス許可）
streamlit run portfolio_ui.py \
    --server.address 0.0.0.0 \
    --server.port 8501 \
    --browser.gatherUsageStats false
