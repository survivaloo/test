#!/usr/bin/env python3
"""
金ETFポートフォリオ運用支援アプリ
インタラクティブにポートフォリオを管理、最適化、リバランスを実行
"""

import sys
from typing import Dict
from portfolio_manager import PortfolioManager
from portfolio_optimizer import PortfolioOptimizer


class PortfolioApp:
    """ポートフォリオ運用支援アプリケーション"""

    def __init__(self):
        # 日本市場の金ETFデータ
        self.etf_data = {
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

        self.manager = PortfolioManager(self.etf_data)
        self.optimizer = PortfolioOptimizer(self.etf_data)

    def show_menu(self):
        """メインメニューを表示"""
        print("\n" + "=" * 100)
        print("金ETFポートフォリオ運用支援アプリ")
        print("=" * 100)
        print("\n【メニュー】")
        print("  1. ETF一覧を表示")
        print("  2. 最適ポートフォリオを提案")
        print("  3. リスクプロファイル別の推奨配分")
        print("  4. 保有ポートフォリオを表示")
        print("  5. ETFを購入（追加）")
        print("  6. ETFを売却")
        print("  7. リバランス提案")
        print("  8. ポートフォリオを保存")
        print("  9. ポートフォリオを読み込み")
        print("  0. 終了")
        print()

    def show_etf_list(self):
        """ETF一覧を表示"""
        print("\n" + "=" * 100)
        print("【金ETF一覧】")
        print("=" * 100)
        print(f"{'銘柄コード':<12} {'ETF名':<50} {'現在価格':>10} {'信託報酬':>8} {'為替ヘッジ':>10}")
        print("-" * 100)

        for ticker, data in self.etf_data.items():
            print(f"{ticker:<12} {data['name']:<50} {data['current_price']:>10,.0f}円 "
                  f"{data['expense_ratio']:>7.2f}% {data['hedge']:>10}")

    def show_optimal_portfolio(self):
        """最適ポートフォリオを表示"""
        print("\n" + "=" * 100)
        print("【最適ポートフォリオ（最大シャープレシオ）】")
        print("=" * 100)

        optimal = self.optimizer.find_optimal_portfolio()

        print(f"\n期待年率リターン: {optimal['return']:.2f}%")
        print(f"年率リスク（標準偏差）: {optimal['volatility']:.2f}%")
        print(f"シャープレシオ: {optimal['sharpe']:.3f}")

        print(f"\n推奨配分:")
        print(f"{'銘柄コード':<12} {'配分比率':>10} {'ETF名':<50}")
        print("-" * 100)

        for ticker, info in sorted(optimal['allocation'].items(),
                                   key=lambda x: x[1]['weight'], reverse=True):
            print(f"{ticker:<12} {info['weight']:>9.1f}% {info['name']:<50}")

        # 投資額シミュレーション
        print("\n【100万円投資した場合の配分例】")
        print(f"{'銘柄コード':<12} {'配分比率':>10} {'投資額':>12} {'購入株数':>10}")
        print("-" * 100)

        investment = 1000000
        for ticker, info in sorted(optimal['allocation'].items(),
                                   key=lambda x: x[1]['weight'], reverse=True):
            amount = investment * (info['weight'] / 100)
            price = self.etf_data[ticker]['current_price']
            shares = int(amount / price)
            print(f"{ticker:<12} {info['weight']:>9.1f}% {amount:>12,.0f}円 {shares:>9}株")

    def show_risk_profiles(self):
        """リスクプロファイル別の推奨を表示"""
        print("\n" + "=" * 100)
        print("【リスクプロファイル別の推奨ポートフォリオ】")
        print("=" * 100)

        profiles = [
            ('保守的（低リスク重視）', 'conservative'),
            ('中庸（バランス型）', 'moderate'),
            ('積極的（高リターン重視）', 'aggressive')
        ]

        for profile_name, profile_key in profiles:
            print(f"\n■ {profile_name}")
            print("-" * 100)

            portfolio = self.optimizer.suggest_allocation_by_risk_profile(profile_key)

            print(f"期待リターン: {portfolio['return']:.2f}%  |  "
                  f"リスク: {portfolio['volatility']:.2f}%  |  "
                  f"シャープレシオ: {portfolio['sharpe']:.3f}")

            print("配分:")
            for ticker, info in sorted(portfolio['allocation'].items(),
                                       key=lambda x: x[1]['weight'], reverse=True):
                print(f"  {ticker}: {info['weight']:>5.1f}% - {info['name']}")

    def show_current_portfolio(self):
        """現在の保有ポートフォリオを表示"""
        if not self.manager.holdings:
            print("\nポートフォリオが空です。ETFを購入してください。")
            return

        print("\n" + "=" * 100)
        print("【保有ポートフォリオ】")
        print("=" * 100)

        performance = self.manager.calculate_performance()

        print(f"\n投資総額: {performance['total_cost']:,.0f}円")
        print(f"現在価値: {performance['total_value']:,.0f}円")
        print(f"評価損益: {performance['total_gain']:+,.0f}円 ({performance['total_gain_pct']:+.2f}%)")

        print(f"\n期待年率リターン: {performance['expected_annual_return']:.2f}%")
        print(f"年率リスク: {performance['annual_volatility']:.2f}%")
        print(f"シャープレシオ: {performance['sharpe_ratio']:.3f}")

        print(f"\n保有銘柄:")
        print(f"{'銘柄':<12} {'株数':>8} {'平均取得':>10} {'現在価格':>10} "
              f"{'評価額':>12} {'損益':>12} {'損益率':>8} {'配分':>6}")
        print("-" * 100)

        for holding in sorted(performance['holdings'], key=lambda x: x['value'], reverse=True):
            print(f"{holding['ticker']:<12} {holding['shares']:>8} "
                  f"{holding['avg_cost']:>10,.0f}円 {holding['current_price']:>10,.0f}円 "
                  f"{holding['value']:>12,.0f}円 {holding['gain']:>+12,.0f}円 "
                  f"{holding['gain_pct']:>+7.1f}% {holding['weight']:>5.1f}%")

    def buy_etf(self):
        """ETFを購入"""
        print("\n【ETF購入】")
        self.show_etf_list()

        ticker = input("\n購入する銘柄コード: ").strip().upper()
        if ticker not in self.etf_data:
            print("無効な銘柄コードです。")
            return

        try:
            shares = int(input("購入株数: "))
            price = float(input(f"購入価格（現在価格: {self.etf_data[ticker]['current_price']}円）: "))

            self.manager.add_holding(ticker, shares, price)
            print(f"\n{ticker} を {shares}株、{price:,.0f}円で購入しました。")
            print(f"合計: {shares * price:,.0f}円")

        except ValueError:
            print("無効な入力です。")

    def sell_etf(self):
        """ETFを売却"""
        if not self.manager.holdings:
            print("\n保有銘柄がありません。")
            return

        print("\n【ETF売却】")
        self.show_current_portfolio()

        ticker = input("\n売却する銘柄コード: ").strip().upper()
        if ticker not in self.manager.holdings:
            print("この銘柄は保有していません。")
            return

        max_shares = self.manager.holdings[ticker]['shares']
        print(f"保有株数: {max_shares}株")

        try:
            shares = int(input("売却株数: "))
            if shares > max_shares:
                print("保有株数を超えています。")
                return

            price = float(input(f"売却価格（現在価格: {self.etf_data[ticker]['current_price']}円）: "))

            self.manager.remove_holding(ticker, shares, price)
            print(f"\n{ticker} を {shares}株、{price:,.0f}円で売却しました。")
            print(f"合計: {shares * price:,.0f}円")

        except ValueError:
            print("無効な入力です。")

    def show_rebalancing(self):
        """リバランス提案を表示"""
        if not self.manager.holdings:
            print("\nポートフォリオが空です。")
            return

        print("\n【リバランス提案】")
        print("目標とするリスクプロファイルを選択してください:")
        print("  1. 保守的（低リスク重視）")
        print("  2. 中庸（バランス型）")
        print("  3. 積極的（高リターン重視）")

        choice = input("\n選択 (1-3): ").strip()

        profile_map = {'1': 'conservative', '2': 'moderate', '3': 'aggressive'}
        profile = profile_map.get(choice, 'aggressive')

        print("\n" + "=" * 100)
        rebalancing = self.manager.suggest_rebalancing(profile)

        target = rebalancing['target_portfolio']
        print(f"目標ポートフォリオ:")
        print(f"  期待リターン: {target['return']:.2f}%")
        print(f"  リスク: {target['volatility']:.2f}%")
        print(f"  シャープレシオ: {target['sharpe']:.3f}")

        print(f"\n目標配分:")
        for ticker, info in sorted(target['allocation'].items(),
                                   key=lambda x: x[1]['weight'], reverse=True):
            print(f"  {ticker}: {info['weight']:.1f}%")

        if rebalancing['trades']:
            print(f"\n推奨取引（ポートフォリオ総額: {rebalancing['current_value']:,.0f}円）:")
            print(f"{'銘柄':<12} {'売買':>6} {'株数':>8} {'金額':>12} {'現在配分':>10} {'目標配分':>10}")
            print("-" * 80)

            for ticker, trade in sorted(rebalancing['trades'].items(),
                                       key=lambda x: x[1]['value'], reverse=True):
                action_jp = '買付' if trade['action'] == 'buy' else '売却'
                print(f"{ticker:<12} {action_jp:>6} {trade['shares']:>8}株 "
                      f"{trade['value']:>12,.0f}円 {trade['current_weight']:>9.1f}% "
                      f"{trade['target_weight']:>9.1f}%")
        else:
            print("\nリバランスは不要です。現在の配分が目標に近い状態です。")

    def run(self):
        """アプリケーションを実行"""
        while True:
            self.show_menu()
            choice = input("選択してください (0-9): ").strip()

            if choice == '0':
                print("\nアプリケーションを終了します。")
                break
            elif choice == '1':
                self.show_etf_list()
            elif choice == '2':
                self.show_optimal_portfolio()
            elif choice == '3':
                self.show_risk_profiles()
            elif choice == '4':
                self.show_current_portfolio()
            elif choice == '5':
                self.buy_etf()
            elif choice == '6':
                self.sell_etf()
            elif choice == '7':
                self.show_rebalancing()
            elif choice == '8':
                filename = input("\n保存ファイル名 (デフォルト: my_portfolio.json): ").strip()
                if not filename:
                    filename = 'my_portfolio.json'
                self.manager.save_portfolio(filename)
                print(f"\nポートフォリオを {filename} に保存しました。")
            elif choice == '9':
                filename = input("\n読み込むファイル名 (デフォルト: my_portfolio.json): ").strip()
                if not filename:
                    filename = 'my_portfolio.json'
                if self.manager.load_portfolio(filename):
                    print(f"\nポートフォリオを {filename} から読み込みました。")
                else:
                    print(f"\nファイル {filename} が見つかりません。")
            else:
                print("\n無効な選択です。")

            input("\nEnterキーを押して続行...")


def main():
    """メイン関数"""
    app = PortfolioApp()

    # デモモードかインタラクティブモードか選択
    if len(sys.argv) > 1 and sys.argv[1] == '--demo':
        # デモモード：自動で全機能を表示
        print("デモモードで実行します...\n")
        app.show_etf_list()
        input("\nEnterキーで次へ...")
        app.show_optimal_portfolio()
        input("\nEnterキーで次へ...")
        app.show_risk_profiles()
    else:
        # インタラクティブモード
        app.run()


if __name__ == "__main__":
    main()
