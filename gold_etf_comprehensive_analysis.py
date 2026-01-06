#!/usr/bin/env python3
"""
金ETF包括的分析スクリプト（デモ版）
標準偏差、リターン、シャープレシオを計算して総合評価を行います。
"""

import math
import statistics

def comprehensive_gold_etf_analysis():
    """金ETFの標準偏差、リターン、リスクリターン比率を分析"""

    # 日本市場の全ての金ETF（過去1年のデータ概算）
    japan_gold_etfs = {
        '424A.T': {
            'name': 'グローバルX ゴールド ETF（為替ヘッジあり）',
            'annual_return': 8.5,  # %
            'annual_volatility': 14.1,  # %（為替ヘッジあり）
            'expense_ratio': 0.1775,
            'avg_volume': 18000,
            'hedge': 'あり',
            'note': '東証最低水準の信託報酬（2025年9月上場）'
        },
        '2840.T': {
            'name': 'iシェアーズ ゴールドインデックス・ファンド（為替ヘッジあり）',
            'annual_return': 8.3,  # %
            'annual_volatility': 14.2,  # %（為替ヘッジあり）
            'expense_ratio': 0.13,
            'avg_volume': 12000,
            'hedge': 'あり',
            'note': '為替ヘッジありで安定的'
        },
        '314A.T': {
            'name': 'iシェアーズ ゴールドETF',
            'annual_return': 27.8,  # %（金価格上昇＋円安効果）
            'annual_volatility': 16.4,  # %
            'expense_ratio': 0.22,
            'avg_volume': 25000,
            'hedge': 'なし',
            'note': 'NISA成長投資枠対象'
        },
        '425A.T': {
            'name': 'グローバルX ゴールド ETF',
            'annual_return': 28.2,  # %（金価格上昇＋円安効果）
            'annual_volatility': 16.4,  # %
            'expense_ratio': 0.1775,
            'avg_volume': 22000,
            'hedge': 'なし',
            'note': '東証最低水準の信託報酬（2025年9月上場）'
        },
        '1540.T': {
            'name': '純金上場信託（金の果実）',
            'annual_return': 27.5,  # %（金価格上昇＋円安効果）
            'annual_volatility': 16.5,  # %
            'expense_ratio': 0.44,
            'avg_volume': 850000,
            'hedge': 'なし',
            'note': '国内最大規模の金ETF'
        },
        '447A.T': {
            'name': 'ステート・ストリート・スパイダーゴールドETF',
            'annual_return': 27.6,  # %
            'annual_volatility': 16.5,  # %
            'expense_ratio': 0.18,
            'avg_volume': 15000,
            'hedge': 'なし',
            'note': '2025年11月上場'
        },
        '1328.T': {
            'name': 'ishares Gold Trust',
            'annual_return': 27.3,  # %
            'annual_volatility': 16.6,  # %
            'expense_ratio': 0.25,
            'avg_volume': 35000,
            'hedge': 'なし',
            'note': '米国IAUの日本上場版'
        },
        '1672.T': {
            'name': 'WisdomTree 金上場投資信託',
            'annual_return': 27.0,  # %
            'annual_volatility': 16.7,  # %
            'expense_ratio': 0.39,
            'avg_volume': 8500,
            'hedge': 'なし',
            'note': '低価格で小口投資向け'
        },
        '1326.T': {
            'name': 'SPDRゴールド・シェア',
            'annual_return': 26.8,  # %
            'annual_volatility': 16.8,  # %
            'expense_ratio': 0.40,
            'avg_volume': 45000,
            'hedge': 'なし',
            'note': '米国GLDの日本上場版'
        }
    }

    # シャープレシオを計算（リスクフリーレート0.5%と仮定）
    risk_free_rate = 0.5

    for ticker, data in japan_gold_etfs.items():
        excess_return = data['annual_return'] - risk_free_rate
        sharpe_ratio = excess_return / data['annual_volatility']
        data['sharpe_ratio'] = sharpe_ratio

        # リスク調整後リターンを計算
        data['risk_adjusted_return'] = data['annual_return'] / data['annual_volatility']

    print("=" * 120)
    print("金ETF包括的分析 - 標準偏差、リターン、リスク調整後リターン")
    print("=" * 120)
    print()
    print("注: このデータは概算値です。実際の投資判断には最新データをご確認ください。")
    print()

    # 標準偏差2%の差の具体例を説明
    print("=" * 120)
    print("【重要】標準偏差2%の差が意味するリスクの違い")
    print("=" * 120)
    print()
    print("100万円を投資した場合の価格変動シミュレーション:")
    print()
    print("標準偏差14%の場合（424A.T - 為替ヘッジあり）:")
    print("  • 68%の確率で年間リターンが -14% ～ +14% の範囲")
    print("    → 資産価値: 86万円 ～ 114万円")
    print("  • 95%の確率で年間リターンが -28% ～ +28% の範囲")
    print("    → 資産価値: 72万円 ～ 128万円")
    print()
    print("標準偏差16%の場合（425A.T - 為替ヘッジなし）:")
    print("  • 68%の確率で年間リターンが -16% ～ +16% の範囲")
    print("    → 資産価値: 84万円 ～ 116万円")
    print("  • 95%の確率で年間リターンが -32% ～ +32% の範囲")
    print("    → 資産価値: 68万円 ～ 132万円")
    print()
    print("【2%の差の影響】")
    print("  • 悪い年（-2標準偏差）: 4万円の追加損失リスク（72万円 vs 68万円）")
    print("  • 良い年（+2標準偏差）: 4万円の追加利益機会（128万円 vs 132万円）")
    print("  • ボラティリティが高い = 損失リスクも大きいが、大きな利益の可能性もある")
    print()

    # リターン順でソート
    print("=" * 120)
    print("【分析1】年率リターンランキング（高い順）")
    print("=" * 120)
    print()

    sorted_by_return = sorted(japan_gold_etfs.items(),
                             key=lambda x: x[1]['annual_return'],
                             reverse=True)

    for rank, (ticker, data) in enumerate(sorted_by_return, 1):
        print(f"{rank}. 【{ticker}】 {data['name']}")
        print(f"   年率リターン: {data['annual_return']:>6.2f}%")
        print(f"   年率標準偏差: {data['annual_volatility']:>6.2f}%")
        print(f"   為替ヘッジ: {data['hedge']:>4s}")
        print(f"   信託報酬: {data['expense_ratio']:>6.4f}%")
        print()

    # 標準偏差順でソート
    print("=" * 120)
    print("【分析2】年率標準偏差ランキング（低リスク順）")
    print("=" * 120)
    print()

    sorted_by_volatility = sorted(japan_gold_etfs.items(),
                                  key=lambda x: x[1]['annual_volatility'])

    for rank, (ticker, data) in enumerate(sorted_by_volatility, 1):
        print(f"{rank}. 【{ticker}】 {data['name']}")
        print(f"   年率標準偏差: {data['annual_volatility']:>6.2f}%")
        print(f"   年率リターン: {data['annual_return']:>6.2f}%")
        print(f"   為替ヘッジ: {data['hedge']:>4s}")
        print()

    # シャープレシオ順でソート
    print("=" * 120)
    print("【分析3】シャープレシオランキング（リスク調整後リターン、高い順）")
    print("=" * 120)
    print()
    print("※ シャープレシオ = (リターン - リスクフリーレート) / 標準偏差")
    print("※ リスク1単位あたりのリターンを示す。高いほど効率的な投資。")
    print()

    sorted_by_sharpe = sorted(japan_gold_etfs.items(),
                             key=lambda x: x[1]['sharpe_ratio'],
                             reverse=True)

    for rank, (ticker, data) in enumerate(sorted_by_sharpe, 1):
        print(f"{rank}. 【{ticker}】 {data['name']}")
        print(f"   シャープレシオ: {data['sharpe_ratio']:>6.3f}")
        print(f"   年率リターン: {data['annual_return']:>6.2f}%")
        print(f"   年率標準偏差: {data['annual_volatility']:>6.2f}%")
        print(f"   為替ヘッジ: {data['hedge']:>4s}")
        print()

    # 総合評価
    print("=" * 120)
    print("【総合評価と推奨】")
    print("=" * 120)
    print()

    # 為替ヘッジあり/なしで分けて評価
    hedged_etfs = {k: v for k, v in japan_gold_etfs.items() if v['hedge'] == 'あり'}
    unhedged_etfs = {k: v for k, v in japan_gold_etfs.items() if v['hedge'] == 'なし'}

    # 為替ヘッジあり
    print("【為替ヘッジあり】")
    best_hedged = max(hedged_etfs.items(), key=lambda x: x[1]['sharpe_ratio'])
    print(f"✓ 最優秀: {best_hedged[0]} ({best_hedged[1]['name']})")
    print(f"  - 年率リターン: {best_hedged[1]['annual_return']:.2f}%")
    print(f"  - 年率標準偏差: {best_hedged[1]['annual_volatility']:.2f}%")
    print(f"  - シャープレシオ: {best_hedged[1]['sharpe_ratio']:.3f}")
    print(f"  - 信託報酬: {best_hedged[1]['expense_ratio']:.4f}%")
    print(f"  - 特徴: 為替リスクなし、純粋な金価格の変動のみ")
    print()

    # 為替ヘッジなし
    print("【為替ヘッジなし】")
    best_unhedged = max(unhedged_etfs.items(), key=lambda x: x[1]['sharpe_ratio'])
    print(f"✓ 最優秀: {best_unhedged[0]} ({best_unhedged[1]['name']})")
    print(f"  - 年率リターン: {best_unhedged[1]['annual_return']:.2f}%")
    print(f"  - 年率標準偏差: {best_unhedged[1]['annual_volatility']:.2f}%")
    print(f"  - シャープレシオ: {best_unhedged[1]['sharpe_ratio']:.3f}")
    print(f"  - 信託報酬: {best_unhedged[1]['expense_ratio']:.4f}%")
    print(f"  - 特徴: 円安時に追加リターンを期待できる")
    print()

    print("=" * 120)
    print("【投資判断のポイント】")
    print("=" * 120)
    print()
    print("1. 為替リスクをどう考えるか？")
    print()
    print("   為替ヘッジあり（424A.T, 2840.T）:")
    print("   • リターン: 約8-9%（純粋な金価格上昇のみ）")
    print("   • リスク: 14%前後（低い）")
    print("   • 向いている人: 為替変動を避けたい、安定重視")
    print()
    print("   為替ヘッジなし（425A.T, 314A.T等）:")
    print("   • リターン: 約27-28%（金価格上昇＋円安効果）")
    print("   • リスク: 16%前後（高い）")
    print("   • 向いている人: 円安トレンド継続を期待、高リターン狙い")
    print()
    print("2. リスクとリターンのバランス")
    print()
    print("   過去1年のパフォーマンスでは:")
    print("   • 為替ヘッジなしの方が、円安の恩恵で約20%高いリターン")
    print("   • ただし標準偏差は約2%高い（追加リスク）")
    print("   • シャープレシオは為替ヘッジなしの方が優秀")
    print()
    print("3. 今後の見通しで選択")
    print()
    print("   円安が続くと予想:")
    print("   → 為替ヘッジなし（425A.T）を推奨")
    print("   → 金価格上昇＋円安のダブル効果")
    print()
    print("   円高に転じる可能性:")
    print("   → 為替ヘッジあり（424A.T）を推奨")
    print("   → 為替変動の悪影響を避けられる")
    print()
    print("   不確実な場合:")
    print("   → 両方に分散投資を検討")
    print()

    print("=" * 120)
    print()

if __name__ == "__main__":
    comprehensive_gold_etf_analysis()
