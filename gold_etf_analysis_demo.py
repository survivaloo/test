#!/usr/bin/env python3
"""
金ETF標準偏差分析スクリプト（デモ版）
サンプルデータを使用して標準偏差の計算方法を示します。

実際のデータ分析には gold_etf_analysis.py を使用してください。
（yfinance, pandas, numpyが必要です）
"""

import math
import statistics

def calculate_volatility_demo():
    """デモデータを使用して標準偏差を計算"""

    # 主要な金ETFの過去の実績データ（概算値）
    # 年率標準偏差（ボラティリティ）のおおよその値
    gold_etfs_volatility = {
        'GLD': {
            'name': 'SPDR Gold Shares',
            'annual_volatility': 15.2,  # %
            'expense_ratio': 0.40,
            'aum': 58.5,  # billion USD
            'note': '最大規模の金ETF'
        },
        'IAU': {
            'name': 'iShares Gold Trust',
            'annual_volatility': 15.3,  # %
            'expense_ratio': 0.25,
            'aum': 27.8,  # billion USD
            'note': '低コストで人気'
        },
        'GLDM': {
            'name': 'SPDR Gold MiniShares Trust',
            'annual_volatility': 15.1,  # %
            'expense_ratio': 0.18,
            'aum': 7.2,  # billion USD
            'note': '最も低コスト'
        },
        'SGOL': {
            'name': 'abrdn Physical Gold Shares ETF',
            'annual_volatility': 15.4,  # %
            'expense_ratio': 0.17,
            'aum': 3.1,  # billion USD
            'note': '物理的金裏付け'
        },
        'BAR': {
            'name': 'GraniteShares Gold Trust',
            'annual_volatility': 15.3,  # %
            'expense_ratio': 0.175,
            'aum': 1.2,  # billion USD
            'note': '低コストの選択肢'
        }
    }

    print("=" * 100)
    print("金ETF標準偏差（ボラティリティ）分析 - デモ版")
    print("=" * 100)
    print()
    print("注: このデータは概算値です。最新のデータは gold_etf_analysis.py で取得してください。")
    print()

    # ボラティリティでソート
    sorted_etfs = sorted(gold_etfs_volatility.items(),
                        key=lambda x: x[1]['annual_volatility'])

    print("=" * 100)
    print("分析結果（年率標準偏差が低い順）")
    print("=" * 100)
    print()

    for ticker, data in sorted_etfs:
        print(f"【{ticker}】 {data['name']}")
        print(f"  年率標準偏差: {data['annual_volatility']:.2f}%")
        print(f"  経費率: {data['expense_ratio']:.2f}%")
        print(f"  運用資産額: ${data['aum']:.1f}B")
        print(f"  特徴: {data['note']}")
        print()

    print("=" * 100)
    print("結論と推奨")
    print("=" * 100)
    print()

    lowest_vol_etf = sorted_etfs[0]
    ticker, data = lowest_vol_etf

    print(f"✓ 標準偏差が最も低い金ETF: {ticker} ({data['name']})")
    print(f"  年率標準偏差: {data['annual_volatility']:.2f}%")
    print()

    print("重要なポイント:")
    print()
    print("1. ボラティリティの差は小さい")
    print("   すべての金ETFは同じ資産（金）に連動しているため、")
    print("   標準偏差の差は非常に小さいです（約15.1-15.4%）。")
    print()
    print("2. その他の考慮要素")
    print("   - 経費率（年間コスト）")
    print("   - 流動性（運用資産額が大きいほど売買しやすい）")
    print("   - スプレッド（売買価格差）")
    print()
    print("3. 推奨ETF")
    print("   - 低コスト重視: GLDM (経費率 0.18%)")
    print("   - 流動性重視: GLD (運用資産額 $58.5B)")
    print("   - バランス重視: IAU (経費率 0.25%, 運用資産額 $27.8B)")
    print()

    print("=" * 100)
    print("標準偏差の意味")
    print("=" * 100)
    print()
    print("標準偏差（ボラティリティ）15%の場合:")
    print("  - 約68%の確率で、年間リターンは平均±15%の範囲に収まります")
    print("  - 約95%の確率で、年間リターンは平均±30%の範囲に収まります")
    print()
    print("標準偏差が低いほど、価格変動が小さく、リスクが低いことを意味します。")
    print()

    # 簡単な計算例を示す
    print("=" * 100)
    print("標準偏差の計算例")
    print("=" * 100)
    print()

    # サンプルの日次リターンデータ（%）
    sample_returns = [0.5, -0.3, 0.8, -0.2, 0.1, 0.4, -0.6, 0.3, -0.1, 0.2]

    print("サンプル日次リターン（%）:", sample_returns)
    print()

    # 標準偏差を計算
    std_dev = statistics.stdev(sample_returns)
    mean_return = statistics.mean(sample_returns)

    print(f"平均リターン: {mean_return:.2f}%")
    print(f"日次標準偏差: {std_dev:.2f}%")

    # 年率換算（252営業日）
    annual_std = std_dev * math.sqrt(252)
    annual_return = mean_return * 252

    print(f"年率平均リターン: {annual_return:.2f}%")
    print(f"年率標準偏差: {annual_std:.2f}%")
    print()

if __name__ == "__main__":
    calculate_volatility_demo()
