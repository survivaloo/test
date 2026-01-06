#!/usr/bin/env python3
"""
日本市場の金ETF標準偏差分析スクリプト（デモ版）
サンプルデータを使用して日本の金ETFの標準偏差を比較します。

実際のデータ分析には japan_gold_etf_analysis.py を使用してください。
"""

import math
import statistics

def analyze_japan_gold_etfs_demo():
    """デモデータを使用して日本市場の金ETFを分析"""

    # 日本市場の主要な金ETF（概算データ）
    japan_gold_etfs = {
        '1540.T': {
            'name': '純金上場信託（金の果実）',
            'annual_volatility': 16.5,  # %（為替変動を含む）
            'expense_ratio': 0.44,
            'avg_volume': 850000,  # 株/日
            'current_price': 6950,  # 円
            'note': '国内最大規模の金ETF',
            'hedge': 'なし'
        },
        '1326.T': {
            'name': 'SPDRゴールド・シェア',
            'annual_volatility': 16.8,  # %
            'expense_ratio': 0.40,
            'avg_volume': 45000,
            'current_price': 22100,
            'note': '米国GLDの日本上場版',
            'hedge': 'なし'
        },
        '2840.T': {
            'name': 'iシェアーズ ゴールドインデックス・ファンド（為替ヘッジあり）',
            'annual_volatility': 14.2,  # %（為替ヘッジあり）
            'expense_ratio': 0.13,
            'avg_volume': 12000,
            'current_price': 18500,
            'note': '為替ヘッジありで安定的',
            'hedge': 'あり'
        },
        '1672.T': {
            'name': 'WisdomTree 金上場投資信託',
            'annual_volatility': 16.7,  # %
            'expense_ratio': 0.39,
            'avg_volume': 8500,
            'current_price': 2215,
            'note': '低価格で小口投資向け',
            'hedge': 'なし'
        },
        '1328.T': {
            'name': 'ishares Gold Trust',
            'annual_volatility': 16.6,  # %
            'expense_ratio': 0.25,
            'avg_volume': 35000,
            'current_price': 3280,
            'note': '米国IAUの日本上場版',
            'hedge': 'なし'
        }
    }

    print("=" * 100)
    print("日本市場 金ETF標準偏差（ボラティリティ）分析 - デモ版")
    print("=" * 100)
    print()
    print("注: このデータは概算値です。最新のデータは japan_gold_etf_analysis.py で取得してください。")
    print()

    # ボラティリティでソート
    sorted_etfs = sorted(japan_gold_etfs.items(),
                        key=lambda x: x[1]['annual_volatility'])

    print("=" * 100)
    print("分析結果（年率標準偏差が低い順）")
    print("=" * 100)
    print()

    for ticker, data in sorted_etfs:
        print(f"【{ticker}】 {data['name']}")
        print(f"  年率標準偏差: {data['annual_volatility']:.2f}%")
        print(f"  信託報酬: {data['expense_ratio']:.2f}%")
        print(f"  為替ヘッジ: {data['hedge']}")
        print(f"  平均出来高: {data['avg_volume']:,}株/日")
        print(f"  参考価格: {data['current_price']:,}円")
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
    print(f"  為替ヘッジ: {data['hedge']}")
    print()

    print("重要なポイント:")
    print()
    print("1. 為替ヘッジの有無が大きな違い")
    print("   - 為替ヘッジあり（2840.T）: 標準偏差 14.2%")
    print("     → 金価格のみの変動、為替リスクなし")
    print()
    print("   - 為替ヘッジなし（その他）: 標準偏差 16.5-16.8%")
    print("     → 金価格 + ドル円為替の変動")
    print()
    print("2. 流動性の考慮")
    print("   - 1540.T（純金上場信託）: 最も高い流動性（850,000株/日）")
    print("   - スプレッドが狭く、大口取引に適している")
    print()
    print("3. 投資目的別の推奨ETF")
    print()
    print("   【リスク最小重視】")
    print("   → 2840.T（為替ヘッジあり、標準偏差 14.2%）")
    print("   - 為替変動リスクを避けたい投資家向け")
    print("   - 純粋な金価格の変動のみを取りたい場合")
    print()
    print("   【流動性重視】")
    print("   → 1540.T（純金上場信託、出来高 850,000株/日）")
    print("   - 大口取引、頻繁な売買に適している")
    print("   - スプレッドが最も狭い")
    print()
    print("   【コスト重視】")
    print("   → 2840.T（信託報酬 0.13%、ただし為替ヘッジコスト別途）")
    print("   - 長期保有の場合、信託報酬の影響が大きい")
    print()
    print("   【バランス重視】")
    print("   → 1328.T（ishares Gold Trust）")
    print("   - 信託報酬 0.25%と比較的低コスト")
    print("   - 適度な流動性（35,000株/日）")
    print()

    print("=" * 100)
    print("米国市場との比較")
    print("=" * 100)
    print()
    print("米国金ETF（為替ヘッジなし）:")
    print("  - GLDM: 年率標準偏差 15.1%")
    print("  - GLD:  年率標準偏差 15.2%")
    print("  - IAU:  年率標準偏差 15.3%")
    print()
    print("日本金ETF（為替ヘッジなし）:")
    print("  - 標準偏差 16.5-16.8%（米国より約1.5%高い）")
    print("  - 理由: ドル円為替変動の影響が追加される")
    print()
    print("日本金ETF（為替ヘッジあり）:")
    print("  - 2840.T: 標準偏差 14.2%（米国より低い）")
    print("  - 為替リスクを排除することで、より安定的")
    print()

    print("=" * 100)
    print("投資判断のチェックリスト")
    print("=" * 100)
    print()
    print("□ 為替リスクを取りたいか？")
    print("  YES → 為替ヘッジなし（1540.T, 1326.T, 1672.T, 1328.T）")
    print("        円安時に追加リターンを期待できる")
    print("  NO  → 為替ヘッジあり（2840.T）")
    print("        純粋な金価格の変動のみ")
    print()
    print("□ 取引頻度は？")
    print("  高頻度 → 1540.T（流動性が最も高い）")
    print("  低頻度 → どのETFでも可")
    print()
    print("□ 投資金額は？")
    print("  大口 → 1540.T（流動性重視）")
    print("  小口 → 1672.T（最低価格 2,215円から）")
    print()
    print("□ 保有期間は？")
    print("  長期 → 信託報酬の低い2840.Tまたは1328.T")
    print("  短期 → 流動性の高い1540.T")
    print()

    # 標準偏差の計算例
    print("=" * 100)
    print("標準偏差が示すリスクの意味")
    print("=" * 100)
    print()
    print("例: 年率標準偏差 16%の場合（為替ヘッジなし）")
    print("  金価格の年率リターンが0%と仮定すると...")
    print("  - 約68%の確率で、-16% ～ +16% の範囲に収まる")
    print("  - 約95%の確率で、-32% ～ +32% の範囲に収まる")
    print()
    print("例: 年率標準偏差 14%の場合（為替ヘッジあり）")
    print("  - 約68%の確率で、-14% ～ +14% の範囲に収まる")
    print("  - 約95%の確率で、-28% ～ +28% の範囲に収まる")
    print()
    print("→ 為替ヘッジありの方が、価格変動幅が小さく安定的")
    print()

if __name__ == "__main__":
    analyze_japan_gold_etfs_demo()
