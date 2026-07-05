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
#       ベースラインシグナルの標準偏差には、自動計算モデルと同じ「GARCH(1,1)-t予測ボラティリティ
#       ×IVレジーム比(MOVE/VIX)反映後の実測ボラティリティ」の幾何平均を使用した上で、
#       実測相関(ρ)とGARCH標準化残差からMLE推定した自由度ν(データ駆動, 固定値5から変更)を
#       用いた2変量t分布で20万回のモンテカルロシミュレーションを実施。
#       現在価値そのもの(単純DCF)についても、価格が利回り・為替に対して凸(コンベックス)
#       であることによる期待値のズレ(イェンセンの不等式)をIV反映後のσで補正
#       (usd_value_iv_adjusted)している。
BAYESIAN_FORECAST_SNAPSHOT = {
    "analysis_date": "2026-07-04",
    "analysis_date_label": "2026年7月4日",
    "method": "ベイズ統計(逆分散加重)×GARCH(1,1)-t(自由度νも同時推定)×IVレジーム調整×"
              "コンベクシティ補正×モンテカルロ(2変量t分布, データ駆動ν, 20万回試行) + "
              "DCF現在価値モデル + EVT(極値理論)/FHS(ヒストリカル・シミュレーション)による"
              "テールリスクのクロスチェック",
    "current": {
        "jgb_yield_pct": 3.937,
        "usd_jpy": 161.15,
        "jgb_jpy_price": 95.886,
        "usd_value_per_10k_face": 59.5011,
        "usd_value_iv_adjusted": 59.505,
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
    "degrees_of_freedom": {
        "estimated_nu": 5.04,
        "source": "usd_value_direct_garch_t",
        "note": "従来固定していた「自由度5」を、USD建て価値の日次変化率にGARCH(1,1)-tを"
                "直接あてはめてMLE推定した値(5.04)に更新。従来の仮定がほぼ妥当だったことが"
                "データで裏付けられた形",
    },
    "garch11": {
        "jgb_yield": {"alpha": 0.3957, "beta": 0.5661, "persistence": 0.9618,
                       "forecast_vol": 6.04, "long_run_vol": 3.59, "nu": 4.02},
        "usd_jpy": {"alpha": 0.194, "beta": 0.8049, "persistence": 0.9989,
                    "forecast_vol": 0.308, "long_run_vol": 0.651, "nu": 3.34},
        "usd_value_direct": {"alpha": 0.3274, "beta": 0.4771, "persistence": 0.8046,
                              "forecast_vol_pct": 1.058, "nu": 5.04},
        "note": "GARCH(1,1)-t(分散ターゲティング法によるMLE, 反復プロファイル尤度で自由度νも"
                "同時推定)による翌営業日の予測ボラティリティ。JGB利回りは直近の入札不調による"
                "ショックの持続(α=0.40と反応感度が高め)で長期平均(3.59bp)より予測値(6.04bp)が"
                "上振れ、USD/JPYはボラティリティの持続性が非常に高い(β=0.80)ものの直近は落ち着いて"
                "おり長期平均(0.651%)より予測値(0.308%)が下振れ。usd_value_directは利回り・為替を"
                "合成せずUSD建て価値の変化率に直接あてはめたクロスチェック用モデルで、"
                "自由度ν=5.04は全体の統計的自由度推定に採用",
    },
    "signals_jgb_yield": [
        {"name": "過去実績(ベースライン, GARCH(1,1)-t×IV反映)", "mean_bp": 0.40, "std_bp": 4.82,
         "note": "GARCH(1,1)-t翌日予測ボラティリティ(6.04bp)とIV反映後の実測ボラティリティ"
                 "(3.84bp)の幾何平均"},
        {"name": "低調な10年債入札の残存影響(2営業日経過し減衰)", "mean_bp": 0.5, "std_bp": 3.5,
         "note": "財務省が7/2実施した10年債入札が低調、長期債全般で利回り上昇。影響は徐々に減衰と想定"},
        {"name": "財政・金融政策の不透明感", "mean_bp": 0.3, "std_bp": 3.0,
         "note": "先行き不透明感から投資家の様子見姿勢が強まっている"},
    ],
    "signals_fx": [
        {"name": "過去実績(ベースライン, GARCH(1,1)-t×IV反映)", "mean_pct": 0.023, "std_pct": 0.334,
         "note": "GARCH(1,1)-t翌日予測ボラティリティ(0.308%)とIV反映後の実測ボラティリティ"
                 "(0.362%)の幾何平均"},
        {"name": "FRB新議長タカ派発言の残存影響(減衰)", "mean_pct": 0.10, "std_pct": 0.25,
         "note": "7/1シントラでの発言によるドル高圧力は残るが影響は逓減と想定"},
        {"name": "続落基調の継続", "mean_pct": -0.08, "std_pct": 0.22,
         "note": "7/1に162.71まで急伸後、7/2は161.58、7/3は161.15と続落した動きを反映"},
    ],
    "correlation": 0.192,
    "posterior_jgb_yield": {
        "mean_bp": 0.388,
        "std_bp": 2.059,
        "note": "JGB利回りシグナルをベイズ統合(逆分散加重)。ベースラインσに"
                "GARCH(1,1)-t×IVレジームの複合ボラティリティを使用済みのため追加調整は不要",
    },
    "posterior_fx": {
        "mean_pct": 0.0034,
        "std_pct": 0.148,
        "note": "USD/JPYシグナルをベイズ統合(逆分散加重)。ベースラインσに"
                "GARCH(1,1)-t×IVレジームの複合ボラティリティを使用済みのため追加調整は不要",
    },
    "expected_shortfall_95": {
        "note": "Expected Shortfall(CVaR, 95%)は自動計算モデル(jgb_30y_bond_usd.expected_shortfall_95)"
                "を参照。パラメトリック(データ駆動ν)・EVT(極値理論)・FHS(ヒストリカル・"
                "シミュレーション)の3手法のうち最も保守的な値を採用したアンサンブル値で、"
                "VaR(90%区間下限)よりさらに厳しい水準になる",
    },
    "backtest_note": "ローリング60日窓のVaR(95%)バックテストでは、実測超過率(観測期間で約2.4%)が"
                      "理論値(5%)を下回っておりKupiec検定でも統計的に有意な乖離が確認されたが、"
                      "これはモデルが直近相場で「やや保守的すぎる」(見積もりが厳しめ)方向の乖離であり、"
                      "危険側(超過が想定より多い)の乖離ではない点に留意",
    "tail_dependence_note": "利回り上昇と円安が同時に上位10%の悪材料となる経験的な同時確率は、"
                             "正規分布(独立)を仮定した場合の理論値の約1.7倍(超過比1.73)。"
                             "線形相関(ρ=0.192)だけでは捉えきれない、ストレス時の連動性の強さを示唆しており、"
                             "テールシナリオでは前提の相関よりも実際の共倒れリスクが高い可能性がある",
    "scenarios": [
        {
            "label": "7月4日(土・週末で市場閑散)",
            "date": "2026-07-04",
            "usd_jpy_expected": 161.15,
            "usd_jpy_range_90": [161.08, 161.23],
            "jgb_jpy_price_expected": 95.873,
            "jgb_jpy_price_range_90": [95.764, 95.981],
            "usd_value_expected": 59.4926,
            "usd_value_range_90": [59.4152, 59.5699],
            "prob_up_pct": 41.9,
            "note": "土日は現物市場が閉まるため変動をシグナルごと0.2倍に縮小"
                    "(GARCH(1,1)-t×IV反映後の値・データ駆動ν=5.04を使用)",
        },
        {
            "label": "7月6日(月・次の実質取引日)",
            "date": "2026-07-06",
            "usd_jpy_expected": 161.16,
            "usd_jpy_range_90": [160.78, 161.53],
            "jgb_jpy_price_expected": 95.821,
            "jgb_jpy_price_range_90": [95.282, 96.363],
            "usd_value_expected": 59.4592,
            "usd_value_range_90": [59.0724, 59.8475],
            "prob_up_pct": 41.7,
            "note": "週明け最初の実質的な取引日。GARCH(1,1)-tはJGB利回りのボラティリティ・"
                    "クラスタリング(入札不調ショックの持続)を捉えて上振れ予測する一方、"
                    "IVレジーム(MOVE/VIXとも1年平均を下回る)は落ち着いた変動を示唆しており、"
                    "両者の幾何平均で穏当なレンジに。データ駆動の自由度ν(5.04)は従来の固定値5と"
                    "ほぼ同水準で、モデル前提が実測データに整合していたことを確認",
        },
    ],
    "conclusion": "利回り上昇(価格下落)方向のシグナルがやや優勢な一方、ドルは直近続落基調にあり"
                  "FX面はやや円高(ドル建て価値にはむしろ追い風)方向で、両シグナルの効果は一部相殺されます。"
                  "7/6のドル建て価値の上昇確率は約42%(下落確率約58%)とやや下落寄りです。"
                  "GARCH(1,1)-tは直近の入札不調によるJGB利回りのボラティリティ上昇を検知しレンジを"
                  "やや広げる一方、MOVE・VIXの「落ち着いたIVレジーム」はレンジを狭める方向に働き、"
                  "両者を幾何平均でブレンドした結果、純ヒストリカルボラティリティのみの場合と"
                  "おおむね近い水準に落ち着いています。EVT・FHSによるテールリスクのクロスチェックでは"
                  "パラメトリック(t分布)手法との大きな乖離は見られず、現在のモデル前提が概ね妥当と"
                  "判断していますが、利回り×為替のテール依存は線形相関の想定より強い可能性があります。",
    "caveats": [
        "各シグナルの平均・標準偏差は入手可能な定性情報を主観的に定量化したもので、厳密なバックテストは"
        "自動計算モデルのbacktest_var_95でのみ実施(手動シグナルの妥当性検証は未実施)",
        "JGB利回り変化とFX変化の相関(ρ=0.192)は過去60営業日の実測値だが、シグナルごとの相関構造までは"
        "反映していない。また実測テール依存係数(excess_ratio≈1.73)が示す通り、線形相関のみを用いた"
        "モンテカルロは極端な同時悪化シナリオの確率をやや過小評価している可能性がある",
        "為替(USD/JPY)と金利(JGB利回り)を独立に統合後、相関ρのみで結合しており、完全なコピュラモデルではない",
        "IV(インプライドボラティリティ)はJGB・USD/JPY固有のオプション市場データではなく、"
        "無料で取得可能なMOVE指数(米国債IV)・VIX指数(株式IV)を代理指標として使用した近似",
        "GARCH(1,1)-tは分散ターゲティング法・格子探索・反復プロファイル尤度による簡易的なMLE実装であり、"
        "真の同時最尤推定(準ニュートン法等によるα・β・νの同時最適化)による改善余地がある",
        "EVT(極値理論)の閾値は上位10%点に固定しており、閾値選択(Hill plot等によるより厳密な手法)次第で"
        "結果が変わりうる",
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


# --- 汎用スチューデントのt分布: PDF・CDF・分位点関数(追加依存なし) ---
# 自由度ν(裾の太さ)を「5に固定」せずデータから推定するには、任意のνに対応した
# CDF/分位点関数が必要になる。正則不完全ベータ関数を Numerical Recipes 方式の
# 連分数展開(Lentzのアルゴリズム)で計算し、そこからt分布のCDFを厳密に導出する。
def _incomplete_beta_cf(a, b, x):
    max_iter = 200
    eps = 3e-14
    fpmin = 1e-300
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _regularized_incomplete_beta(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    bt = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log(1 - x)
    )
    if x < (a + 1) / (a + b + 2):
        return bt * _incomplete_beta_cf(a, b, x) / a
    return 1.0 - bt * _incomplete_beta_cf(b, a, 1 - x) / b


def t_pdf_standard(x, nu):
    c = math.exp(math.lgamma((nu + 1) / 2) - math.lgamma(nu / 2)) / math.sqrt(nu * math.pi)
    return c * (1 + x * x / nu) ** (-(nu + 1) / 2)


def t_cdf_standard(x, nu):
    """標準(位置0, 尺度1)t分布(自由度nu)の累積分布関数(厳密解, 不完全ベータ関数経由)。"""
    xt = nu / (nu + x * x)
    p = 0.5 * _regularized_incomplete_beta(nu / 2, 0.5, xt)
    return p if x < 0 else 1 - p


def t_quantile_standard(p, nu, lo=-300.0, hi=300.0):
    """標準t分布の分位点関数(CDFの二分探索による数値的逆関数)。"""
    if p <= 0:
        return -math.inf
    if p >= 1:
        return math.inf
    for _ in range(100):
        mid = (lo + hi) / 2
        if t_cdf_standard(mid, nu) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def t_expected_shortfall_multiplier(nu, alpha):
    """標準化t分布(自由度nu)における下側Expected Shortfallの「標準偏差換算の倍率」を返す。
    ES_α = (g_ν(q_α)/α)·(ν+q_α²)/(ν-1) (q_α=下側α分位点, g_ν=標準t分布のPDF)。"""
    if nu <= 1:
        return math.inf
    q = t_quantile_standard(alpha, nu)
    g = t_pdf_standard(q, nu)
    return (g / alpha) * (nu + q * q) / (nu - 1)


# --- 自由度ν(裾の太さ)のデータ駆動推定 ---
# これまでは「自由度5」を固定値として仮定していたが、実際の裾の厚さは市場ごとに異なる。
# GARCHで標準化した残差 z_t = r_t/σ_t (ボラティリティ・クラスタリングを除去した「純粋な
# ショック」)にt分布をあてはめ、νを最尤推定することで、その市場固有の裾の厚さを
# データから直接求める。
def compute_garch_standardized_residuals(returns, omega, alpha, beta):
    long_run_var = statistics.pvariance(returns)
    var_t = long_run_var if long_run_var > 0 else 1e-9
    residuals = []
    for r in returns:
        sigma_t = math.sqrt(var_t) if var_t > 0 else 1e-9
        residuals.append(r / sigma_t)
        var_t = omega + alpha * r * r + beta * var_t
    return residuals


def fit_t_shape(standardized_residuals):
    """位置0のt分布を標準化残差にあてはめ、自由度ν(裾の厚さ)とスケール補正を
    格子探索+局所精緻化によるMLEで推定する。"""
    n = len(standardized_residuals)
    if n < 40:
        return None

    def log_likelihood(sigma, nu):
        if sigma <= 0:
            return -math.inf
        ll = 0.0
        for z in standardized_residuals:
            ll += math.log(t_pdf_standard(z / sigma, nu)) - math.log(sigma)
        return ll

    def grid_search(sigma_range, nu_range, steps):
        best = (-math.inf, None, None)
        for si in range(steps + 1):
            sigma = sigma_range[0] + (sigma_range[1] - sigma_range[0]) * si / steps
            for ni in range(steps + 1):
                nu = nu_range[0] + (nu_range[1] - nu_range[0]) * ni / steps
                ll = log_likelihood(sigma, nu)
                if ll > best[0]:
                    best = (ll, sigma, nu)
        return best

    best_ll, best_sigma, best_nu = grid_search((0.6, 1.6), (2.2, 40.0), 24)
    if best_sigma is None:
        return None
    span_s, span_n = 0.25, 6.0
    for _ in range(2):
        best_ll, best_sigma, best_nu = grid_search(
            (max(0.3, best_sigma - span_s), best_sigma + span_s),
            (max(2.05, best_nu - span_n), best_nu + span_n),
            16,
        )
        span_s /= 3.0
        span_n /= 3.0

    return {
        "nu": round(best_nu, 2),
        "scale": round(best_sigma, 4),
        "log_likelihood": round(best_ll, 3),
        "n_obs": n,
    }


# --- GARCH(1,1) ボラティリティモデル(分散ターゲティング法によるMLE, 追加依存なし) ---
# 単純な過去N日の実測標準偏差は「窓内は等ウェイト、窓外は無視」という単純な仮定だが、
# GARCH(1,1)はボラティリティ・クラスタリング(荒れた相場の後は荒れが続きやすい)を
# σ²_t = ω + α·r²_{t-1} + β·σ²_{t-1} という自己回帰構造で捉える。
# ここでは Engle–Mezrich (1996) の分散ターゲティング法を用い、ω = 長期分散·(1-α-β) と
# 置くことで探索パラメータを(α, β)の2次元に削減し、格子探索+局所精緻化で最尤推定する
# (scipy等の数値最適化ライブラリへの依存を避けるため)。
# nuを指定すると、正規分布の代わりに自由度nuのt分布を尤度関数に用いる
# (Bollerslev(1987)のGARCH-tモデル。金融リターンの過剰尖度をボラティリティ推定自体にも反映)。
def fit_garch11(returns, nu=None):
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
            if nu is None:
                ll += -0.5 * (math.log(2 * math.pi) + math.log(var_t) + (r * r) / var_t)
            else:
                sigma_t = math.sqrt(var_t)
                ll += math.log(t_pdf_standard(r / sigma_t, nu)) - math.log(sigma_t)
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
        "nu": nu,
    }


def fit_garch11_t(returns):
    """GARCH(1,1)パラメータ(α,β)と自由度ν(裾の厚さ)を反復プロファイル尤度で
    同時推定する。(1)正規尤度でGARCHを粗く推定→(2)標準化残差からνをMLE推定→
    (3)推定したνでt分布尤度によりGARCHを再推定、を数回繰り返すことで、
    (α,β,ν)の3次元同時最適化を避けつつBollerslev(1987)のGARCH-tに近い解に収束させる。"""
    fit = fit_garch11(returns, nu=None)
    if fit is None:
        return None
    shape_info = None
    for _ in range(3):
        resid = compute_garch_standardized_residuals(returns, fit["omega"], fit["alpha"], fit["beta"])
        new_shape = fit_t_shape(resid)
        if new_shape is None:
            break
        if shape_info and abs(new_shape["nu"] - shape_info["nu"]) < 0.05:
            shape_info = new_shape
            break
        shape_info = new_shape
        refit = fit_garch11(returns, nu=shape_info["nu"])
        if refit is None:
            break
        fit = refit
    if shape_info:
        fit["nu"] = shape_info["nu"]
        fit["shape_fit"] = shape_info
    final_residuals = compute_garch_standardized_residuals(returns, fit["omega"], fit["alpha"], fit["beta"])
    fit["_standardized_residuals"] = final_residuals
    return fit


# --- 極値理論(Extreme Value Theory): Peak-Over-Threshold法 + 一般化パレート分布(GPD) ---
# t分布は「分布全体」の形状を単一のνで近似するが、Pickands–Balkema–de Haanの定理により、
# 「十分高い閾値を超えた超過量」の分布は(元の分布によらず漸近的に)一般化パレート分布に
# 従うことが知られている。分布全体ではなく裾そのものを直接モデル化することで、
# t分布による近似が持つ「裾の中央部分に引きずられる」バイアスを避けられる。
def fit_gpd(exceedances):
    """一般化パレート分布(GPD)を閾値超過量にMLE(格子探索+精緻化)であてはめる。
    形状パラメータxi(xi>0で裾が厚い)とスケールパラメータbetaを推定する。"""
    n = len(exceedances)
    if n < 20:
        return None
    mean_exc = statistics.mean(exceedances)
    if mean_exc <= 0:
        return None

    def log_likelihood(xi, beta):
        if beta <= 0:
            return -math.inf
        ll = 0.0
        for y in exceedances:
            z = 1 + xi * y / beta
            if z <= 1e-9:
                return -math.inf
            if abs(xi) < 1e-8:
                ll += -math.log(beta) - y / beta
            else:
                ll += -math.log(beta) - (1 / xi + 1) * math.log(z)
        return ll

    def grid_search(xi_range, beta_range, steps):
        best = (-math.inf, None, None)
        for xi_i in range(steps + 1):
            xi = xi_range[0] + (xi_range[1] - xi_range[0]) * xi_i / steps
            for b_i in range(steps + 1):
                beta = beta_range[0] + (beta_range[1] - beta_range[0]) * b_i / steps
                ll = log_likelihood(xi, beta)
                if ll > best[0]:
                    best = (ll, xi, beta)
        return best

    best_ll, best_xi, best_beta = grid_search((-0.4, 0.7), (mean_exc * 0.2, mean_exc * 3.0), 22)
    if best_xi is None:
        return None
    span_xi, span_beta = 0.15, mean_exc * 0.6
    for _ in range(2):
        best_ll, best_xi, best_beta = grid_search(
            (best_xi - span_xi, best_xi + span_xi),
            (max(1e-6, best_beta - span_beta), best_beta + span_beta),
            16,
        )
        span_xi /= 3.0
        span_beta /= 3.0

    return {
        "xi": round(best_xi, 4),
        "beta": round(best_beta, 6),
        "log_likelihood": round(best_ll, 3),
        "n_exceedances": n,
    }


def evt_tail_risk(loss_series, threshold_quantile=0.90, target_p=0.95):
    """Peak-Over-Threshold法(POT)による極値理論のテールリスク推定。
    loss_seriesは「損失が正の値になる」よう符号を揃えた系列を渡す。"""
    n = len(loss_series)
    if n < 80:
        return None
    sorted_losses = sorted(loss_series)
    idx = min(n - 1, max(0, int(n * threshold_quantile)))
    threshold = sorted_losses[idx]
    exceedances = [x - threshold for x in loss_series if x > threshold]
    n_exc = len(exceedances)
    if n_exc < 20:
        return None
    gpd = fit_gpd(exceedances)
    if gpd is None:
        return None
    xi, beta = gpd["xi"], gpd["beta"]
    p_exceed = n_exc / n
    q = 1 - target_p
    if q >= p_exceed:
        var = threshold
    elif abs(xi) > 1e-6:
        var = threshold + (beta / xi) * ((q / p_exceed) ** (-xi) - 1)
    else:
        var = threshold - beta * math.log(q / p_exceed)

    es = None
    if xi < 1:
        es = (var + beta - xi * threshold) / (1 - xi) if abs(xi) > 1e-6 else var + beta

    return {
        "threshold": round(threshold, 6),
        "threshold_quantile": threshold_quantile,
        "xi": xi,
        "beta": beta,
        "n_exceedances": n_exc,
        "n_obs": n,
        "target_p": target_p,
        "var": var,
        "es": es,
    }


def fhs_tail_es(standardized_residuals, forecast_vol, alpha=0.05):
    """Filtered Historical Simulation(FHS): GARCHで標準化した実測残差の経験分布を
    (正規分布やt分布のような分布形状の仮定を一切置かずに)そのまま使い、翌日の予測
    ボラティリティでスケールしてExpected Shortfallをノンパラメトリックに求める。"""
    n = len(standardized_residuals)
    if n < 40:
        return None
    sorted_z = sorted(standardized_residuals)
    cutoff_idx = max(1, int(round(n * alpha)))
    tail = sorted_z[:cutoff_idx]
    es_z = statistics.mean(tail)
    return {
        "es_z": round(es_z, 4),
        "n_tail_obs": cutoff_idx,
        "n_obs": n,
        "es_scaled": es_z * forecast_vol,
    }


def kupiec_pof_test(n_obs, n_breaches, expected_rate):
    """Kupiec(1995)の比率的中検定(Proportion of Failures test)。
    「VaR超過が想定通りの頻度で起きているか」を尤度比検定で評価する
    (バーゼル規制のVaRモデル検証で標準的に用いられる手法)。"""
    if n_obs == 0:
        return None
    observed_rate = n_breaches / n_obs
    if n_breaches == 0:
        ll_null = n_obs * math.log(1 - expected_rate)
        ll_alt = 0.0
    elif n_breaches == n_obs:
        ll_null = n_obs * math.log(expected_rate)
        ll_alt = 0.0
    else:
        ll_null = n_breaches * math.log(expected_rate) + (n_obs - n_breaches) * math.log(1 - expected_rate)
        ll_alt = n_breaches * math.log(observed_rate) + (n_obs - n_breaches) * math.log(1 - observed_rate)
    lr_stat = -2 * (ll_null - ll_alt)
    # 自由度1のカイ二乗分布の生存確率 P(chi2_1 > x) = erfc(sqrt(x/2))
    p_value = math.erfc(math.sqrt(max(lr_stat, 0) / 2))
    return {
        "n_obs": n_obs,
        "n_breaches": n_breaches,
        "observed_rate": round(observed_rate, 4),
        "expected_rate": expected_rate,
        "lr_statistic": round(lr_stat, 3),
        "p_value": round(p_value, 4),
        "reject_at_5pct": p_value < 0.05,
    }


def backtest_var(log_returns, window=60, confidence=0.95, nu=5.0):
    """過去データに対するローリングVaRのバックテスト。各日、直前window日間の
    実測ボラティリティからt分布ベースのVaRを計算し、翌日の実際のリターンがそれを
    下回った(=損失がVaRを超過した)回数を数え、期待超過率とKupiec検定で比較する。"""
    n = len(log_returns)
    if n < window + 30:
        return None
    alpha = 1 - confidence
    q_mult = t_quantile_standard(alpha, nu)  # 負値
    breaches = 0
    count = 0
    for i in range(window, n):
        hist = log_returns[i - window:i]
        sigma = statistics.pstdev(hist)
        mu = statistics.mean(hist)
        var_threshold = mu + q_mult * sigma
        count += 1
        if log_returns[i] < var_threshold:
            breaches += 1
    kupiec = kupiec_pof_test(count, breaches, alpha)
    return {
        "method": "simplified_rolling_std",
        "window": window,
        "confidence": confidence,
        "nu_used": nu,
        "n_tested": count,
        "n_breaches": breaches,
        "kupiec": kupiec,
        "note": "直近window日間の単純な実測標準偏差のみでVaRを計算する簡易版バックテスト。"
                "自由度νは全期間データから推定した最終値を遡及適用しているため、軽微な"
                "先読みバイアスがある(超過の時間的な偏りはChristoffersen検定を含む"
                "full_backtestで別途検証)",
    }


def christoffersen_independence_test(breach_flags):
    """Christoffersen(1998)の独立性検定。VaR超過(breach)を2状態マルコフ連鎖と見なし、
    「超過が起きた翌日にまた超過が起きる確率」が「超過が起きなかった翌日に超過が起きる
    確率」と統計的に同じか(=超過が時間的に偏りなく独立に発生しているか)を尤度比検定で
    評価する。Kupiec検定は「頻度」しか見ないため、超過が特定の期間に固まって発生する
    (モデルの反応が遅れている等の)問題を検出できない弱点を補う。"""
    n = len(breach_flags)
    if n < 30:
        return None

    def safe_log(x):
        return math.log(x) if x > 0 else 0.0

    n00 = n01 = n10 = n11 = 0
    for i in range(1, n):
        prev, cur = breach_flags[i - 1], breach_flags[i]
        if not prev and not cur:
            n00 += 1
        elif not prev and cur:
            n01 += 1
        elif prev and not cur:
            n10 += 1
        else:
            n11 += 1

    n0_total = n00 + n01
    n1_total = n10 + n11
    if n0_total == 0 or n1_total == 0:
        return None

    pi01 = n01 / n0_total
    pi11 = n11 / n1_total
    pi = (n01 + n11) / (n00 + n01 + n10 + n11)

    ll_null = (n00 + n10) * safe_log(1 - pi) + (n01 + n11) * safe_log(pi)
    ll_alt = (
        n00 * safe_log(1 - pi01) + n01 * safe_log(pi01)
        + n10 * safe_log(1 - pi11) + n11 * safe_log(pi11)
    )
    lr_stat = -2 * (ll_null - ll_alt)
    p_value = math.erfc(math.sqrt(max(lr_stat, 0) / 2))
    return {
        "n00": n00, "n01": n01, "n10": n10, "n11": n11,
        "prob_breach_after_no_breach": round(pi01, 4),
        "prob_breach_after_breach": round(pi11, 4),
        "lr_statistic": round(lr_stat, 3),
        "p_value": round(p_value, 4),
        "reject_at_5pct": p_value < 0.05,
    }


def walk_forward_full_backtest(returns, min_train=150, refit_freq=21, confidence=0.95):
    """フルバックテスト: 「その時点で実際に得られていたデータのみ」を使ってGARCH(1,1)-t
    (α・β・自由度ν)を一定間隔(refit_freq営業日=約1ヵ月ごと)で再推定し、再推定の合間は
    GARCHの分散再帰式(σ²_t=ω+α・r²_{t-1}+β・σ²_{t-1})で条件付き分散を日次更新しながら、
    毎日その時点のσ_t・ν_tからVaR・ESを計算して実際のリターンと比較する。

    簡易版(backtest_var: 直前window日の単純標準偏差+全期間データで推定した自由度νを
    遡及適用)と異なり、パラメータ推定に「将来のデータ」を一切使わない(先読みバイアスなし)。
    Kupiec検定(超過頻度)に加え、Christoffersen独立性検定(超過の時間的な偏り)・両者を
    統合した条件付きカバレッジ検定・ESの妥当性検証(超過日の実測損失平均とモデル予測ESの比較)
    も行う、より厳密なモデル検証。"""
    n = len(returns)
    if n < min_train + 60:
        return None
    alpha_level = 1 - confidence

    breach_flags = []
    var_thresholds = []
    es_thresholds = []
    actuals = []
    n_refits = 0

    fit = None
    var_t = None
    next_refit_idx = min_train

    for t in range(min_train, n):
        if fit is None or t >= next_refit_idx:
            train_data = returns[:t]  # t日目より前のデータのみを使用(先読みなし)
            new_fit = fit_garch11_t(train_data)
            if new_fit:
                fit = new_fit
                long_run_var = fit["omega"] / max(1e-9, 1 - fit["alpha"] - fit["beta"])
                var_t = long_run_var
                n_refits += 1
            next_refit_idx = t + refit_freq
        if fit is None or var_t is None or var_t <= 0:
            continue

        sigma_t = math.sqrt(var_t)
        nu_t = fit.get("nu") or 5.0
        q_mult = t_quantile_standard(alpha_level, nu_t)  # 負値
        es_mult = t_expected_shortfall_multiplier(nu_t, alpha_level)
        var_threshold = q_mult * sigma_t
        es_threshold = -es_mult * sigma_t

        r = returns[t]
        breach_flags.append(r < var_threshold)
        var_thresholds.append(var_threshold)
        es_thresholds.append(es_threshold)
        actuals.append(r)

        # 観測したリターンを使って分散再帰式を1期進める(翌日以降の予測に反映)
        var_t = fit["omega"] + fit["alpha"] * r * r + fit["beta"] * var_t

    n_tested = len(breach_flags)
    n_breaches = sum(1 for b in breach_flags if b)
    if n_tested == 0:
        return None

    kupiec = kupiec_pof_test(n_tested, n_breaches, alpha_level)
    independence = christoffersen_independence_test(breach_flags)
    conditional_coverage = None
    if kupiec and independence:
        lr_cc = kupiec["lr_statistic"] + independence["lr_statistic"]
        p_cc = math.exp(-max(lr_cc, 0) / 2)  # 自由度2のカイ二乗分布の生存確率(=指数分布)
        conditional_coverage = {
            "lr_statistic": round(lr_cc, 3),
            "p_value": round(p_cc, 4),
            "reject_at_5pct": p_cc < 0.05,
        }

    breach_indices = [i for i, b in enumerate(breach_flags) if b]
    es_backtest = None
    if breach_indices:
        avg_realized_loss = -statistics.mean(actuals[i] for i in breach_indices)
        avg_predicted_es = -statistics.mean(es_thresholds[i] for i in breach_indices)
        es_backtest = {
            "n_breach_days": len(breach_indices),
            "avg_realized_loss": round(avg_realized_loss, 6),
            "avg_predicted_es": round(avg_predicted_es, 6),
            "ratio": round(avg_realized_loss / avg_predicted_es, 3) if avg_predicted_es else None,
            "note": "VaR超過が発生した日に限定した、実際の損失の平均とモデルが予測したExpected "
                    "Shortfallの平均の比較(McNeil–Frey(2000)型のES検証)。比率が1に近いほど、"
                    "「最悪シナリオの深刻さ」の推定が実際の悪化度合いと整合していることを示す",
        }

    return {
        "method": "walk_forward_garch_t",
        "min_train": min_train,
        "refit_freq": refit_freq,
        "n_refits": n_refits,
        "confidence": confidence,
        "n_tested": n_tested,
        "n_breaches": n_breaches,
        "kupiec": kupiec,
        "independence": independence,
        "conditional_coverage": conditional_coverage,
        "es_backtest": es_backtest,
        "note": "先読みバイアスを排除したウォークフォワード検証: 各時点で入手可能だったデータのみを"
                f"使い、約{refit_freq}営業日ごとにGARCH(1,1)-tを再推定(初回は直近{min_train}営業日で学習)。"
                "Kupiec検定(頻度)・Christoffersen独立性検定(超過の時間的偏り)・両者を統合した"
                "条件付きカバレッジ検定・ESの妥当性検証まで実施した厳密版バックテスト",
    }


def empirical_tail_dependence(x_series, y_series, q=0.10):
    """利回り変化とドル円変化が「同時に国債USD建て価値にとって悪い方向」に大きく
    動く経験的な同時確率(下側/上側テール依存)を求める。正規分布(ガウス型コピュラ)を
    仮定した相関だけでは、暴落局面での連動性の強さ(テール依存)を過小評価しうるため、
    実測データで直接検証する。x, yは共に「値が大きいほど国債USD建て価値にとって
    悪い」方向に符号を揃えて渡す(本アプリではyield_chg_bp, fx_chg_pctがそのまま該当)。"""
    n = len(x_series)
    if n < 60:
        return None
    sorted_x = sorted(x_series)
    sorted_y = sorted(y_series)
    idx = min(n - 1, max(0, int(round(n * (1 - q))) - 1))
    x_thresh = sorted_x[idx]
    y_thresh = sorted_y[idx]
    joint_count = sum(1 for xv, yv in zip(x_series, y_series) if xv >= x_thresh and yv >= y_thresh)
    empirical_prob = joint_count / n
    independence_baseline = q * q
    return {
        "q": q,
        "empirical_joint_prob": round(empirical_prob, 4),
        "independence_baseline": round(independence_baseline, 4),
        "excess_ratio": round(empirical_prob / independence_baseline, 3) if independence_baseline > 0 else None,
        "n_obs": n,
    }


def _strip_internal_keys(d: dict | None) -> dict | None:
    """内部計算専用のキー(標準化残差の生配列など、JSON出力には不要で肥大化を招くもの)を
    取り除いたコピーを返す。"""
    if d is None:
        return None
    return {k: v for k, v in d.items() if not k.startswith("_")}


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

    garch_yield = fit_garch11_t(ext_yield_chg_bp)
    garch_fx = fit_garch11_t(ext_fx_chg_pct)

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
    # d ln(USD建て価値) ≈ -修正デュレーション×Δ利回り(bp)/10000 - ΔFX(%)/100 の分散から近似
    c1 = mod_duration / 10000.0
    c2 = 1.0 / 100.0
    var_ln = (c1 ** 2) * (yield_vol_bp ** 2) + (c2 ** 2) * (fx_vol_pct ** 2) \
        + 2 * c1 * c2 * correlation * yield_vol_bp * fx_vol_pct
    std_ln_linear = math.sqrt(var_ln)

    # --- ドル建て価値そのもの(利回り×為替の合成リスク)への直接GARCH-tモデル ---
    # 上記は「修正デュレーション×利回り変化 + 為替変化」という1次近似(線形合成)によって
    # 利回り・為替それぞれのボラティリティからUSD建て価値の分散を再構成したものだが、
    # ここでは実際の日次ドル建て価値の変化率そのものにGARCH(1,1)-tを直接あてはめ、
    # 独立したクロスチェックとしての予測ボラティリティ・自由度ν・標準化残差を得る。
    ext_usd_values = [
        bond_dcf_price(yv, JGB_BOND_COUPON_RATE,
                        (JGB_BOND_MATURITY - date.fromisoformat(d)).days / 365.25)[0] / fxv
        for d, yv, fxv in zip(extended_dates, ext_yield_vals, ext_fx_vals)
    ]
    ext_usd_value_log_ret = [math.log(ext_usd_values[i] / ext_usd_values[i - 1]) for i in range(1, len(ext_usd_values))]
    garch_direct = fit_garch11_t(ext_usd_value_log_ret)

    # 自由度ν(裾の厚さ)は、これまでの「固定値5」ではなく、上記の直接モデルからデータ駆動で
    # 推定する。取得に失敗した場合は利回り・為替それぞれの推定値の分散加重平均、
    # さらにそれも無ければ保守的な既定値5にフォールバックする。
    if garch_direct and garch_direct.get("nu"):
        estimated_nu = garch_direct["nu"]
        nu_source = "usd_value_direct_garch_t"
    else:
        nu_y = garch_yield.get("nu") if garch_yield else None
        nu_f = garch_fx.get("nu") if garch_fx else None
        candidates = [v for v in (nu_y, nu_f) if v]
        estimated_nu = round(statistics.mean(candidates), 2) if candidates else 5.0
        nu_source = "yield_fx_average" if candidates else "fallback_default"

    std_ln_direct = garch_direct["forecast_vol"] if garch_direct else None
    # 線形合成モデル(デュレーション近似)と直接モデル(実測USD建て価値の時系列)の
    # 幾何平均で最終的な標準偏差を求め、モデル構造の異なる2つの推定を頑健にブレンドする。
    std_ln = math.sqrt(std_ln_linear * std_ln_direct) if std_ln_direct else std_ln_linear

    range_q = t_quantile_standard(0.95, estimated_nu)  # 90%区間の上側5%点(自由度ν、正の値)
    range_90_low = round(usd_value_iv_adjusted * math.exp(-range_q * std_ln), 4)
    range_90_high = round(usd_value_iv_adjusted * math.exp(range_q * std_ln), 4)

    # --- Expected Shortfall: 3手法によるアンサンブル ---
    # (1) パラメトリック: データ駆動で推定した自由度νのt分布による解析解
    # (2) EVT(POT+GPD): 分布全体でなく裾そのものを極値理論で直接モデル化
    # (3) FHS(Filtered Historical Simulation): 分布形状を一切仮定せず、GARCH標準化残差の
    #     実測経験分布をそのまま用いるノンパラメトリック手法
    # 手法によって前提が異なるため、3つのうち最も保守的(=価格が最も下がる)値を採用しつつ、
    # 全ての結果を透明性のため併記する。
    es_mult_param = t_expected_shortfall_multiplier(estimated_nu, 0.05)
    es_param_low = usd_value_iv_adjusted * math.exp(-es_mult_param * std_ln)

    evt_loss_series = [-r for r in ext_usd_value_log_ret]  # 価値の下落(損失)を正の値にする
    evt_result = evt_tail_risk(evt_loss_series, threshold_quantile=0.90, target_p=0.95)
    es_evt_low = usd_value_iv_adjusted * math.exp(-evt_result["es"]) if evt_result and evt_result.get("es") else None

    fhs_result = None
    es_fhs_low = None
    if garch_direct and garch_direct.get("_standardized_residuals"):
        fhs_result = fhs_tail_es(garch_direct["_standardized_residuals"], std_ln, alpha=0.05)
        if fhs_result:
            es_fhs_low = usd_value_iv_adjusted * math.exp(fhs_result["es_scaled"])

    es_candidates = {"parametric_t": es_param_low, "evt_gpd": es_evt_low, "fhs": es_fhs_low}
    valid_es = {k: v for k, v in es_candidates.items() if v is not None}
    ensemble_es_low = round(min(valid_es.values()), 4) if valid_es else round(es_param_low, 4)
    ensemble_es_method = min(valid_es, key=valid_es.get) if valid_es else "parametric_t"

    # --- バックテスト: ローリングVaR超過率のKupiec比率的中検定(簡易版) ---
    # 直近window日間の実測ボラティリティ(モデルの単純化版)から日々VaRを計算し、
    # 実際の超過頻度が理論値(1-confidence)と統計的に整合しているかを検証する。
    # 自由度νは全期間データから推定した最終値を遡及適用しているため、軽微な先読み
    # バイアスがある(下のfull_backtestはこれを排除したより厳密な検証)。
    backtest_result = backtest_var(ext_usd_value_log_ret, window=60, confidence=0.95, nu=estimated_nu)

    # --- フルバックテスト: ウォークフォワード方式による厳密な検証 ---
    # 各時点で実際に入手可能だったデータのみを使ってGARCH(1,1)-tを定期的に再推定し、
    # 先読みバイアスを排除。Kupiec検定に加えChristoffersen独立性検定・条件付きカバレッジ・
    # ESの妥当性検証まで行う(詳細はwalk_forward_full_backtestのdocstring参照)。
    full_backtest_result = walk_forward_full_backtest(
        ext_usd_value_log_ret, min_train=150, refit_freq=21, confidence=0.95
    )

    # --- テール依存構造の実測診断(コピュラの簡易代替) ---
    # 線形相関(ピアソン相関)だけでは「同時に大きく悪化する」確率を過小評価しうるため、
    # 利回り上昇と円安(共にUSD建て価値にとって悪材料)が同時に極端な水準となる
    # 経験的な同時確率を、正規分布(独立)を仮定した場合の理論値と比較する。
    tail_dependence = empirical_tail_dependence(ext_yield_chg_bp, ext_fx_chg_pct, q=0.10)

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
            "jgb_yield": _strip_internal_keys(garch_yield),
            "usd_jpy": _strip_internal_keys(garch_fx),
            "usd_value_direct": _strip_internal_keys(garch_direct),
            "note": "GARCH(1,1)-t(分散ターゲティング法によるMLE, 格子探索+反復プロファイル尤度で"
                    "自由度νも同時推定)による翌営業日の予測ボラティリティ。過去60営業日の等ウェイト"
                    "実測値と異なり、ボラティリティ・クラスタリング(荒れ相場の後は荒れが続きやすい性質)を"
                    "反映できる。usd_value_directは利回り・為替を合成せず、USD建て価値の日次変化率"
                    "そのものに直接あてはめたクロスチェック用モデル。最終的な採用ボラティリティ"
                    "(jgb_yield_daily_vol_bp等)はIV反映値との幾何平均",
        },
        "degrees_of_freedom": {
            "estimated_nu": estimated_nu,
            "source": nu_source,
            "note": "テール(裾)の厚さを表すt分布の自由度ν。従来は「5」に固定していたが、"
                    "GARCH標準化残差(ボラティリティ・クラスタリングを除去した純粋なショック)に"
                    "t分布をMLEであてはめることでデータから直接推定する。νが小さいほど裾が厚い"
                    "(極端な変動が起きやすい)ことを意味する",
        },
        "statistical_range_90": {
            "low": range_90_low,
            "high": range_90_high,
            "note": "IV反映後の現在価値推定(usd_value_iv_adjusted)を中心に、過去60営業日の実測ボラティリティ・"
                    "MOVE/VIXのIVレジーム比・GARCH(1,1)-t予測ボラティリティ(線形合成モデルと"
                    "USD建て価値直接モデルの幾何平均)・データ駆動の自由度νを組み合わせた統計的な"
                    "変動レンジ(個別の材料の方向感は含まない)",
        },
        "expected_shortfall_95": {
            "low": ensemble_es_low,
            "method": ensemble_es_method,
            "components": {
                "parametric_t": round(es_param_low, 4) if es_param_low else None,
                "evt_gpd": round(es_evt_low, 4) if es_evt_low else None,
                "fhs": round(es_fhs_low, 4) if es_fhs_low else None,
            },
            "note": "下側Expected Shortfall(CVaR, 95%): 起こりうる最悪5%のシナリオに限定した場合の"
                    "期待値。前提の異なる3手法「パラメトリック(データ駆動の自由度νのt分布解析解)」"
                    "「EVT(極値理論, POT+一般化パレート分布による裾そのものの直接推定)」"
                    "「FHS(Filtered Historical Simulation, 分布形状を仮定しないノンパラメトリック"
                    "手法)」を算出し、最も保守的(価格が最も下がる)な値を採用したアンサンブル。"
                    "VaR(90%区間の下限)より厳しい、テールリスクを織り込んだ指標"
                    "(Basel III/FRTBで採用されている手法)",
        },
        "evt_tail_risk": evt_result,
        "filtered_historical_simulation": fhs_result,
        "backtest_var_95": backtest_result,
        "full_backtest": full_backtest_result,
        "yield_fx_tail_dependence": tail_dependence,
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
