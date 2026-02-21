#!/usr/bin/env python3
"""
金ETFポートフォリオ最適化モジュール（標準ライブラリ版）
効率的フロンティア、最適配分、リバランス提案などを提供
"""

import math
import random
import statistics
from typing import Dict, List, Tuple


class PortfolioOptimizer:
    """金ETFポートフォリオの最適化を行うクラス"""

    def __init__(self, etf_data: Dict[str, Dict]):
        """
        Args:
            etf_data: ETFのデータ辞書
                {ticker: {'annual_return': float, 'annual_volatility': float, 'expense_ratio': float}}
        """
        self.etf_data = etf_data
        self.tickers = list(etf_data.keys())
        self.returns = [data['annual_return'] for data in etf_data.values()]
        self.volatilities = [data['annual_volatility'] for data in etf_data.values()]
        self.expense_ratios = [data['expense_ratio'] for data in etf_data.values()]

        # 共分散行列を生成
        self._generate_covariance_matrix()

    def _generate_covariance_matrix(self):
        """共分散行列を生成"""
        n = len(self.tickers)

        # 相関行列を初期化
        correlation = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]

        for i in range(n):
            for j in range(n):
                if i != j:
                    # 同じヘッジタイプなら高相関、異なれば低相関
                    hedge_i = self.etf_data[self.tickers[i]].get('hedge', 'なし')
                    hedge_j = self.etf_data[self.tickers[j]].get('hedge', 'なし')

                    if hedge_i == hedge_j:
                        correlation[i][j] = 0.95  # 高相関
                    else:
                        correlation[i][j] = 0.60  # 中程度の相関

        # 共分散行列 = 相関行列 × 標準偏差の外積
        self.cov_matrix = []
        for i in range(n):
            row = []
            for j in range(n):
                cov = correlation[i][j] * self.volatilities[i] * self.volatilities[j]
                row.append(cov)
            self.cov_matrix.append(row)

    def _dot_product(self, vec1: List[float], vec2: List[float]) -> float:
        """内積を計算"""
        return sum(a * b for a, b in zip(vec1, vec2))

    def _matrix_vector_mult(self, matrix: List[List[float]], vector: List[float]) -> List[float]:
        """行列とベクトルの積"""
        return [self._dot_product(row, vector) for row in matrix]

    def calculate_portfolio_metrics(self, weights: List[float]) -> Tuple[float, float, float]:
        """
        ポートフォリオのリターン、リスク、シャープレシオを計算

        Args:
            weights: 各ETFの配分比率（合計1.0）

        Returns:
            (expected_return, volatility, sharpe_ratio)
        """
        # ポートフォリオリターン
        portfolio_return = self._dot_product(weights, self.returns)

        # 経費率の影響を考慮
        portfolio_expense = self._dot_product(weights, self.expense_ratios)
        net_return = portfolio_return - portfolio_expense

        # ポートフォリオリスク（標準偏差）
        temp = self._matrix_vector_mult(self.cov_matrix, weights)
        portfolio_variance = self._dot_product(weights, temp)
        portfolio_volatility = math.sqrt(max(0, portfolio_variance))

        # シャープレシオ
        risk_free_rate = 0.5
        sharpe_ratio = (net_return - risk_free_rate) / portfolio_volatility if portfolio_volatility > 0 else 0

        return net_return, portfolio_volatility, sharpe_ratio

    def generate_random_portfolios(self, num_portfolios: int = 10000) -> List[Dict]:
        """
        ランダムなポートフォリオを生成してシミュレーション

        Args:
            num_portfolios: 生成するポートフォリオ数

        Returns:
            ポートフォリオデータのリスト
        """
        results = []

        for _ in range(num_portfolios):
            # ランダムな配分を生成
            weights = [random.random() for _ in range(len(self.tickers))]
            total = sum(weights)
            weights = [w / total for w in weights]  # 合計1.0に正規化

            ret, vol, sharpe = self.calculate_portfolio_metrics(weights)

            results.append({
                'weights': weights.copy(),
                'return': ret,
                'volatility': vol,
                'sharpe': sharpe
            })

        return results

    def find_optimal_portfolio(self, target_return: float = None,
                              min_volatility: bool = False) -> Dict:
        """
        最適ポートフォリオを探索

        Args:
            target_return: 目標リターン（Noneの場合は最大シャープレシオ）
            min_volatility: 最小ボラティリティポートフォリオを探索

        Returns:
            最適ポートフォリオの情報
        """
        # ランダムシミュレーションで探索
        portfolios = self.generate_random_portfolios(50000)

        if min_volatility:
            # 最小ボラティリティ
            best = min(portfolios, key=lambda x: x['volatility'])
        elif target_return is not None:
            # 目標リターンに近く、ボラティリティが最小
            filtered = [p for p in portfolios if p['return'] >= target_return * 0.95]
            if not filtered:
                filtered = portfolios
            best = min(filtered, key=lambda x: x['volatility'])
        else:
            # 最大シャープレシオ
            best = max(portfolios, key=lambda x: x['sharpe'])

        # 配分詳細を追加
        allocation = {}
        for i, ticker in enumerate(self.tickers):
            if best['weights'][i] > 0.01:  # 1%以上の配分のみ表示
                allocation[ticker] = {
                    'weight': best['weights'][i] * 100,
                    'name': self.etf_data[ticker]['name']
                }

        best['allocation'] = allocation
        return best

    def suggest_allocation_by_risk_profile(self, risk_profile: str) -> Dict:
        """
        リスクプロファイルに基づいた配分を提案

        Args:
            risk_profile: 'conservative', 'moderate', 'aggressive'

        Returns:
            推奨ポートフォリオ
        """
        if risk_profile == 'conservative':
            # 保守的：最小リスク
            return self.find_optimal_portfolio(min_volatility=True)
        elif risk_profile == 'aggressive':
            # 積極的：最大シャープレシオ
            return self.find_optimal_portfolio()
        else:  # moderate
            # 中庸：中程度のリターンを目標
            median_return = statistics.median(self.returns)
            return self.find_optimal_portfolio(target_return=median_return)

    def calculate_rebalancing_trades(self, current_holdings: Dict[str, float],
                                    target_weights: Dict[str, float],
                                    total_value: float) -> Dict:
        """
        リバランスに必要な売買を計算

        Args:
            current_holdings: 現在の保有数量 {ticker: shares}
            target_weights: 目標配分比率 {ticker: weight(0-1)}
            total_value: ポートフォリオ総額

        Returns:
            売買指示
        """
        trades = {}

        for ticker in self.tickers:
            current_shares = current_holdings.get(ticker, 0)
            current_price = self.etf_data[ticker].get('current_price', 5000)
            current_value = current_shares * current_price

            target_weight = target_weights.get(ticker, 0)
            target_value = total_value * target_weight

            diff_value = target_value - current_value
            diff_shares = diff_value / current_price

            if abs(diff_value) > total_value * 0.01:  # 1%以上の差がある場合のみ
                trades[ticker] = {
                    'action': 'buy' if diff_value > 0 else 'sell',
                    'shares': abs(int(diff_shares)),
                    'value': abs(diff_value),
                    'current_weight': (current_value / total_value) * 100,
                    'target_weight': target_weight * 100
                }

        return trades


def main_demo():
    """デモ実行"""
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
        }
    }

    optimizer = PortfolioOptimizer(etf_data)

    print("=" * 100)
    print("金ETFポートフォリオ最適化デモ")
    print("=" * 100)
    print()

    # 最大シャープレシオポートフォリオ
    print("【1】最大シャープレシオポートフォリオ（最も効率的）")
    print("-" * 100)
    optimal = optimizer.find_optimal_portfolio()
    print(f"期待リターン: {optimal['return']:.2f}%")
    print(f"リスク（標準偏差）: {optimal['volatility']:.2f}%")
    print(f"シャープレシオ: {optimal['sharpe']:.3f}")
    print("\n推奨配分:")
    for ticker, info in sorted(optimal['allocation'].items(),
                               key=lambda x: x[1]['weight'], reverse=True):
        print(f"  {ticker}: {info['weight']:.1f}% - {info['name']}")
    print()

    # リスクプロファイル別提案
    print("【2】リスクプロファイル別の推奨ポートフォリオ")
    print("-" * 100)

    for profile_name, profile_key in [('保守的（低リスク）', 'conservative'),
                                      ('中庸（バランス）', 'moderate'),
                                      ('積極的（高リターン）', 'aggressive')]:
        print(f"\n■ {profile_name}")
        portfolio = optimizer.suggest_allocation_by_risk_profile(profile_key)
        print(f"  期待リターン: {portfolio['return']:.2f}%")
        print(f"  リスク: {portfolio['volatility']:.2f}%")
        print(f"  シャープレシオ: {portfolio['sharpe']:.3f}")
        print("  配分:")
        for ticker, info in sorted(portfolio['allocation'].items(),
                                   key=lambda x: x[1]['weight'], reverse=True):
            print(f"    {ticker}: {info['weight']:.1f}%")

    print()
    print("=" * 100)


if __name__ == "__main__":
    main_demo()
