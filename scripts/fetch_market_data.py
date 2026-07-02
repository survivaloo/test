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
import sys
import urllib.request
from datetime import datetime, timezone

JGB_CSV_URL = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv"
BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/LNS14000000"
OUTPUT_PATH = "web/usdjpy-rate/market-data.json"

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
