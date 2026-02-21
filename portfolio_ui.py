#!/usr/bin/env python3
"""
金ETFポートフォリオ運用支援アプリ - Web UI
Streamlitベースのインタラクティブダッシュボード
"""

try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    print("Streamlitがインストールされていません。")
    print("インストール: pip install streamlit")
    import sys
    sys.exit(1)

from portfolio_optimizer import PortfolioOptimizer
from portfolio_manager import PortfolioManager
import json
from datetime import datetime


# ETFデータ
ETF_DATA = {
    '424A.T': {
        'name': 'グローバルX ゴールド ETF（為替ヘッジあり）',
        'annual_return': 8.5,
        'annual_volatility': 14.1,
        'expense_ratio': 0.1775,
        'current_price': 5120,
        'hedge': 'あり'
    },
    '2840.T': {
        'name': 'iシェアーズ ゴールドインデックス・ファンド（為替ヘッジあり）',
        'annual_return': 8.3,
        'annual_volatility': 14.2,
        'expense_ratio': 0.13,
        'current_price': 18500,
        'hedge': 'あり'
    },
    '314A.T': {
        'name': 'iシェアーズ ゴールドETF',
        'annual_return': 27.8,
        'annual_volatility': 16.4,
        'expense_ratio': 0.22,
        'current_price': 4850,
        'hedge': 'なし'
    },
    '425A.T': {
        'name': 'グローバルX ゴールド ETF',
        'annual_return': 28.2,
        'annual_volatility': 16.4,
        'expense_ratio': 0.1775,
        'current_price': 5085,
        'hedge': 'なし'
    },
    '447A.T': {
        'name': 'ステート・ストリート・スパイダーゴールドETF',
        'annual_return': 27.6,
        'annual_volatility': 16.5,
        'expense_ratio': 0.18,
        'current_price': 4920,
        'hedge': 'なし'
    },
    '1540.T': {
        'name': '純金上場信託（金の果実）',
        'annual_return': 27.5,
        'annual_volatility': 16.5,
        'expense_ratio': 0.44,
        'current_price': 6950,
        'hedge': 'なし'
    },
    '1328.T': {
        'name': 'ishares Gold Trust',
        'annual_return': 27.3,
        'annual_volatility': 16.6,
        'expense_ratio': 0.25,
        'current_price': 3280,
        'hedge': 'なし'
    },
}


def init_session_state():
    """セッション状態を初期化"""
    if 'manager' not in st.session_state:
        st.session_state.manager = PortfolioManager(ETF_DATA)
    if 'optimizer' not in st.session_state:
        st.session_state.optimizer = PortfolioOptimizer(ETF_DATA)


def show_etf_list():
    """ETF一覧を表示"""
    st.header("📊 金ETF一覧")

    # データフレーム形式で表示
    etf_list = []
    for ticker, data in ETF_DATA.items():
        etf_list.append({
            '銘柄コード': ticker,
            'ETF名': data['name'],
            '現在価格': f"¥{data['current_price']:,}",
            '年率リターン': f"{data['annual_return']:.1f}%",
            '年率リスク': f"{data['annual_volatility']:.1f}%",
            '信託報酬': f"{data['expense_ratio']:.2f}%",
            '為替ヘッジ': data['hedge']
        })

    st.dataframe(etf_list, use_container_width=True, hide_index=True)


def show_optimal_portfolio():
    """最適ポートフォリオを表示"""
    st.header("🎯 最適ポートフォリオ提案")

    # 最適化タイプ選択
    optimization_type = st.radio(
        "最適化目標",
        ["最大シャープレシオ（推奨）", "最小リスク"],
        horizontal=True
    )

    if optimization_type == "最大シャープレシオ（推奨）":
        optimal = st.session_state.optimizer.find_optimal_portfolio()
    else:
        optimal = st.session_state.optimizer.find_optimal_portfolio(min_volatility=True)

    # メトリクス表示
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("期待年率リターン", f"{optimal['return']:.2f}%")
    with col2:
        st.metric("年率リスク", f"{optimal['volatility']:.2f}%")
    with col3:
        st.metric("シャープレシオ", f"{optimal['sharpe']:.3f}")

    # 配分表示
    st.subheader("推奨配分")
    allocation_data = []
    for ticker, info in sorted(optimal['allocation'].items(),
                               key=lambda x: x[1]['weight'], reverse=True):
        allocation_data.append({
            '銘柄': ticker,
            'ETF名': info['name'],
            '配分比率': f"{info['weight']:.1f}%",
            '配分（数値）': info['weight']
        })

    st.dataframe(allocation_data[:-1] if allocation_data else [],
                 use_container_width=True, hide_index=True,
                 column_config={
                     '配分（数値）': st.column_config.ProgressColumn(
                         "配分",
                         format="%.1f%%",
                         min_value=0,
                         max_value=100,
                     )
                 })

    # 投資額シミュレーション
    st.subheader("投資額シミュレーション")
    investment = st.number_input(
        "投資金額（円）",
        min_value=100000,
        max_value=100000000,
        value=1000000,
        step=100000
    )

    sim_data = []
    for ticker, info in sorted(optimal['allocation'].items(),
                               key=lambda x: x[1]['weight'], reverse=True):
        amount = investment * (info['weight'] / 100)
        price = ETF_DATA[ticker]['current_price']
        shares = int(amount / price)
        actual_amount = shares * price

        sim_data.append({
            '銘柄': ticker,
            '配分比率': f"{info['weight']:.1f}%",
            '投資額': f"¥{int(amount):,}",
            '購入株数': shares,
            '実際の投資額': f"¥{actual_amount:,}"
        })

    st.dataframe(sim_data, use_container_width=True, hide_index=True)


def show_risk_profiles():
    """リスクプロファイル別推奨"""
    st.header("🎭 リスクプロファイル別推奨")

    profile = st.selectbox(
        "リスクプロファイルを選択",
        ["保守的（低リスク重視）", "中庸（バランス型）", "積極的（高リターン重視）"]
    )

    profile_map = {
        "保守的（低リスク重視）": 'conservative',
        "中庸（バランス型）": 'moderate',
        "積極的（高リターン重視）": 'aggressive'
    }

    portfolio = st.session_state.optimizer.suggest_allocation_by_risk_profile(
        profile_map[profile]
    )

    # メトリクス
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("期待リターン", f"{portfolio['return']:.2f}%")
    with col2:
        st.metric("リスク", f"{portfolio['volatility']:.2f}%")
    with col3:
        st.metric("シャープレシオ", f"{portfolio['sharpe']:.3f}")

    # 配分
    st.subheader("推奨配分")
    allocation_data = []
    for ticker, info in sorted(portfolio['allocation'].items(),
                               key=lambda x: x[1]['weight'], reverse=True):
        allocation_data.append({
            '銘柄': ticker,
            'ETF名': info['name'],
            '配分比率': f"{info['weight']:.1f}%"
        })

    st.dataframe(allocation_data, use_container_width=True, hide_index=True)


def show_portfolio_management():
    """ポートフォリオ管理"""
    st.header("💼 保有ポートフォリオ管理")

    # タブで機能を分ける
    tab1, tab2, tab3 = st.tabs(["保有状況", "売買", "リバランス"])

    with tab1:
        if not st.session_state.manager.holdings:
            st.info("保有銘柄がありません。「売買」タブからETFを購入してください。")
        else:
            performance = st.session_state.manager.calculate_performance()

            # サマリーメトリクス
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("投資総額", f"¥{performance['total_cost']:,.0f}")
            with col2:
                st.metric("現在価値", f"¥{performance['total_value']:,.0f}")
            with col3:
                st.metric("評価損益",
                         f"¥{performance['total_gain']:,.0f}",
                         f"{performance['total_gain_pct']:.2f}%")
            with col4:
                st.metric("シャープレシオ", f"{performance['sharpe_ratio']:.3f}")

            # 保有銘柄詳細
            st.subheader("保有銘柄詳細")
            holdings_data = []
            for h in sorted(performance['holdings'], key=lambda x: x['value'], reverse=True):
                holdings_data.append({
                    '銘柄': h['ticker'],
                    '保有株数': h['shares'],
                    '平均取得': f"¥{h['avg_cost']:,.0f}",
                    '現在価格': f"¥{h['current_price']:,.0f}",
                    '評価額': f"¥{h['value']:,.0f}",
                    '損益': f"¥{h['gain']:+,.0f}",
                    '損益率': f"{h['gain_pct']:+.1f}%",
                    '配分': f"{h['weight']:.1f}%"
                })

            st.dataframe(holdings_data, use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("ETF売買")

        action = st.radio("操作", ["購入", "売却"], horizontal=True)

        if action == "購入":
            ticker = st.selectbox("銘柄", list(ETF_DATA.keys()),
                                 format_func=lambda x: f"{x} - {ETF_DATA[x]['name']}")

            current_price = ETF_DATA[ticker]['current_price']
            st.info(f"現在価格: ¥{current_price:,}")

            shares = st.number_input("購入株数", min_value=1, value=10, step=1)
            price = st.number_input("購入価格",
                                   min_value=1.0,
                                   value=float(current_price),
                                   step=10.0)

            if st.button("購入実行", type="primary"):
                st.session_state.manager.add_holding(ticker, shares, price)
                st.success(f"{ticker} を {shares}株、¥{price:,.0f}円で購入しました。合計: ¥{shares * price:,.0f}")
                st.rerun()

        else:  # 売却
            if not st.session_state.manager.holdings:
                st.warning("保有銘柄がありません。")
            else:
                ticker = st.selectbox("銘柄",
                                     list(st.session_state.manager.holdings.keys()),
                                     format_func=lambda x: f"{x} - {ETF_DATA[x]['name']}")

                max_shares = st.session_state.manager.holdings[ticker]['shares']
                current_price = ETF_DATA[ticker]['current_price']

                st.info(f"保有株数: {max_shares}株 | 現在価格: ¥{current_price:,}")

                shares = st.number_input("売却株数", min_value=1, max_value=max_shares, value=1)
                price = st.number_input("売却価格",
                                       min_value=1.0,
                                       value=float(current_price),
                                       step=10.0)

                if st.button("売却実行", type="primary"):
                    st.session_state.manager.remove_holding(ticker, shares, price)
                    st.success(f"{ticker} を {shares}株、¥{price:,.0f}円で売却しました。合計: ¥{shares * price:,.0f}")
                    st.rerun()

    with tab3:
        if not st.session_state.manager.holdings:
            st.warning("保有銘柄がありません。")
        else:
            st.subheader("リバランス提案")

            profile = st.selectbox(
                "目標リスクプロファイル",
                ["保守的", "中庸", "積極的"],
                index=2
            )

            profile_map = {"保守的": "conservative", "中庸": "moderate", "積極的": "aggressive"}

            rebalancing = st.session_state.manager.suggest_rebalancing(
                profile_map[profile]
            )

            target = rebalancing['target_portfolio']

            # 目標ポートフォリオ
            st.write("**目標ポートフォリオ:**")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("期待リターン", f"{target['return']:.2f}%")
            with col2:
                st.metric("リスク", f"{target['volatility']:.2f}%")
            with col3:
                st.metric("シャープレシオ", f"{target['sharpe']:.3f}")

            # 推奨取引
            if rebalancing['trades']:
                st.subheader("推奨取引")
                trades_data = []
                for ticker, trade in sorted(rebalancing['trades'].items(),
                                          key=lambda x: x[1]['value'], reverse=True):
                    action_jp = '買付' if trade['action'] == 'buy' else '売却'
                    trades_data.append({
                        '銘柄': ticker,
                        '売買': action_jp,
                        '株数': trade['shares'],
                        '金額': f"¥{trade['value']:,.0f}",
                        '現在配分': f"{trade['current_weight']:.1f}%",
                        '目標配分': f"{trade['target_weight']:.1f}%"
                    })

                st.dataframe(trades_data, use_container_width=True, hide_index=True)
            else:
                st.success("リバランスは不要です。現在の配分が目標に近い状態です。")


def show_comparison():
    """ETF比較"""
    st.header("📈 ETF比較")

    selected_etfs = st.multiselect(
        "比較するETFを選択（2〜7銘柄）",
        list(ETF_DATA.keys()),
        default=['425A.T', '424A.T', '314A.T'],
        format_func=lambda x: f"{x} - {ETF_DATA[x]['name']}"
    )

    if len(selected_etfs) < 2:
        st.warning("2銘柄以上選択してください。")
    else:
        # 比較表
        comparison_data = []
        for ticker in selected_etfs:
            data = ETF_DATA[ticker]
            comparison_data.append({
                '銘柄': ticker,
                'ETF名': data['name'][:30] + '...' if len(data['name']) > 30 else data['name'],
                '現在価格': f"¥{data['current_price']:,}",
                'リターン': f"{data['annual_return']:.1f}%",
                'リスク': f"{data['annual_volatility']:.1f}%",
                '信託報酬': f"{data['expense_ratio']:.2f}%",
                'ヘッジ': data['hedge']
            })

        st.dataframe(comparison_data, use_container_width=True, hide_index=True)

        # シャープレシオ計算
        st.subheader("シャープレシオ比較")
        sharpe_data = []
        for ticker in selected_etfs:
            data = ETF_DATA[ticker]
            risk_free_rate = 0.5
            sharpe = (data['annual_return'] - data['expense_ratio'] - risk_free_rate) / data['annual_volatility']
            sharpe_data.append({
                '銘柄': ticker,
                'シャープレシオ': f"{sharpe:.3f}",
                '評価': '優秀' if sharpe > 1.5 else '良好' if sharpe > 1.0 else '普通'
            })

        # シャープレシオでソート
        sharpe_data.sort(key=lambda x: float(x['シャープレシオ']), reverse=True)
        st.dataframe(sharpe_data, use_container_width=True, hide_index=True)


def main():
    """メイン関数"""
    st.set_page_config(
        page_title="金ETFポートフォリオ運用支援",
        page_icon="💰",
        layout="wide"
    )

    st.title("💰 金ETFポートフォリオ運用支援アプリ")
    st.markdown("---")

    # セッション初期化
    init_session_state()

    # サイドバーでメニュー選択
    with st.sidebar:
        st.header("メニュー")
        menu = st.radio(
            "機能を選択",
            ["🏠 ホーム", "📊 ETF一覧", "🎯 最適ポートフォリオ",
             "🎭 リスクプロファイル", "💼 ポートフォリオ管理", "📈 ETF比較"],
            label_visibility="collapsed"
        )

        st.markdown("---")

        # データ管理
        st.subheader("データ管理")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 保存", use_container_width=True):
                st.session_state.manager.save_portfolio('portfolio.json')
                st.success("保存完了")

        with col2:
            if st.button("📂 読込", use_container_width=True):
                if st.session_state.manager.load_portfolio('portfolio.json'):
                    st.success("読込完了")
                    st.rerun()
                else:
                    st.error("ファイルなし")

    # メインコンテンツ
    if menu == "🏠 ホーム":
        st.header("ようこそ！")
        st.markdown("""
        このアプリは、日本市場の金ETFを分析し、最適なポートフォリオを提案します。

        ### 主な機能

        - **📊 ETF一覧**: 取り扱い銘柄の一覧と詳細
        - **🎯 最適ポートフォリオ**: 最大シャープレシオまたは最小リスクのポートフォリオを提案
        - **🎭 リスクプロファイル**: 保守的・中庸・積極的なプロファイル別の推奨配分
        - **💼 ポートフォリオ管理**: 保有銘柄の管理、売買、リバランス提案
        - **📈 ETF比較**: 複数のETFを比較

        左のメニューから機能を選択してください。
        """)

        # クイックスタット
        st.subheader("📊 クイック統計")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("取扱ETF数", f"{len(ETF_DATA)}銘柄")

        with col2:
            if st.session_state.manager.holdings:
                st.metric("保有銘柄数", f"{len(st.session_state.manager.holdings)}銘柄")
            else:
                st.metric("保有銘柄数", "0銘柄")

        with col3:
            if st.session_state.manager.holdings:
                total_value = st.session_state.manager.get_current_value()
                st.metric("ポートフォリオ総額", f"¥{total_value:,.0f}")
            else:
                st.metric("ポートフォリオ総額", "¥0")

    elif menu == "📊 ETF一覧":
        show_etf_list()

    elif menu == "🎯 最適ポートフォリオ":
        show_optimal_portfolio()

    elif menu == "🎭 リスクプロファイル":
        show_risk_profiles()

    elif menu == "💼 ポートフォリオ管理":
        show_portfolio_management()

    elif menu == "📈 ETF比較":
        show_comparison()


if __name__ == "__main__":
    main()
