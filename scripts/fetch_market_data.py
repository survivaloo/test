#!/usr/bin/env python3
"""
web/usdjpy-rate/market-data.json を更新するスクリプト。

USD/JPYはブラウザから直接CORS対応APIを叩けるためここでは扱わず、
CORS未対応の日本国債金利(財務省)と、念のためBLSの失業率データを
ビルド時に取得してJSON化し、同一オリジンの静的ファイルとして配信する。

GitHub Actions (.github/workflows/update-market-data.yml) から定期実行される。
"""
import csv
import io
import json
import statistics
import sys
import urllib.request
from datetime import datetime, timezone

JGB_CSV_URL = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv"
BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/LNS14000000"
FRED_DGS30_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS30"
YAHOO_ZB_URL = "https://query1.finance.yahoo.com/v8/finance/chart/ZB=F?range=6mo&interval=1d"
OUTPUT_PATH = "web/usdjpy-rate/market-data.json"

# 米国30年国債(現在の指標銘柄, CUSIP 912810UU0)のDCF価格モデル用パラメータ
BOND_COUPON_RATE = 5.000
BOND_FACE = 100.0
BOND_YEARS_TO_MATURITY = 29.87  # 2056/5/15満期

# ベイズ統計×モンテカルロ分析のスナップショット(2026/7/1時点、手動更新)
# 詳細: FRB新議長ウォーシュ氏のタカ派発言(2026/7/1シントラ)、
#       弱いJGB10年入札、次回米30年債入札(7/9、オファー減額)を
#       独立/相関シグナルとしてベイズ統合し、t分布(自由度5)で
#       20万回のモンテカルロシミュレーションを実施。
BAYESIAN_FORECAST_SNAPSHOT = {
    "analysis_date": "2026-07-01",
    "analysis_date_label": "2026年7月1日",
    "method": "ベイズ統計(逆分散加重・相関調整)×モンテカルロ(t分布, 20万回試行) + DCF現在価値モデル",
    "signals": [
        {"name": "過去実績(ベースライン)", "mean_bp": 0.13, "std_bp": 3.42,
         "note": "直近60営業日のDGS30日次変化"},
        {"name": "FRB新議長タカ派発言", "mean_bp": 1.0, "std_bp": 4.0,
         "note": "7/1シントラでの2%目標堅持発言、9月利上げ観測が浮上"},
        {"name": "米30年債入札需給", "mean_bp": -0.5, "std_bp": 3.0,
         "note": "7/9入札はオファー220億ドル(5月の250億ドルより減額、やや支持的)"},
        {"name": "JGB波及効果", "mean_bp": 0.8, "std_bp": 4.5,
         "note": "日本10年債入札が低調、JGB30年利回り上昇が波及(FRB発言との相関ρ=0.5で調整)"},
        {"name": "経済指標サプライズ", "mean_bp": 0.0, "std_bp": 3.42,
         "note": "7/3は休場のため新規発表なし"},
    ],
    "posterior": {"mean_bp": 0.070, "std_bp": 1.673,
                  "note": "全シグナルをベイズ統合(相関のあるシグナルはGLSで調整済み)"},
    "scenarios": [
        {
            "label": "7月3日(祝日・休場)",
            "date": "2026-07-03",
            "zb_expected": 112.53,
            "zb_range_90": [112.41, 112.64],
            "tlt_expected": 85.51,
            "tlt_range_90": [85.42, 85.60],
            "prob_up_pct": 47.5,
            "note": "米国債市場休場のためボラティリティを0.25倍に縮小",
        },
        {
            "label": "7月6日(月・次の実質取引日)",
            "date": "2026-07-06",
            "zb_expected": 112.52,
            "zb_range_90": [112.07, 112.97],
            "tlt_expected": 85.50,
            "tlt_range_90": [85.15, 85.86],
            "prob_up_pct": 47.7,
            "note": "祝日明け最初の実質的な取引日",
        },
    ],
    "conclusion": "ベイズ統合後も期待値はほぼ横ばいで、上昇確率約48%・下落確率約52%とほぼコイントス。"
                  "日次の債券価格は効率的市場に近く、既知の情報だけからは方向性を予測するのは困難。",
    "caveats": [
        "各シグナルの平均・標準偏差は入手可能な定性情報を主観的に定量化したもので、厳密なバックテストは未実施",
        "シグナル間の相関は一部(FRB発言とJGB波及)のみ調整しており、完全な独立性の仮定は不確実性を過小評価しうる",
        "投資助言ではなく、教育・分析目的の試験的なモデル出力",
    ],
}

USER_AGENT = "Mozilla/5.0 (compatible; usdjpy-rate-app-bot/1.0)"


def fetch_url(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def fetch_jgb_30y():
    raw = fetch_url(JGB_CSV_URL).decode("shift_jis", errors="replace")
    reader = csv.reader(io.StringIO(raw))
    rows = list(reader)

    header_idx = None
    for i, row in enumerate(rows):
        if row and row[0].strip() == "Date":
            header_idx = i
            break
    if header_idx is None:
        raise RuntimeError("JGB CSV: header row not found")

    header = [c.strip() for c in rows[header_idx]]
    try:
        col_30y = header.index("30Y")
    except ValueError:
        raise RuntimeError("JGB CSV: 30Y column not found")

    latest_date = None
    latest_value = None
    for row in rows[header_idx + 1:]:
        if not row or not row[0].strip():
            continue
        date_str = row[0].strip()
        if "/" not in date_str:
            continue
        if len(row) <= col_30y:
            continue
        value_str = row[col_30y].strip()
        if not value_str:
            continue
        latest_date = date_str
        latest_value = value_str

    if latest_date is None or latest_value is None:
        raise RuntimeError("JGB CSV: no valid data row found")

    year, month, day = (int(p) for p in latest_date.split("/"))

    return {
        "value": float(latest_value),
        "date": latest_date,
        "date_label": f"{year}年{month}月{day}日",
        "unit": "%",
        "source": "Ministry of Finance Japan",
        "source_url": "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/",
    }


def fetch_us_unemployment():
    raw = fetch_url(BLS_API_URL)
    data = json.loads(raw)

    if data.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(f"BLS API error: {data.get('message')}")

    series = data["Results"]["series"][0]["data"]
    if not series:
        raise RuntimeError("BLS API: no data points returned")

    latest = series[0]
    for point in series:
        if point.get("latest") == "true":
            latest = point
            break

    month_num = int(latest["period"][1:])

    return {
        "value": float(latest["value"]),
        "period": f"{latest['year']}-{latest['period'][1:]}",
        "period_name": f"{latest['year']}年{month_num}月",
        "unit": "%",
        "source": "U.S. Bureau of Labor Statistics",
        "source_url": "https://www.bls.gov/cps/",
    }


def bond_dcf_price(yield_pct: float, coupon_rate: float = BOND_COUPON_RATE,
                    years: float = BOND_YEARS_TO_MATURITY, face: float = BOND_FACE):
    """半年複利のDCFでクリーン価格・修正デュレーションを計算する。"""
    y = yield_pct / 100.0
    periods = round(years * 2)
    coupon = face * coupon_rate / 100.0 / 2.0
    y_semi = y / 2.0

    price = 0.0
    weighted_time = 0.0
    for t in range(1, periods + 1):
        cf = coupon + (face if t == periods else 0.0)
        df = (1 + y_semi) ** (-t)
        pv = cf * df
        price += pv
        weighted_time += (t / 2.0) * pv

    macaulay_duration = weighted_time / price
    modified_duration = macaulay_duration / (1 + y_semi)
    return round(price, 4), round(modified_duration, 2)


def fetch_us_30y_yield_history():
    """FREDからDGS30(米国30年国債利回り)の日次系列を取得する。"""
    raw = fetch_url(FRED_DGS30_URL).decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(raw))
    rows = list(reader)
    if not rows or rows[0][0] != "observation_date":
        raise RuntimeError("FRED DGS30 CSV: unexpected format")

    points = []
    for row in rows[1:]:
        if len(row) < 2 or row[1] in ("", "."):
            continue
        points.append((row[0], float(row[1])))

    if not points:
        raise RuntimeError("FRED DGS30 CSV: no valid data points")
    return points


def fetch_zb_futures_price():
    """Yahoo FinanceからZB(30年国債先物)の直近終値を取得する。"""
    raw = fetch_url(YAHOO_ZB_URL)
    data = json.loads(raw)
    result = data["chart"]["result"][0]
    closes = result["indicators"]["quote"][0]["close"]
    timestamps = result["timestamp"]

    for ts, close in zip(reversed(timestamps), reversed(closes)):
        if close is not None:
            date_label = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            return float(close), date_label
    raise RuntimeError("Yahoo Finance ZB: no valid close price")


def fetch_us_30y_bond():
    yield_points = fetch_us_30y_yield_history()
    latest_date, latest_yield = yield_points[-1]

    recent = [v for _, v in yield_points[-61:]]
    daily_changes_bp = [(recent[i] - recent[i - 1]) * 100 for i in range(1, len(recent))]
    daily_vol_bp = statistics.pstdev(daily_changes_bp) if len(daily_changes_bp) > 1 else 3.4

    dcf_price, mod_duration = bond_dcf_price(latest_yield)

    try:
        zb_price, zb_date = fetch_zb_futures_price()
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: failed to fetch ZB futures price: {exc}", file=sys.stderr)
        zb_price, zb_date = None, None

    # 統計モデルのみによる翌取引日の価格レンジ(±1標準偏差, ±1.645標準偏差=90%区間)
    # 修正デュレーションから 価格変化率 ≒ -修正デュレーション × 利回り変化(%) で近似
    price_vol_pct = mod_duration * (daily_vol_bp / 100.0) / 100.0 * 100.0  # % change in price per 1 std dev of yield
    base_price = zb_price if zb_price is not None else dcf_price
    range_90_low = round(base_price * (1 - 1.645 * price_vol_pct / 100.0), 2)
    range_90_high = round(base_price * (1 + 1.645 * price_vol_pct / 100.0), 2)

    return {
        "yield": latest_yield,
        "yield_date": latest_date,
        "daily_vol_bp": round(daily_vol_bp, 2),
        "dcf_price": dcf_price,
        "modified_duration": mod_duration,
        "zb_futures_price": zb_price,
        "zb_futures_date": zb_date,
        "statistical_range_90": {
            "low": range_90_low,
            "high": range_90_high,
            "note": "過去60営業日の利回りボラティリティのみに基づく統計的な変動レンジ(材料の方向感は含まない)",
        },
        "source": "FRED (DGS30), Yahoo Finance (ZB=F)",
        "source_url": "https://fred.stlouisfed.org/series/DGS30",
    }


def main():
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        result["jgb_30y"] = fetch_jgb_30y()
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: failed to fetch JGB 30Y data: {exc}", file=sys.stderr)

    try:
        result["us_unemployment"] = fetch_us_unemployment()
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: failed to fetch US unemployment data: {exc}", file=sys.stderr)

    try:
        result["us_30y_bond"] = fetch_us_30y_bond()
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: failed to fetch US 30Y bond data: {exc}", file=sys.stderr)

    # ベイズ統計×モンテカルロによる分析(FRB要人発言・入札需給・JGB波及効果など
    # 定性情報の解釈が必要なため自動取得はできない。分析セッションごとに手動更新するスナップショット)
    result["us_30y_bond_forecast"] = BAYESIAN_FORECAST_SNAPSHOT

    if "jgb_30y" not in result and "us_unemployment" not in result:
        print("ERROR: both data sources failed, aborting without writing file", file=sys.stderr)
        sys.exit(1)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Wrote {OUTPUT_PATH}:")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
