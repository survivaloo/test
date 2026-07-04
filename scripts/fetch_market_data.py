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
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=2y&interval=1d"
OUTPUT_PATH = "web/usdjpy-rate/market-data.json"

# インプライドボラティリティ(IV)の無料で取得可能な代理指標。
# JGB・USD/JPY固有のオプションIV(CME CVOL, CBOE JYVIX等)は無料APIが存在しないため、
# 金利IVの代理として米国債IVを表すMOVE指数、為替IVの代理としてリスクオフ局面で
# 円の変動と連動しやすいVIX指数(株式IV)を採用する。
MOVE_TICKER = "%5EMOVE"
VIX_TICKER = "%5EVIX"
IV_REGIME_DAMPING = 0.5  # IVレジーム比を実測ボラティリティに反映する際の減衰指数(0=無視, 1=完全反映)

# 日本国債30年(現在の指標銘柄, 30年利付国債 第90回)のDCF価格モデル用パラメータ
JGB_BOND_COUPON_RATE = 3.7
JGB_BOND_MATURITY = date(2056, 3, 20)

# ベイズ統計×モンテカルロ分析のスナップショット(2026/7/4時点、手動更新)
# 「ドル建て30年国債」= 日本国債30年をUSD/JPYで米ドル換算した価値。
# 詳細: 7/2の低調な10年債入札を受けた長期金利上昇や財政・金融政策を巡る不透明感、
#       FRB新議長ウォーシュ氏のタカ派発言(残存影響は経過日数に応じて減衰させて反映)を
#       JGB利回り変化とUSD/JPY変化それぞれについて独立シグナルとしてベイズ統合。
#       ベースラインシグナルの標準偏差には、自動計算モデルと同じ「GARCH(1,1)予測ボラティリティ
#       ×IVレジーム比(MOVE/VIX)反映後の実測ボラティリティ」の幾何平均を使用した上で、
#       実測相関(ρ)を用いた2変量t分布(自由度5)で20万回のモンテカルロシミュレーションを実施。
#       現在価値そのもの(単純DCF)についても、価格が利回り・為替に対して凸(コンベックス)
#       であることによる期待値のズレ(イェンセンの不等式)をIV反映後のσで補正
#       (usd_value_iv_adjusted)している。
BAYESIAN_FORECAST_SNAPSHOT = {
    "analysis_date": "2026-07-04",
    "analysis_date_label": "2026年7月4日",
    "method": "ベイズ統計(逆分散加重)×GARCH(1,1)×IVレジーム調整×コンベクシティ補正×モンテカルロ"
              "(2変量t分布, 20万回試行) + DCF現在価値モデル",
    "current": {
        "jgb_yield_pct": 3.937,
        "usd_jpy": 161.15,
        "jgb_jpy_price": 95.886,
        "usd_value_per_10k_face": 59.5011,
        "usd_value_iv_adjusted": 59.5052,
        "note": "usd_value_per_10k_faceは単純DCF価格、usd_value_iv_adjustedはIV反映後の"
                "コンベクシティ補正込みの現在価値推定。コンベクシティ効果は"
                "現状のボラティリティ水準では僅少",
    },
    "iv_regime": {
        "move": {"current": 66.79, "avg_1y": 75.00, "regime_ratio": 0.8905,
                  "note": "MOVE指数(米国債オプションの30日インプライドボラティリティ)。"
                          "1年平均比▲11%で、金利市場は直近平均より落ち着いた変動を織り込んでいる"},
        "vix": {"current": 15.81, "avg_1y": 18.10, "regime_ratio": 0.8735,
                "note": "VIX指数(株式オプションの30日インプライドボラティリティ)。"
                        "1年平均比▲13%で、リスクオフ的な急変動への警戒感は低め"},
        "damping_exponent": 0.5,
        "note": "JGB・USD/JPY固有のオプションIV(CME CVOL、CBOE JYVIX等)は無料で継続取得できるAPIが"
                "存在しないため、金利IVの代理としてMOVE指数、為替IVの代理としてVIX指数を採用",
    },
    "garch11": {
        "jgb_yield": {"alpha": 0.2593, "beta": 0.6553, "persistence": 0.9146,
                       "forecast_vol": 5.38, "long_run_vol": 3.59},
        "usd_jpy": {"alpha": 0.0751, "beta": 0.8461, "persistence": 0.9213,
                    "forecast_vol": 0.506, "long_run_vol": 0.651},
        "note": "GARCH(1,1)(分散ターゲティング法によるMLE)による翌営業日の予測ボラティリティ。"
                "JGB利回りは直近の入札不調によるショックの持続(α=0.26と反応感度が高め)で"
                "長期平均(3.59bp)より予測値(5.38bp)が上振れ、USD/JPYは逆に直近落ち着いており"
                "長期平均(0.651%)より予測値(0.506%)が下振れ。ベースラインシグナルのσは"
                "このGARCH予測値とIV反映後の実測ボラティリティの幾何平均",
    },
    "signals_jgb_yield": [
        {"name": "過去実績(ベースライン, GARCH(1,1)×IV反映)", "mean_bp": 0.40, "std_bp": 4.55,
         "note": "GARCH(1,1)翌日予測ボラティリティ(5.38bp)とIV反映後の実測ボラティリティ"
                 "(3.84bp)の幾何平均"},
        {"name": "低調な10年債入札の残存影響(2営業日経過し減衰)", "mean_bp": 0.5, "std_bp": 3.5,
         "note": "財務省が7/2実施した10年債入札が低調、長期債全般で利回り上昇。影響は徐々に減衰と想定"},
        {"name": "財政・金融政策の不透明感", "mean_bp": 0.3, "std_bp": 3.0,
         "note": "先行き不透明感から投資家の様子見姿勢が強まっている"},
    ],
    "signals_fx": [
        {"name": "過去実績(ベースライン, GARCH(1,1)×IV反映)", "mean_pct": 0.023, "std_pct": 0.426,
         "note": "GARCH(1,1)翌日予測ボラティリティ(0.506%)とIV反映後の実測ボラティリティ"
                 "(0.358%)の幾何平均"},
        {"name": "FRB新議長タカ派発言の残存影響(減衰)", "mean_pct": 0.10, "std_pct": 0.25,
         "note": "7/1シントラでの発言によるドル高圧力は残るが影響は逓減と想定"},
        {"name": "続落基調の継続", "mean_pct": -0.08, "std_pct": 0.22,
         "note": "7/1に162.71まで急伸後、7/2は161.58、7/3は161.15と続落した動きを反映"},
    ],
    "correlation": 0.192,
    "posterior_jgb_yield": {
        "mean_bp": 0.387,
        "std_bp": 2.037,
        "note": "JGB利回りシグナルをベイズ統合(逆分散加重)。ベースラインσに"
                "GARCH(1,1)×IVレジームの複合ボラティリティを使用済みのため追加調整は不要",
    },
    "posterior_fx": {
        "mean_pct": 0.0018,
        "std_pct": 0.154,
        "note": "USD/JPYシグナルをベイズ統合(逆分散加重)。ベースラインσに"
                "GARCH(1,1)×IVレジームの複合ボラティリティを使用済みのため追加調整は不要",
    },
    "expected_shortfall_95": {
        "note": "Expected Shortfall(CVaR, 95%)は自動計算モデル(jgb_30y_bond_usd.expected_shortfall_95)"
                "を参照。最悪5%シナリオの期待値はVaR(90%区間下限)よりさらに厳しい水準になる",
    },
    "scenarios": [
        {
            "label": "7月4日(土・週末で市場閑散)",
            "date": "2026-07-04",
            "usd_jpy_expected": 161.15,
            "usd_jpy_range_90": [161.05, 161.25],
            "jgb_jpy_price_expected": 95.873,
            "jgb_jpy_price_range_90": [95.734, 96.012],
            "usd_value_expected": 59.4928,
            "usd_value_range_90": [59.3929, 59.5929],
            "prob_up_pct": 43.7,
            "note": "土日は現物市場が閉まるため変動をシグナルごと0.2倍に縮小(GARCH×IV反映後の値を使用)",
        },
        {
            "label": "7月6日(月・次の実質取引日)",
            "date": "2026-07-06",
            "usd_jpy_expected": 161.15,
            "usd_jpy_range_90": [160.65, 161.65],
            "jgb_jpy_price_expected": 95.822,
            "jgb_jpy_price_range_90": [95.131, 96.516],
            "usd_value_expected": 59.4604,
            "usd_value_range_90": [58.9624, 59.9618],
            "prob_up_pct": 43.7,
            "note": "週明け最初の実質的な取引日。GARCH(1,1)はJGB利回りのボラティリティ・クラスタリング"
                    "(入札不調ショックの持続)を捉えて上振れ予測する一方、IVレジーム(MOVE/VIXとも"
                    "1年平均を下回る)は落ち着いた変動を示唆しており、両者の幾何平均で穏当なレンジに",
        },
    ],
    "conclusion": "利回り上昇(価格下落)方向のシグナルがやや優勢な一方、ドルは直近続落基調にあり"
                  "FX面はやや円高(ドル建て価値にはむしろ追い風)方向で、両シグナルの効果は一部相殺されます。"
                  "7/6のドル建て価値の上昇確率は約44%(下落確率約56%)とやや下落寄りですが、7/2時点の"
                  "分析(上昇確率約39%)よりも方向感はやや弱まりました。GARCH(1,1)は直近の入札不調による"
                  "JGB利回りのボラティリティ上昇を検知しレンジをやや広げる一方、MOVE・VIXの「落ち着いた"
                  "IVレジーム」はレンジを狭める方向に働き、両者を幾何平均でブレンドした結果、"
                  "純ヒストリカルボラティリティのみの場合とおおむね近い水準に落ち着いています。",
    "caveats": [
        "各シグナルの平均・標準偏差は入手可能な定性情報を主観的に定量化したもので、厳密なバックテストは未実施",
        "JGB利回り変化とFX変化の相関(ρ=0.192)は過去60営業日の実測値だが、シグナルごとの相関構造までは反映していない",
        "為替(USD/JPY)と金利(JGB利回り)を独立に統合後、相関ρのみで結合しており、完全なモデルではない",
        "IV(インプライドボラティリティ)はJGB・USD/JPY固有のオプション市場データではなく、"
        "無料で取得可能なMOVE指数(米国債IV)・VIX指数(株式IV)を代理指標として使用した近似",
        "GARCH(1,1)は分散ターゲティング法・格子探索による簡易的なMLE実装であり、"
        "定期的な再検証やより高精度な最適化(準ニュートン法等)による改善余地がある",
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


def bond_price_curvature(yield_pct: float, coupon_rate: float, years: float, h: float = 0.1):
    """DCF価格の利回りに対する1階・2階微分(コンベクシティ)を中心差分で数値的に求める。
    戻り値は(価格, dP/d利回り(%), d²P/d利回り(%)²)。単位は「利回りをyield_pctと同じ%表記で
    動かした場合」のスケール。"""
    price0, _ = bond_dcf_price(yield_pct, coupon_rate, years)
    price_up, _ = bond_dcf_price(yield_pct + h, coupon_rate, years)
    price_down, _ = bond_dcf_price(yield_pct - h, coupon_rate, years)
    dprice = (price_up - price_down) / (2 * h)
    d2price = (price_up - 2 * price0 + price_down) / (h ** 2)
    return price0, dprice, d2price


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


def fetch_usdjpy_history(days: int = 800):
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


def fetch_yahoo_series(ticker: str):
    """Yahoo Financeのチャート用APIから日次終値の時系列(過去2年)を取得する。"""
    url = YAHOO_CHART_URL.format(ticker=ticker)
    raw = fetch_url(url)
    data = json.loads(raw)
    result = data["chart"]["result"][0]
    closes = result["indicators"]["quote"][0]["close"]
    timestamps = result["timestamp"]
    points = [
        (datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"), float(c))
        for ts, c in zip(timestamps, closes) if c is not None
    ]
    if not points:
        raise RuntimeError(f"Yahoo Finance {ticker}: no valid data points")
    return points


def fetch_implied_vol_regime():
    """MOVE指数(米国債IV)・VIX指数(株式IV)を取得し、直近1年平均に対する
    現在値の比率(レジーム比)を算出する。レジーム比>1は「直近1年の平均より
    IVが高い(警戒感が強い)」ことを意味する。"""
    result = {}

    try:
        move_points = fetch_yahoo_series(MOVE_TICKER)
        move_vals = [v for _, v in move_points]
        move_current = move_vals[-1]
        move_avg_1y = statistics.mean(move_vals[-252:])
        result["move"] = {
            "current": round(move_current, 2),
            "avg_1y": round(move_avg_1y, 2),
            "regime_ratio": round(move_current / move_avg_1y, 4),
            "date": move_points[-1][0],
            "description": "ICE BofA MOVE指数(米国債オプションの30日インプライドボラティリティ)。"
                            "JGB固有のオプションIVは無料で取得できないため、金利IVレジームの代理指標として使用",
        }
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: failed to fetch MOVE index: {exc}", file=sys.stderr)

    try:
        vix_points = fetch_yahoo_series(VIX_TICKER)
        vix_vals = [v for _, v in vix_points]
        vix_current = vix_vals[-1]
        vix_avg_1y = statistics.mean(vix_vals[-252:])
        result["vix"] = {
            "current": round(vix_current, 2),
            "avg_1y": round(vix_avg_1y, 2),
            "regime_ratio": round(vix_current / vix_avg_1y, 4),
            "date": vix_points[-1][0],
            "description": "CBOE VIX指数(S&P500オプションの30日インプライドボラティリティ)。"
                            "USD/JPY固有のオプションIV(CVOL等)は無料で取得できないため、"
                            "リスクオフ局面で円の変動と連動しやすいVIXを為替IVレジームの代理指標として使用",
        }
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: failed to fetch VIX index: {exc}", file=sys.stderr)

    return result


# --- GARCH(1,1) ボラティリティモデル(分散ターゲティング法によるMLE, 追加依存なし) ---
# 単純な過去N日の実測標準偏差は「窓内は等ウェイト、窓外は無視」という単純な仮定だが、
# GARCH(1,1)はボラティリティ・クラスタリング(荒れた相場の後は荒れが続きやすい)を
# σ²_t = ω + α·r²_{t-1} + β·σ²_{t-1} という自己回帰構造で捉える。
# ここでは Engle–Mezrich (1996) の分散ターゲティング法を用い、ω = 長期分散·(1-α-β) と
# 置くことで探索パラメータを(α, β)の2次元に削減し、格子探索+局所精緻化で最尤推定する
# (scipy等の数値最適化ライブラリへの依存を避けるため)。
def fit_garch11(returns):
    n = len(returns)
    if n < 40:
        return None
    long_run_var = statistics.pvariance(returns)
    if long_run_var <= 0:
        return None

    def log_likelihood(alpha, beta):
        omega = long_run_var * (1 - alpha - beta)
        if omega <= 0:
            return -math.inf
        var_t = long_run_var
        ll = 0.0
        for r in returns:
            if var_t <= 0:
                return -math.inf
            ll += -0.5 * (math.log(2 * math.pi) + math.log(var_t) + (r * r) / var_t)
            var_t = omega + alpha * r * r + beta * var_t
        return ll

    def grid_search(alpha_range, beta_range, steps):
        best = (-math.inf, None, None)
        for ai in range(steps + 1):
            alpha = alpha_range[0] + (alpha_range[1] - alpha_range[0]) * ai / steps
            for bi in range(steps + 1):
                beta = beta_range[0] + (beta_range[1] - beta_range[0]) * bi / steps
                if alpha < 0 or beta < 0 or alpha + beta >= 0.999:
                    continue
                ll = log_likelihood(alpha, beta)
                if ll > best[0]:
                    best = (ll, alpha, beta)
        return best

    best_ll, best_alpha, best_beta = grid_search((0.01, 0.35), (0.5, 0.97), 20)
    if best_alpha is None:
        return None
    # 粗い格子探索で見つけた最適点の周辺をさらに2段階で精緻化する
    span_a, span_b = 0.06, 0.06
    for _ in range(2):
        best_ll, best_alpha, best_beta = grid_search(
            (max(0.001, best_alpha - span_a), min(0.6, best_alpha + span_a)),
            (max(0.3, best_beta - span_b), min(0.98, best_beta + span_b)),
            14,
        )
        span_a /= 3.0
        span_b /= 3.0

    omega = long_run_var * (1 - best_alpha - best_beta)
    var_t = long_run_var
    for r in returns:
        var_t = omega + best_alpha * r * r + best_beta * var_t
    forecast_var = var_t  # ループ後、翌期(1期先)の予測分散になっている

    return {
        "omega": omega,
        "alpha": round(best_alpha, 4),
        "beta": round(best_beta, 4),
        "persistence": round(best_alpha + best_beta, 4),
        "forecast_vol": math.sqrt(forecast_var),
        "long_run_vol": math.sqrt(long_run_var),
        "log_likelihood": round(best_ll, 3),
        "n_obs": n,
    }


# --- Expected Shortfall(CVaR): 自由度5のt分布における解析解 ---
# VaR(パーセンタイル)は「その水準を超える確率」しか示さないが、Expected Shortfallは
# 「その水準を超えて悪化した場合の期待値」を示す整合的リスク尺度(coherent risk measure)で、
# Basel III(FRTB)がVaRからESへ移行した理由でもある。
# 標準t分布(自由度ν)のES: ES_α = -(g_ν(q_α)/α)·(ν+q_α²)/(ν-1) (q_α=下側α分位点)
def t_dist_pdf_standard(x, df):
    from math import gamma
    c = gamma((df + 1) / 2) / (math.sqrt(df * math.pi) * gamma(df / 2))
    return c * (1 + (x * x) / df) ** (-(df + 1) / 2)


def t_expected_shortfall_multiplier(df, alpha, q_alpha):
    """標準化t分布における下側Expected Shortfallの「標準偏差換算の倍率」を返す
    (q_alpha: 下側α分位点。自由度5・α=0.05なら q_alpha≈-2.015)。"""
    g = t_dist_pdf_standard(q_alpha, df)
    return (g / alpha) * (df + q_alpha ** 2) / (df - 1)


T5_VAR_95_QUANTILE = -2.015  # 自由度5のt分布における下側5%点(既存の90%区間の算出にも使用)
T5_ES_95_MULTIPLIER = t_expected_shortfall_multiplier(5, 0.05, T5_VAR_95_QUANTILE)


def fetch_jgb_30y_bond_usd(jgb_current: dict, iv_regime: dict | None = None):
    """日本国債30年をUSD/JPYでドル換算した価値と、実測統計+インプライド
    ボラティリティ(IV)レジームに基づく客観的な翌取引日レンジを算出する。"""
    iv_regime = iv_regime or {}
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

    yield_vol_bp_realized = statistics.pstdev(yield_chg_bp)
    fx_vol_pct_realized = statistics.pstdev(fx_chg_pct)

    # --- GARCH(1,1)によるボラティリティ・クラスタリングを考慮した予測分散 ---
    # 直近60営業日の等ウェイト標準偏差(上記)は「窓内一律」の単純な推定量だが、
    # GARCH(1,1)は直近のショックの大きさ(α項)と過去の分散の持続性(β項)を
    # 自己回帰的に反映するため、荒れ相場の後は高いボラティリティが、凪の後は
    # 低いボラティリティが翌日も続きやすいという実証的性質(volatility clustering)を捉えられる。
    extended_dates = common_dates[-750:]
    ext_yield_vals = [yield_map[d] for d in extended_dates]
    ext_fx_vals = [fx_map[d] for d in extended_dates]
    ext_yield_chg_bp = [(ext_yield_vals[i] - ext_yield_vals[i - 1]) * 100 for i in range(1, len(ext_yield_vals))]
    ext_fx_chg_pct = [(ext_fx_vals[i] / ext_fx_vals[i - 1] - 1) * 100 for i in range(1, len(ext_fx_vals))]

    garch_yield = fit_garch11(ext_yield_chg_bp)
    garch_fx = fit_garch11(ext_fx_chg_pct)

    # IV(インプライドボラティリティ)レジームを実測(ヒストリカル)ボラティリティに反映する。
    # レジーム比の(damping乗根)倍だけ実測ボラティリティを調整することで、
    # オプション市場が「直近平均より警戒/楽観しているか」を織り込む。
    move_ratio = iv_regime.get("move", {}).get("regime_ratio")
    vix_ratio = iv_regime.get("vix", {}).get("regime_ratio")

    yield_vol_bp_iv = yield_vol_bp_realized * (move_ratio ** IV_REGIME_DAMPING) if move_ratio else yield_vol_bp_realized
    fx_vol_pct_iv = fx_vol_pct_realized * (vix_ratio ** IV_REGIME_DAMPING) if vix_ratio else fx_vol_pct_realized

    # 最終的なボラティリティ推定値は「IV反映後のヒストリカルボラティリティ」と
    # 「GARCH(1,1)の翌日予測ボラティリティ」の幾何平均でブレンドする。前者は
    # オプション市場が織り込む先行き期待(フォワードルッキング)、後者は時系列の
    # 自己回帰構造(足元のクラスタリング)を反映しており、性質の異なる2つのボラティリティ
    # シグナルを対数正規的に(比率のスケールで)平均することで頑健性を高める。
    yield_vol_bp = math.sqrt(yield_vol_bp_iv * garch_yield["forecast_vol"]) if garch_yield else yield_vol_bp_iv
    fx_vol_pct = math.sqrt(fx_vol_pct_iv * garch_fx["forecast_vol"]) if garch_fx else fx_vol_pct_iv

    # 相関は実測(ヒストリカル)ボラティリティで正規化する(IV調整・GARCHは水準のみに適用し、
    # 相関構造には反映しない)。
    n = len(yield_chg_bp)
    mean_y = statistics.mean(yield_chg_bp)
    mean_f = statistics.mean(fx_chg_pct)
    cov = sum((yield_chg_bp[i] - mean_y) * (fx_chg_pct[i] - mean_f) for i in range(n)) / n
    correlation = cov / (yield_vol_bp_realized * fx_vol_pct_realized) if yield_vol_bp_realized and fx_vol_pct_realized else 0.0

    latest_fx_date, latest_fx = fx_history[-1]
    current_yield = jgb_current["value"]

    as_of = date.fromisoformat(fx_history[-1][0])
    years_to_maturity = (JGB_BOND_MATURITY - as_of).days / 365.25
    jpy_price, mod_duration = bond_dcf_price(current_yield, JGB_BOND_COUPON_RATE, years_to_maturity)
    usd_value_per_10k_face = round(jpy_price / latest_fx * 100, 4)

    # --- 現在価値推定モデルへのIV(インプライドボラティリティ)反映 ---
    # 単純なDCF価格は「今日の利回り・為替」を代入した決定論的な値だが、
    # 価格(P)は利回りに対して凸(コンベックス)、ドル換算(P/FX)はFXに対しても凸なため、
    # 分散(=ボラティリティ)が大きいほど期待値は単純DCF価格からズレる(イェンセンの不等式)。
    # そこでUSD建て価値 g(y,FX)=P(y)/FX を(y0, FX0)まわりで2次のテイラー展開し、
    # IVレジーム反映済みのσ(yield_vol_bp, fx_vol_pct)と実測相関ρを用いて期待値を補正する。
    #   E[g] ≈ g0 + 0.5*g_yy*Var(Δy) + 0.5*g_xx*Var(ΔFX) + g_yx*Cov(Δy,ΔFX)
    _, dprice_dy, d2price_dy2 = bond_price_curvature(current_yield, JGB_BOND_COUPON_RATE, years_to_maturity)
    sigma_y_pct = yield_vol_bp / 100.0  # bp→パーセンテージポイント
    sigma_x_frac = fx_vol_pct / 100.0   # %→比率

    convexity_term = 0.5 * d2price_dy2 * (sigma_y_pct ** 2) / latest_fx * 100
    fx_convexity_term = jpy_price * (sigma_x_frac ** 2) / latest_fx * 100
    cross_term = -dprice_dy * correlation * sigma_y_pct * sigma_x_frac / latest_fx * 100
    iv_pv_adjustment = convexity_term + fx_convexity_term + cross_term
    usd_value_iv_adjusted = round(usd_value_per_10k_face + iv_pv_adjustment, 4)

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
    range_90_low = round(usd_value_iv_adjusted * math.exp(-1.645 * std_ln), 4)
    range_90_high = round(usd_value_iv_adjusted * math.exp(1.645 * std_ln), 4)

    # Expected Shortfall(95%, 自由度5のt分布解析解)。VaR(パーセンタイル)は「その水準を
    # 超える確率」のみ示すが、ESは「悪化した場合の期待値」を示す整合的リスク尺度。
    es_95_low = round(usd_value_iv_adjusted * math.exp(-T5_ES_95_MULTIPLIER * std_ln), 4)

    return {
        "jgb_yield_pct": current_yield,
        "jgb_yield_date": jgb_current["date"],
        "usd_jpy": latest_fx,
        "usd_jpy_date": latest_fx_date,
        "jgb_jpy_price": jpy_price,
        "modified_duration": mod_duration,
        "convexity": round(d2price_dy2 / jpy_price, 4),
        "usd_value_per_10k_face": usd_value_per_10k_face,
        "usd_value_iv_adjusted": usd_value_iv_adjusted,
        "iv_present_value_adjustment": {
            "total": round(iv_pv_adjustment, 4),
            "yield_convexity_term": round(convexity_term, 4),
            "fx_convexity_term": round(fx_convexity_term, 4),
            "cross_term": round(cross_term, 4),
            "note": "IV(MOVE指数・VIX指数)反映後のボラティリティを用いて、価格が利回りに対して凸(コンベックス)"
                    "であること・USD換算が為替に対して凸であることによる期待値のズレ(イェンセンの不等式)を"
                    "単純DCF価格に加算した現在価値推定への補正額",
        },
        "history": usd_value_history,
        "jgb_yield_daily_vol_bp": round(yield_vol_bp, 3),
        "jgb_yield_daily_vol_bp_realized": round(yield_vol_bp_realized, 3),
        "jgb_yield_daily_vol_bp_iv_adjusted": round(yield_vol_bp_iv, 3),
        "usd_jpy_daily_vol_pct": round(fx_vol_pct, 4),
        "usd_jpy_daily_vol_pct_realized": round(fx_vol_pct_realized, 4),
        "usd_jpy_daily_vol_pct_iv_adjusted": round(fx_vol_pct_iv, 4),
        "yield_fx_correlation": round(correlation, 3),
        "iv_regime": iv_regime,
        "garch11": {
            "jgb_yield": garch_yield,
            "usd_jpy": garch_fx,
            "note": "GARCH(1,1)(分散ターゲティング法によるMLE, 格子探索で推定)による翌営業日の"
                    "予測ボラティリティ。過去60営業日の等ウェイト実測値と異なり、ボラティリティ・"
                    "クラスタリング(荒れ相場の後は荒れが続きやすい性質)を反映できる。"
                    "最終的な採用ボラティリティ(jgb_yield_daily_vol_bp等)はIV反映値との幾何平均",
        },
        "statistical_range_90": {
            "low": range_90_low,
            "high": range_90_high,
            "note": "IV反映後の現在価値推定(usd_value_iv_adjusted)を中心に、過去60営業日の実測ボラティリティ・"
                    "MOVE/VIXのIVレジーム比・GARCH(1,1)予測ボラティリティを組み合わせた統計的な"
                    "変動レンジ(個別の材料の方向感は含まない)",
        },
        "expected_shortfall_95": {
            "low": es_95_low,
            "note": "下側Expected Shortfall(CVaR, 95%): 起こりうる最悪5%のシナリオに限定した場合の"
                    "期待値(自由度5のt分布の解析解)。VaR(90%区間の下限)より厳しい、"
                    "テールリスクを織り込んだ保守的な指標(Basel III/FRTBで採用されている手法)",
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

    iv_regime = fetch_implied_vol_regime()

    if "jgb_30y" in result:
        try:
            result["jgb_30y_bond_usd"] = fetch_jgb_30y_bond_usd(result["jgb_30y"], iv_regime)
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
