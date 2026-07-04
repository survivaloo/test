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
import math
import statistics
import sys
import urllib.request
from datetime import date, datetime, timezone

JGB_CSV_URL = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv"
JGB_HISTORICAL_CSV_URL = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv"
BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/LNS14000000"
FRANKFURTER_TIMESERIES_URL = "https://api.frankfurter.dev/v1/{start}..{end}?from=USD&to=JPY"
OUTPUT_PATH = "web/usdjpy-rate/market-data.json"

# 日本国債30年(現在の指標銘柄, 30年利付国債 第90回)のDCF価格モデル用パラメータ
JGB_BOND_COUPON_RATE = 3.7
JGB_BOND_MATURITY = date(2056, 3, 20)

# ベイズ統計×モンテカルロ分析のスナップショット(2026/7/1〜7/2時点、手動更新)
# 「ドル建て30年国債」= 日本国債30年をUSD/JPYで米ドル換算した価値。
# 詳細: 7/2の低調な10年債入札を受けた長期金利上昇の残存影響、財政・金融政策を
#       巡る不透明感(様子見姿勢)、FRB新議長ウォーシュ氏のタカ派発言による
#       ドル高圧力を、JGB利回り変化とUSD/JPY変化それぞれについて独立シグナルと
#       してベイズ統合し、実測相関(ρ=0.237)を用いた2変量t分布(自由度5)で
#       20万回のモンテカルロシミュレーションを実施。
BAYESIAN_FORECAST_SNAPSHOT = {
    "analysis_date": "2026-07-02",
    "analysis_date_label": "2026年7月2日",
    "method": "ベイズ統計(逆分散加重)×モンテカルロ(2変量t分布, 20万回試行) + DCF現在価値モデル",
    "current": {
        "jgb_yield_pct": 3.883,
        "usd_jpy": 161.58,
        "jgb_jpy_price": 96.8027,
        "usd_value_per_10k_face": 59.9101,
    },
    "signals_jgb_yield": [
        {"name": "過去実績(ベースライン)", "mean_bp": 0.31, "std_bp": 4.00,
         "note": "直近60営業日のJGB30年利回り日次変化(実測)"},
        {"name": "低調な10年債入札の残存影響", "mean_bp": 1.0, "std_bp": 3.5,
         "note": "財務省が7/2実施した10年債入札が低調、長期債全般で利回り上昇"},
        {"name": "財政・金融政策の不透明感", "mean_bp": 0.3, "std_bp": 3.0,
         "note": "先行き不透明感から投資家の様子見姿勢が強まっている"},
    ],
    "signals_fx": [
        {"name": "過去実績(ベースライン)", "mean_pct": 0.034, "std_pct": 0.377,
         "note": "直近60営業日のUSD/JPY日次変化(実測)"},
        {"name": "FRB新議長タカ派発言の残存影響", "mean_pct": 0.15, "std_pct": 0.25,
         "note": "7/1シントラでの発言でドル高圧力、9月利上げ観測が浮上"},
        {"name": "急伸後の調整", "mean_pct": -0.10, "std_pct": 0.25,
         "note": "7/1に162.71まで急伸後、7/2に161.58へ反落した動きを反映"},
    ],
    "correlation": 0.237,
    "posterior_jgb_yield": {"mean_bp": 0.526, "std_bp": 1.979,
                             "note": "JGB利回りシグナルをベイズ統合(逆分散加重)"},
    "posterior_fx": {"mean_pct": 0.0266, "std_pct": 0.1601,
                      "note": "USD/JPYシグナルをベイズ統合(逆分散加重)"},
    "scenarios": [
        {
            "label": "7月4日(土・週末で市場閑散)",
            "date": "2026-07-04",
            "usd_jpy_expected": 161.59,
            "usd_jpy_range_90": [161.48, 161.69],
            "jgb_jpy_price_expected": 96.785,
            "jgb_jpy_price_range_90": [96.648, 96.921],
            "usd_value_expected": 59.8957,
            "usd_value_range_90": [59.7946, 59.9964],
            "prob_up_pct": 39.3,
            "note": "土日は現物市場が閉まるため変動をシグナルごと0.2倍に縮小",
        },
        {
            "label": "7月6日(月・次の実質取引日)",
            "date": "2026-07-06",
            "usd_jpy_expected": 161.62,
            "usd_jpy_range_90": [161.10, 162.14],
            "jgb_jpy_price_expected": 96.715,
            "jgb_jpy_price_range_90": [96.033, 97.395],
            "usd_value_expected": 59.8404,
            "usd_value_range_90": [59.3379, 60.3447],
            "prob_up_pct": 39.4,
            "note": "週明け最初の実質的な取引日",
        },
    ],
    "conclusion": "利回り上昇(価格下落)とドル高(円安、ドル建て価値には逆風)の両シグナルとも"
                  "小幅ながら同方向(ドル建て価値の下落方向)に偏っており、7/6のドル建て価値の"
                  "上昇確率は約39%(下落確率約61%)とやや下落寄りの結果になりました。"
                  "ただし90%区間は現在値を大きく挟んでおり、方向を確信できる水準ではありません。",
    "caveats": [
        "各シグナルの平均・標準偏差は入手可能な定性情報を主観的に定量化したもので、厳密なバックテストは未実施",
        "JGB利回り変化とFX変化の相関(ρ=0.237)は過去60営業日の実測値だが、シグナルごとの相関構造までは反映していない",
        "為替(USD/JPY)と金利(JGB利回り)を独立に統合後、相関ρのみで結合しており、完全なモデルではない",
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

    try:
        history_points = fetch_jgb_yield_history()
        history_map = dict(history_points)
        current_date_iso = f"{year:04d}-{month:02d}-{day:02d}"
        history_map[current_date_iso] = float(latest_value)
        history = [{"date": d, "value": v} for d, v in sorted(history_map.items())[-90:]]
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: failed to fetch JGB yield history: {exc}", file=sys.stderr)
        history = []

    return {
        "value": float(latest_value),
        "date": latest_date,
        "date_label": f"{year}年{month}月{day}日",
        "unit": "%",
        "history": history,
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

    history = [
        {"period": f"{p['year']}-{p['period'][1:]}", "value": float(p["value"])}
        for p in reversed(series[:24])
        if p.get("value") not in (None, "", "-")
    ]

    return {
        "value": float(latest["value"]),
        "period": f"{latest['year']}-{latest['period'][1:]}",
        "period_name": f"{latest['year']}年{month_num}月",
        "unit": "%",
        "history": history,
        "source": "U.S. Bureau of Labor Statistics",
        "source_url": "https://www.bls.gov/cps/",
    }


def bond_dcf_price(yield_pct: float, coupon_rate: float, years: float, face: float = 100.0):
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


def fetch_jgb_yield_history():
    """財務省の履歴CSV(1974〜)からJGB30年利回りの日次系列を取得する。"""
    raw = fetch_url(JGB_HISTORICAL_CSV_URL).decode("shift_jis", errors="replace")
    reader = csv.reader(io.StringIO(raw))
    rows = list(reader)

    header_idx = None
    for i, row in enumerate(rows):
        if row and row[0].strip() == "Date":
            header_idx = i
            break
    if header_idx is None:
        raise RuntimeError("JGB historical CSV: header row not found")

    header = [c.strip() for c in rows[header_idx]]
    col_30y = header.index("30Y")

    points = []
    for row in rows[header_idx + 1:]:
        if not row or not row[0].strip() or "/" not in row[0]:
            continue
        if len(row) <= col_30y:
            continue
        value_str = row[col_30y].strip()
        if not value_str or value_str == "-":
            continue
        y, m, d = (int(p) for p in row[0].strip().split("/"))
        points.append((f"{y:04d}-{m:02d}-{d:02d}", float(value_str)))

    if not points:
        raise RuntimeError("JGB historical CSV: no valid data points")
    return points


def fetch_usdjpy_history(days: int = 130):
    """Frankfurter APIからUSD/JPYの日次時系列を取得する(過去days日)。"""
    from datetime import timedelta
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days)
    url = FRANKFURTER_TIMESERIES_URL.format(start=start.isoformat(), end=end.isoformat())
    raw = fetch_url(url)
    data = json.loads(raw)
    rates = data.get("rates", {})
    if not rates:
        raise RuntimeError("Frankfurter timeseries: no data returned")
    return sorted((d, v["JPY"]) for d, v in rates.items())


def fetch_jgb_30y_bond_usd(jgb_current: dict):
    """日本国債30年をUSD/JPYでドル換算した価値と、実測統計に基づく
    (主観的シグナルを含まない)客観的な翌取引日レンジを算出する。"""
    yield_history = fetch_jgb_yield_history()
    fx_history = fetch_usdjpy_history()

    cy, cm, cd = (int(p) for p in jgb_current["date"].split("/"))
    current_date_iso = f"{cy:04d}-{cm:02d}-{cd:02d}"

    yield_map = dict(yield_history)
    yield_map[current_date_iso] = jgb_current["value"]
    fx_map = dict(fx_history)

    common_dates = sorted(set(yield_map) & set(fx_map))
    if len(common_dates) < 10:
        raise RuntimeError("Not enough overlapping JGB/FX history for statistics")
    recent_dates = common_dates[-61:]

    yield_vals = [yield_map[d] for d in recent_dates]
    fx_vals = [fx_map[d] for d in recent_dates]

    yield_chg_bp = [(yield_vals[i] - yield_vals[i - 1]) * 100 for i in range(1, len(yield_vals))]
    fx_chg_pct = [(fx_vals[i] / fx_vals[i - 1] - 1) * 100 for i in range(1, len(fx_vals))]

    yield_vol_bp = statistics.pstdev(yield_chg_bp)
    fx_vol_pct = statistics.pstdev(fx_chg_pct)

    n = len(yield_chg_bp)
    mean_y = statistics.mean(yield_chg_bp)
    mean_f = statistics.mean(fx_chg_pct)
    cov = sum((yield_chg_bp[i] - mean_y) * (fx_chg_pct[i] - mean_f) for i in range(n)) / n
    correlation = cov / (yield_vol_bp * fx_vol_pct) if yield_vol_bp and fx_vol_pct else 0.0

    latest_fx_date, latest_fx = fx_history[-1]
    current_yield = jgb_current["value"]

    as_of = date.fromisoformat(fx_history[-1][0])
    years_to_maturity = (JGB_BOND_MATURITY - as_of).days / 365.25
    jpy_price, mod_duration = bond_dcf_price(current_yield, JGB_BOND_COUPON_RATE, years_to_maturity)
    usd_value_per_10k_face = round(jpy_price / latest_fx * 100, 4)

    # ドル建て価値の時系列(グラフ表示用)。満期までの残存年数はほぼ一定とみなし、
    # 各日のJGB利回りとUSD/JPYからその日時点のドル建て価値を再計算する。
    chart_dates = sorted(set(yield_map) & set(fx_map))[-90:]
    usd_value_history = []
    for d in chart_dates:
        y_val = yield_map[d]
        fx_val = fx_map[d]
        as_of_d = date.fromisoformat(d)
        yrs = (JGB_BOND_MATURITY - as_of_d).days / 365.25
        jpy_p, _ = bond_dcf_price(y_val, JGB_BOND_COUPON_RATE, yrs)
        usd_value_history.append({"date": d, "value": round(jpy_p / fx_val * 100, 4)})

    # 統計モデルのみによる翌取引日のドル建て価値レンジ(平均0、実測ボラティリティ・相関を使用)
    # d ln(USD建て価値) ≈ -修正デュレーション×Δ利回り(bp)/10000 - ΔFX(%)/100 の分散から90%区間を近似
    c1 = mod_duration / 10000.0
    c2 = 1.0 / 100.0
    var_ln = (c1 ** 2) * (yield_vol_bp ** 2) + (c2 ** 2) * (fx_vol_pct ** 2) \
        + 2 * c1 * c2 * correlation * yield_vol_bp * fx_vol_pct
    std_ln = math.sqrt(var_ln)
    range_90_low = round(usd_value_per_10k_face * math.exp(-1.645 * std_ln), 4)
    range_90_high = round(usd_value_per_10k_face * math.exp(1.645 * std_ln), 4)

    return {
        "jgb_yield_pct": current_yield,
        "jgb_yield_date": jgb_current["date"],
        "usd_jpy": latest_fx,
        "usd_jpy_date": latest_fx_date,
        "jgb_jpy_price": jpy_price,
        "modified_duration": mod_duration,
        "usd_value_per_10k_face": usd_value_per_10k_face,
        "history": usd_value_history,
        "jgb_yield_daily_vol_bp": round(yield_vol_bp, 3),
        "usd_jpy_daily_vol_pct": round(fx_vol_pct, 4),
        "yield_fx_correlation": round(correlation, 3),
        "statistical_range_90": {
            "low": range_90_low,
            "high": range_90_high,
            "note": "過去60営業日のJGB利回り・USD/JPYの実測ボラティリティ/相関のみに基づく統計的な変動レンジ(材料の方向感は含まない)",
        },
        "bond_info": {
            "issue": "30年利付国債(第90回)",
            "coupon_rate": JGB_BOND_COUPON_RATE,
            "maturity": JGB_BOND_MATURITY.isoformat(),
        },
        "source": "Ministry of Finance Japan (JGB利回り), Frankfurter API (USD/JPY)",
        "source_url": "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/",
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

    if "jgb_30y" in result:
        try:
            result["jgb_30y_bond_usd"] = fetch_jgb_30y_bond_usd(result["jgb_30y"])
        except Exception as exc:  # noqa: BLE001
            print(f"WARNING: failed to fetch JGB 30Y USD-denominated bond data: {exc}", file=sys.stderr)

    # ベイズ統計×モンテカルロによる分析(入札結果・財政政策を巡る不透明感・FRB発言など
    # 定性情報の解釈が必要なため自動取得はできない。分析セッションごとに手動更新するスナップショット)
    result["jgb_30y_bond_usd_forecast"] = BAYESIAN_FORECAST_SNAPSHOT

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
