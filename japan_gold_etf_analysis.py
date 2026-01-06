#!/usr/bin/env python3
"""
日本市場の金ETF標準偏差分析スクリプト
東京証券取引所で取引される主要な金ETFの価格データを取得し、
標準偏差（ボラティリティ）を計算して比較します。
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def analyze_japan_gold_etfs():
    """日本市場の主要な金ETFの標準偏差を計算"""

    # 日本市場の全ての金ETF（東京証券取引所）
    japan_gold_etfs = {
        '1540.T': '純金上場信託（金の果実）',
        '1326.T': 'SPDRゴールド・シェア',
        '2840.T': 'iシェアーズ ゴールドインデックス・ファンド（為替ヘッジあり）',
        '1672.T': 'WisdomTree 金上場投資信託',
        '1328.T': 'ishares Gold Trust',
        '314A.T': 'iシェアーズ ゴールドETF',
        '424A.T': 'グローバルX ゴールド ETF（為替ヘッジあり）',
        '425A.T': 'グローバルX ゴールド ETF',
        '447A.T': 'ステート・ストリート・スパイダーゴールドETF'
    }

    # 分析期間（過去1年間）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    print("=" * 100)
    print("日本市場 金ETF標準偏差分析")
    print("=" * 100)
    print(f"分析期間: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")
    print("取引所: 東京証券取引所（TSE）")
    print()

    results = []

    for ticker, name in japan_gold_etfs.items():
        try:
            print(f"データ取得中: {ticker} ({name})...")

            # データ取得
            etf = yf.Ticker(ticker)
            hist = etf.history(start=start_date, end=end_date)

            if hist.empty:
                print(f"  ⚠️  データが取得できませんでした\n")
                continue

            # 日次リターンを計算
            daily_returns = hist['Close'].pct_change().dropna()

            # データポイントが少なすぎる場合はスキップ
            if len(daily_returns) < 30:
                print(f"  ⚠️  データポイントが不足しています（{len(daily_returns)}日分）\n")
                continue

            # 標準偏差を計算（年率換算）
            daily_std = daily_returns.std()
            annual_std = daily_std * np.sqrt(252)  # 252営業日で年率換算

            # その他の統計情報
            mean_return = daily_returns.mean() * 252  # 年率換算
            min_price = hist['Close'].min()
            max_price = hist['Close'].max()
            current_price = hist['Close'].iloc[-1]

            # 取引量情報
            avg_volume = hist['Volume'].mean()

            results.append({
                'コード': ticker,
                'ETF名': name,
                '日次標準偏差(%)': daily_std * 100,
                '年率標準偏差(%)': annual_std * 100,
                '年率平均リターン(%)': mean_return * 100,
                '現在価格(円)': current_price,
                '最低価格(円)': min_price,
                '最高価格(円)': max_price,
                '平均出来高': avg_volume,
                'データ件数': len(hist)
            })

            print(f"  ✓ 完了（{len(hist)}日分のデータ）\n")

        except Exception as e:
            print(f"  ✗ エラー: {e}\n")
            continue

    if not results:
        print("分析できるデータがありませんでした。")
        print("\n注意: 日本市場のデータ取得には時間がかかる場合があります。")
        print("また、一部のETFはデータが取得できない可能性があります。")
        return

    # 結果をDataFrameに変換
    df_results = pd.DataFrame(results)

    # 標準偏差でソート（低い順）
    df_results = df_results.sort_values('年率標準偏差(%)')

    print("\n" + "=" * 100)
    print("分析結果（標準偏差が低い順）")
    print("=" * 100)
    print()

    # 詳細な結果を表示
    for idx, row in df_results.iterrows():
        print(f"【{row['コード']}】 {row['ETF名']}")
        print(f"  日次標準偏差: {row['日次標準偏差(%)']:.4f}%")
        print(f"  年率標準偏差: {row['年率標準偏差(%)']:.2f}%")
        print(f"  年率平均リターン: {row['年率平均リターン(%)']:.2f}%")
        print(f"  現在価格: {row['現在価格(円)']:,.0f}円")
        print(f"  価格レンジ: {row['最低価格(円)']:,.0f}円 ～ {row['最高価格(円)']:,.0f}円")
        print(f"  平均出来高: {row['平均出来高']:,.0f}株/日")
        print(f"  データ件数: {row['データ件数']}日")
        print()

    print("=" * 100)
    print("結論")
    print("=" * 100)

    lowest_std_etf = df_results.iloc[0]
    print(f"\n✓ 標準偏差が最も低い金ETF: {lowest_std_etf['コード']} ({lowest_std_etf['ETF名']})")
    print(f"  年率標準偏差: {lowest_std_etf['年率標準偏差(%)']:.2f}%")
    print()

    # 比較情報
    print("=" * 100)
    print("投資判断の参考情報")
    print("=" * 100)
    print()
    print("1. 標準偏差（ボラティリティ）")
    print("   - 数値が低いほど価格変動が小さく、リスクが低い")
    print("   - 日本の金ETFは基本的に同じ金価格に連動")
    print()
    print("2. 為替リスク")
    print("   - 為替ヘッジあり: 為替変動の影響を受けにくい")
    print("   - 為替ヘッジなし: ドル円の為替変動の影響を受ける")
    print()
    print("3. 流動性")
    print("   - 平均出来高が多いほど、売買しやすい")
    print("   - スプレッド（売買価格差）が狭くなる傾向")
    print()
    print("4. 信託報酬（運用コスト）")
    print("   - 1540.T: 約0.44%/年")
    print("   - 1326.T: 約0.40%/年")
    print("   - 2840.T: 約0.13%/年（為替ヘッジコスト別途）")
    print("   - 1672.T: 約0.39%/年")
    print()

    # CSV出力
    output_file = 'japan_gold_etf_analysis_results.csv'
    df_results.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"結果を '{output_file}' に保存しました。")
    print()

    return df_results

if __name__ == "__main__":
    analyze_japan_gold_etfs()
