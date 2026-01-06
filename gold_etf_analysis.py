#!/usr/bin/env python3
"""
金ETFの標準偏差分析スクリプト
主要な金ETFの価格データを取得し、標準偏差（ボラティリティ）を計算して比較します。
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def analyze_gold_etfs():
    """主要な金ETFの標準偏差を計算"""

    # 主要な金ETF
    gold_etfs = {
        'GLD': 'SPDR Gold Shares',
        'IAU': 'iShares Gold Trust',
        'GLDM': 'SPDR Gold MiniShares Trust',
        'SGOL': 'abrdn Physical Gold Shares ETF',
        'BAR': 'GraniteShares Gold Trust'
    }

    # 分析期間（過去1年間）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    print("=" * 80)
    print("金ETF標準偏差分析")
    print("=" * 80)
    print(f"分析期間: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")
    print()

    results = []

    for ticker, name in gold_etfs.items():
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

            # 標準偏差を計算（年率換算）
            daily_std = daily_returns.std()
            annual_std = daily_std * np.sqrt(252)  # 252営業日で年率換算

            # その他の統計情報
            mean_return = daily_returns.mean() * 252  # 年率換算
            min_price = hist['Close'].min()
            max_price = hist['Close'].max()
            current_price = hist['Close'].iloc[-1]

            results.append({
                'ティッカー': ticker,
                'ETF名': name,
                '日次標準偏差(%)': daily_std * 100,
                '年率標準偏差(%)': annual_std * 100,
                '年率平均リターン(%)': mean_return * 100,
                '現在価格($)': current_price,
                '最低価格($)': min_price,
                '最高価格($)': max_price,
                'データ件数': len(hist)
            })

            print(f"  ✓ 完了\n")

        except Exception as e:
            print(f"  ✗ エラー: {e}\n")
            continue

    if not results:
        print("分析できるデータがありませんでした。")
        return

    # 結果をDataFrameに変換
    df_results = pd.DataFrame(results)

    # 標準偏差でソート（低い順）
    df_results = df_results.sort_values('年率標準偏差(%)')

    print("\n" + "=" * 80)
    print("分析結果（標準偏差が低い順）")
    print("=" * 80)
    print()

    # 詳細な結果を表示
    for idx, row in df_results.iterrows():
        print(f"【{row['ティッカー']}】 {row['ETF名']}")
        print(f"  日次標準偏差: {row['日次標準偏差(%)']:.4f}%")
        print(f"  年率標準偏差: {row['年率標準偏差(%)']:.2f}%")
        print(f"  年率平均リターン: {row['年率平均リターン(%)']:.2f}%")
        print(f"  現在価格: ${row['現在価格($)']:.2f}")
        print(f"  価格レンジ: ${row['最低価格($)']:.2f} ～ ${row['最高価格($)']:.2f}")
        print(f"  データ件数: {row['データ件数']}日")
        print()

    print("=" * 80)
    print("結論")
    print("=" * 80)

    lowest_std_etf = df_results.iloc[0]
    print(f"\n✓ 標準偏差が最も低い金ETF: {lowest_std_etf['ティッカー']} ({lowest_std_etf['ETF名']})")
    print(f"  年率標準偏差: {lowest_std_etf['年率標準偏差(%)']:.2f}%")
    print()

    # CSV出力
    output_file = 'gold_etf_analysis_results.csv'
    df_results.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"結果を '{output_file}' に保存しました。")
    print()

    return df_results

if __name__ == "__main__":
    analyze_gold_etfs()
