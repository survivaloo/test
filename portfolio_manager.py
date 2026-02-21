#!/usr/bin/env python3
"""
金ETFポートフォリオマネージャー
保有状況の管理、パフォーマンス追跡、リバランス提案を行う
"""

import json
from typing import Dict, List
from datetime import datetime
from portfolio_optimizer import PortfolioOptimizer


class PortfolioManager:
    """ポートフォリオの保有状況を管理するクラス"""

    def __init__(self, etf_data: Dict[str, Dict]):
        """
        Args:
            etf_data: ETFのデータ辞書
        """
        self.etf_data = etf_data
        self.optimizer = PortfolioOptimizer(etf_data)
        self.holdings = {}  # {ticker: {'shares': int, 'avg_cost': float}}
        self.transactions = []  # 取引履歴

    def add_holding(self, ticker: str, shares: int, price: float):
        """保有を追加"""
        if ticker not in self.etf_data:
            raise ValueError(f"Unknown ticker: {ticker}")

        if ticker in self.holdings:
            # 平均取得価格を計算
            current_shares = self.holdings[ticker]['shares']
            current_avg = self.holdings[ticker]['avg_cost']
            total_cost = (current_shares * current_avg) + (shares * price)
            new_shares = current_shares + shares
            new_avg = total_cost / new_shares

            self.holdings[ticker]['shares'] = new_shares
            self.holdings[ticker]['avg_cost'] = new_avg
        else:
            self.holdings[ticker] = {
                'shares': shares,
                'avg_cost': price
            }

        # 取引履歴を記録
        self.transactions.append({
            'date': datetime.now().isoformat(),
            'ticker': ticker,
            'action': 'buy',
            'shares': shares,
            'price': price,
            'total': shares * price
        })

    def remove_holding(self, ticker: str, shares: int, price: float):
        """保有を減らす（売却）"""
        if ticker not in self.holdings:
            raise ValueError(f"No holdings for {ticker}")

        if self.holdings[ticker]['shares'] < shares:
            raise ValueError(f"Insufficient shares for {ticker}")

        self.holdings[ticker]['shares'] -= shares

        if self.holdings[ticker]['shares'] == 0:
            del self.holdings[ticker]

        # 取引履歴を記録
        self.transactions.append({
            'date': datetime.now().isoformat(),
            'ticker': ticker,
            'action': 'sell',
            'shares': shares,
            'price': price,
            'total': shares * price
        })

    def get_current_value(self) -> float:
        """現在のポートフォリオ総額を計算"""
        total = 0
        for ticker, holding in self.holdings.items():
            current_price = self.etf_data[ticker]['current_price']
            total += holding['shares'] * current_price
        return total

    def get_current_allocation(self) -> Dict[str, float]:
        """現在の配分比率を取得"""
        total_value = self.get_current_value()
        if total_value == 0:
            return {}

        allocation = {}
        for ticker, holding in self.holdings.items():
            current_price = self.etf_data[ticker]['current_price']
            value = holding['shares'] * current_price
            allocation[ticker] = value / total_value

        return allocation

    def calculate_performance(self) -> Dict:
        """ポートフォリオのパフォーマンスを計算"""
        total_cost = 0
        total_value = 0
        holdings_detail = []

        for ticker, holding in self.holdings.items():
            shares = holding['shares']
            avg_cost = holding['avg_cost']
            current_price = self.etf_data[ticker]['current_price']

            cost = shares * avg_cost
            value = shares * current_price
            gain = value - cost
            gain_pct = (gain / cost * 100) if cost > 0 else 0

            total_cost += cost
            total_value += value

            holdings_detail.append({
                'ticker': ticker,
                'name': self.etf_data[ticker]['name'],
                'shares': shares,
                'avg_cost': avg_cost,
                'current_price': current_price,
                'cost': cost,
                'value': value,
                'gain': gain,
                'gain_pct': gain_pct,
                'weight': 0  # 後で計算
            })

        # 配分比率を計算
        for detail in holdings_detail:
            detail['weight'] = (detail['value'] / total_value * 100) if total_value > 0 else 0

        total_gain = total_value - total_cost
        total_gain_pct = (total_gain / total_cost * 100) if total_cost > 0 else 0

        # ポートフォリオ全体のリスク・リターンを計算
        current_allocation = self.get_current_allocation()
        weights = [current_allocation.get(ticker, 0) for ticker in self.optimizer.tickers]
        weights_array = [weights[i] if i < len(weights) else 0 for i in range(len(self.optimizer.tickers))]

        portfolio_return, portfolio_volatility, sharpe_ratio = \
            self.optimizer.calculate_portfolio_metrics(weights_array)

        return {
            'total_cost': total_cost,
            'total_value': total_value,
            'total_gain': total_gain,
            'total_gain_pct': total_gain_pct,
            'expected_annual_return': portfolio_return,
            'annual_volatility': portfolio_volatility,
            'sharpe_ratio': sharpe_ratio,
            'holdings': holdings_detail
        }

    def suggest_rebalancing(self, target_profile: str = 'aggressive') -> Dict:
        """
        リバランス提案を生成

        Args:
            target_profile: 目標プロファイル ('conservative', 'moderate', 'aggressive')

        Returns:
            リバランス提案
        """
        # 目標配分を取得
        target_portfolio = self.optimizer.suggest_allocation_by_risk_profile(target_profile)
        target_weights = {ticker: info['weight'] / 100
                         for ticker, info in target_portfolio['allocation'].items()}

        # 現在の保有状況
        current_holdings = {ticker: holding['shares']
                          for ticker, holding in self.holdings.items()}

        total_value = self.get_current_value()

        # リバランス取引を計算
        trades = self.optimizer.calculate_rebalancing_trades(
            current_holdings, target_weights, total_value
        )

        return {
            'target_portfolio': target_portfolio,
            'trades': trades,
            'current_value': total_value
        }

    def save_portfolio(self, filename: str = 'my_portfolio.json'):
        """ポートフォリオを保存"""
        data = {
            'holdings': self.holdings,
            'transactions': self.transactions,
            'saved_at': datetime.now().isoformat()
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_portfolio(self, filename: str = 'my_portfolio.json'):
        """ポートフォリオを読み込み"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.holdings = data.get('holdings', {})
            self.transactions = data.get('transactions', [])
            return True
        except FileNotFoundError:
            return False


def interactive_demo():
    """インタラクティブなデモ"""
    # ETFデータ
    etf_data = {
        '424A.T': {
            'name': 'グローバルX ゴールド ETF（為替ヘッジあり）',
            'annual_return': 8.5,
            'annual_volatility': 14.1,
            'expense_ratio': 0.1775,
            'current_price': 5120,
            'hedge': 'あり'
        },
        '425A.T': {
            'name': 'グローバルX ゴールド ETF',
            'annual_return': 28.2,
            'annual_volatility': 16.4,
            'expense_ratio': 0.1775,
            'current_price': 5085,
            'hedge': 'なし'
        },
        '314A.T': {
            'name': 'iシェアーズ ゴールドETF',
            'annual_return': 27.8,
            'annual_volatility': 16.4,
            'expense_ratio': 0.22,
            'current_price': 4850,
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
    }

    manager = PortfolioManager(etf_data)

    print("=" * 100)
    print("金ETFポートフォリオマネージャー - デモ")
    print("=" * 100)
    print()

    # サンプルポートフォリオを作成
    print("【サンプルポートフォリオを作成】")
    print("-" * 100)
    manager.add_holding('425A.T', 100, 4500)  # 100株を4500円で購入
    manager.add_holding('424A.T', 50, 5000)   # 50株を5000円で購入
    manager.add_holding('1540.T', 30, 6500)   # 30株を6500円で購入
    print("ポートフォリオを作成しました。")
    print()

    # パフォーマンス表示
    print("【現在のポートフォリオパフォーマンス】")
    print("-" * 100)
    performance = manager.calculate_performance()

    print(f"投資総額: {performance['total_cost']:,.0f}円")
    print(f"現在価値: {performance['total_value']:,.0f}円")
    print(f"評価損益: {performance['total_gain']:+,.0f}円 ({performance['total_gain_pct']:+.2f}%)")
    print(f"\n期待年率リターン: {performance['expected_annual_return']:.2f}%")
    print(f"年率リスク: {performance['annual_volatility']:.2f}%")
    print(f"シャープレシオ: {performance['sharpe_ratio']:.3f}")

    print("\n保有銘柄詳細:")
    print(f"{'銘柄':<12} {'保有株数':>8} {'平均取得':>10} {'現在価格':>10} {'評価額':>12} {'損益':>12} {'損益率':>8} {'配分':>6}")
    print("-" * 100)

    for holding in sorted(performance['holdings'], key=lambda x: x['value'], reverse=True):
        print(f"{holding['ticker']:<12} {holding['shares']:>8} "
              f"{holding['avg_cost']:>10,.0f}円 {holding['current_price']:>10,.0f}円 "
              f"{holding['value']:>12,.0f}円 {holding['gain']:>+12,.0f}円 "
              f"{holding['gain_pct']:>+7.1f}% {holding['weight']:>5.1f}%")

    print()

    # リバランス提案
    print("【リバランス提案（積極的プロファイル）】")
    print("-" * 100)
    rebalancing = manager.suggest_rebalancing('aggressive')

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
        print(f"\n推奨取引（総額: {rebalancing['current_value']:,.0f}円）:")
        print(f"{'銘柄':<12} {'売買':>6} {'株数':>8} {'金額':>12} {'現在':>8} {'目標':>8}")
        print("-" * 70)

        for ticker, trade in sorted(rebalancing['trades'].items(),
                                   key=lambda x: x[1]['value'], reverse=True):
            action_jp = '買付' if trade['action'] == 'buy' else '売却'
            print(f"{ticker:<12} {action_jp:>6} {trade['shares']:>8}株 "
                  f"{trade['value']:>12,.0f}円 {trade['current_weight']:>7.1f}% "
                  f"{trade['target_weight']:>7.1f}%")
    else:
        print("\nリバランスは不要です（現在の配分が目標に近い状態です）")

    print()
    print("=" * 100)


if __name__ == "__main__":
    interactive_demo()
