#!/usr/bin/env python3
"""
Raspberry Pi AI HAT+ 2 在庫確認アプリ（日本国内ショップ特化版）
Amazon.co.jp + 国内主要電子部品ショップの在庫状況をチェックします。
"""

import requests
from bs4 import BeautifulSoup
import re
import sys
import time
import json
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional


@dataclass
class StockResult:
    shop: str
    url: str
    status: str  # "在庫あり", "在庫なし", "確認不可"
    price: Optional[str] = None
    note: Optional[str] = None


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

SHOPS = [
    # --- Amazon.co.jp ---
    {
        "shop": "Amazon.co.jp (AI HAT+ 2 / 40TOPS)",
        "url": "https://www.amazon.co.jp/dp/B0GK251MF3",
        "checker": "amazon_jp",
    },
    {
        "shop": "Amazon.co.jp (AI HAT+ 26TOPS)",
        "url": "https://www.amazon.co.jp/dp/B0DPLR3RPQ",
        "checker": "amazon_jp",
        "note_extra": "旧モデル",
    },
    {
        "shop": "Amazon.co.jp (AI HAT+ 13TOPS)",
        "url": "https://www.amazon.co.jp/dp/B0DPLQ9TB9",
        "checker": "amazon_jp",
        "note_extra": "旧モデル",
    },
    # --- 国内専門店 ---
    {
        "shop": "スイッチサイエンス",
        "url": "https://www.switch-science.com/products/10916",
        "checker": "switch_science",
    },
    {
        "shop": "KSY (公式代理店)",
        "url": "https://raspberry-pi.ksyic.com/main/index/pdp.id/1257/pdp.open/1257",
        "checker": "ksy",
    },
    {
        "shop": "秋月電子通商",
        "url": "https://akizukidenshi.com/catalog/g/g131618/",
        "checker": "akizuki",
    },
    {
        "shop": "マルツ",
        "url": "https://www.marutsu.co.jp/pc/i/50354161/",
        "checker": "marutsu",
    },
    {
        "shop": "千石電商",
        "url": "https://www.sengoku.co.jp/mod/sgk_cart/search.php?cid=&mcid=&search=AI+HAT%2B+2&x=0&y=0",
        "checker": "sengoku",
    },
]


def fetch_page(url: str, timeout: int = 15) -> Optional[BeautifulSoup]:
    """URLからページを取得してBeautifulSoupオブジェクトを返す"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception:
        return None


def check_amazon_jp(shop_info: dict) -> StockResult:
    """Amazon.co.jp の在庫確認"""
    soup = fetch_page(shop_info["url"])
    if not soup:
        return StockResult(shop_info["shop"], shop_info["url"], "確認不可",
                           note="ページ取得失敗 (Bot検出の可能性)")

    text = soup.get_text(" ", strip=True)

    price = None
    price_el = soup.select_one(
        "#priceblock_ourprice, #priceblock_dealprice, "
        ".a-price .a-offscreen, #corePrice_feature_div .a-offscreen, "
        "#tp_price_block_total_price_ww .a-offscreen"
    )
    if price_el:
        price = price_el.get_text(strip=True)

    note_extra = shop_info.get("note_extra", "")

    if "在庫あり" in text or "在庫残り" in text:
        return StockResult(shop_info["shop"], shop_info["url"], "在庫あり",
                           price=price, note=note_extra or None)
    elif "現在在庫切れ" in text or "この商品は現在お取り扱いできません" in text:
        return StockResult(shop_info["shop"], shop_info["url"], "在庫なし",
                           price=price, note=note_extra or None)
    elif "カートに入れる" in text:
        return StockResult(shop_info["shop"], shop_info["url"], "在庫あり（カート可）",
                           price=price, note=note_extra or None)
    else:
        return StockResult(shop_info["shop"], shop_info["url"], "確認不可",
                           price=price, note=note_extra + " / 在庫表示を検出できず" if note_extra else "在庫表示を検出できず")


def check_generic_jp(shop_info: dict, in_stock_patterns: list, out_of_stock_patterns: list,
                      price_selector: Optional[str] = None) -> StockResult:
    """汎用的な日本ショップ在庫チェッカー"""
    soup = fetch_page(shop_info["url"])
    if not soup:
        return StockResult(shop_info["shop"], shop_info["url"], "確認不可",
                           note="ページ取得失敗")

    text = soup.get_text(" ", strip=True)
    text_lower = text.lower()

    price = None
    if price_selector:
        price_el = soup.select_one(price_selector)
        if price_el:
            price = price_el.get_text(strip=True)

    # 価格がない場合、テキストから抽出を試みる
    if not price:
        price_match = re.search(r'[¥￥][\d,]+', text)
        if not price_match:
            price_match = re.search(r'(\d{1,3}(?:,\d{3})+)\s*円', text)
        if price_match:
            price = price_match.group(0)

    for pattern in out_of_stock_patterns:
        if pattern.lower() in text_lower:
            return StockResult(shop_info["shop"], shop_info["url"], "在庫なし", price=price)

    for pattern in in_stock_patterns:
        if pattern.lower() in text_lower:
            return StockResult(shop_info["shop"], shop_info["url"], "在庫あり", price=price)

    return StockResult(shop_info["shop"], shop_info["url"], "確認不可",
                       price=price, note="在庫表示を検出できず")


def check_switch_science(shop_info: dict) -> StockResult:
    return check_generic_jp(
        shop_info,
        in_stock_patterns=["カートに入れる", "在庫あり", "add to cart"],
        out_of_stock_patterns=["sold out", "在庫切れ", "入荷待ち", "入荷についてはお問い合わせ"],
        price_selector=".product-price, .price",
    )


def check_ksy(shop_info: dict) -> StockResult:
    return check_generic_jp(
        shop_info,
        in_stock_patterns=["カートに入れる", "add to cart", "在庫あり", "buy now", "カートに追加"],
        out_of_stock_patterns=["sold out", "在庫切れ", "品切れ", "入荷未定", "在庫なし"],
    )


def check_akizuki(shop_info: dict) -> StockResult:
    return check_generic_jp(
        shop_info,
        in_stock_patterns=["カートに入れる", "在庫あり", "在庫数"],
        out_of_stock_patterns=["在庫切れ", "品切れ", "sold out", "入荷未定", "メンテナンス中"],
    )


def check_marutsu(shop_info: dict) -> StockResult:
    soup = fetch_page(shop_info["url"])
    if not soup:
        return StockResult(shop_info["shop"], shop_info["url"], "確認不可",
                           note="ページ取得失敗")

    text = soup.get_text(" ", strip=True)

    price = None
    price_match = re.search(r'[¥￥][\d,]+', text)
    if not price_match:
        price_match = re.search(r'(\d{1,3}(?:,\d{3})+)\s*円', text)
    if price_match:
        price = price_match.group(0)

    # マルツの在庫数を確認
    stock_match = re.search(r'在庫数[：:\s]*(\d+)', text)
    if stock_match:
        stock_num = int(stock_match.group(1))
        if stock_num > 0:
            return StockResult(shop_info["shop"], shop_info["url"], "在庫あり",
                               price=price, note=f"在庫数: {stock_num}")
        else:
            # 納期を探す
            lead_match = re.search(r'納期[：:\s]*([\d]+\s*週間)', text)
            lead_time = lead_match.group(1) if lead_match else None
            return StockResult(shop_info["shop"], shop_info["url"], "在庫なし",
                               price=price, note=f"納期: {lead_time}" if lead_time else None)

    if "在庫切れ" in text or "品切れ" in text:
        return StockResult(shop_info["shop"], shop_info["url"], "在庫なし", price=price)
    elif "カートに入れる" in text:
        return StockResult(shop_info["shop"], shop_info["url"], "在庫あり", price=price)

    return StockResult(shop_info["shop"], shop_info["url"], "確認不可",
                       price=price, note="在庫表示を検出できず")


def check_sengoku(shop_info: dict) -> StockResult:
    return check_generic_jp(
        shop_info,
        in_stock_patterns=["カートに入れる", "在庫あり", "add to cart"],
        out_of_stock_patterns=["在庫切れ", "品切れ", "sold out", "該当する商品がありません"],
    )


CHECKER_MAP = {
    "amazon_jp": check_amazon_jp,
    "switch_science": check_switch_science,
    "ksy": check_ksy,
    "akizuki": check_akizuki,
    "marutsu": check_marutsu,
    "sengoku": check_sengoku,
}


def check_shop(shop_info: dict) -> StockResult:
    checker = CHECKER_MAP.get(shop_info["checker"])
    if not checker:
        return StockResult(shop_info["shop"], shop_info["url"], "確認不可",
                           note="チェッカー未実装")
    return checker(shop_info)


def status_icon(status: str) -> str:
    if "在庫あり" in status:
        return "●"
    elif "在庫なし" in status:
        return "✕"
    else:
        return "?"


def print_results(results: list[StockResult]):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print()
    print("=" * 78)
    print("  Raspberry Pi AI HAT+ 2 在庫確認結果（日本国内）")
    print(f"  確認日時: {now}")
    print("=" * 78)
    print()

    # Amazon と国内ショップに分類
    amazon_results = [r for r in results if "Amazon" in r.shop]
    domestic_results = [r for r in results if "Amazon" not in r.shop]

    print("  [Amazon.co.jp]")
    print(f"  {'─' * 72}")
    for r in amazon_results:
        icon = status_icon(r.status)
        price_str = f" | {r.price}" if r.price else ""
        note_str = f" ({r.note})" if r.note else ""
        print(f"  {icon} {r.shop}")
        print(f"    状態: {r.status}{price_str}{note_str}")
        print(f"    URL:  {r.url}")
    print()

    print("  [国内電子部品ショップ]")
    print(f"  {'─' * 72}")
    for r in domestic_results:
        icon = status_icon(r.status)
        price_str = f" | {r.price}" if r.price else ""
        note_str = f" ({r.note})" if r.note else ""
        print(f"  {icon} {r.shop}")
        print(f"    状態: {r.status}{price_str}{note_str}")
        print(f"    URL:  {r.url}")
    print()

    # サマリー
    in_stock = [r for r in results if "在庫あり" in r.status]
    out_stock = [r for r in results if "在庫なし" in r.status]
    unknown = [r for r in results if "確認不可" in r.status]

    print("─" * 78)
    print(f"  ● 在庫あり: {len(in_stock)}  |  ✕ 在庫なし: {len(out_stock)}  |  ? 確認不可: {len(unknown)}")
    print("─" * 78)

    if in_stock:
        print()
        print("  >>> 購入可能なショップ:")
        for r in in_stock:
            price_str = f" ({r.price})" if r.price else ""
            print(f"      {r.shop}{price_str}")
            print(f"        {r.url}")

    print()
    print("  ※ Amazon等はBot検出により正確に取得できない場合があります。")
    print("  ※ 最新の在庫状況は各サイトで直接ご確認ください。")
    print()


def clean_price(price: Optional[str]) -> Optional[str]:
    """価格文字列をクリーンアップ"""
    if not price:
        return None
    # パイプ文字を除去（Markdownテーブル対策）
    price = price.replace("|", "")
    # 最初の価格だけ取り出す
    match = re.search(r'[¥￥$][\d,]+(?:\.\d+)?|[\d,]+円', price)
    if match:
        return match.group(0)
    return price.strip()


def export_markdown(results: list[StockResult], filepath: str = "inventory_result.md"):
    """結果をMarkdownファイルに出力"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    amazon_results = [r for r in results if "Amazon" in r.shop]
    domestic_results = [r for r in results if "Amazon" not in r.shop]
    in_stock = [r for r in results if "在庫あり" in r.status]
    out_stock = [r for r in results if "在庫なし" in r.status]
    unknown = [r for r in results if "確認不可" in r.status]

    lines = [
        f"# Raspberry Pi AI HAT+ 2 在庫確認結果",
        f"",
        f"**確認日時:** {now}",
        f"",
        f"**製品情報:** Hailo-10H AIアクセラレータ / 40 TOPS (INT4) / 8GB RAM / $130",
        f"",
        f"---",
        f"",
        f"## サマリー",
        f"",
        f"| 状態 | 件数 |",
        f"|------|------|",
        f"| 在庫あり | **{len(in_stock)}** |",
        f"| 在庫なし | {len(out_stock)} |",
        f"| 確認不可 | {len(unknown)} |",
        f"",
        f"---",
        f"",
        f"## Amazon.co.jp",
        f"",
        f"| ショップ | 状態 | 価格 | 備考 |",
        f"|----------|------|------|------|",
    ]

    for r in amazon_results:
        icon = status_icon(r.status)
        price = clean_price(r.price) or "-"
        note = (r.note or "").replace("|", "/")
        lines.append(f"| {icon} [{r.shop}]({r.url}) | {r.status} | {price} | {note} |")

    lines += [
        f"",
        f"## 国内電子部品ショップ",
        f"",
        f"| ショップ | 状態 | 価格 | 備考 |",
        f"|----------|------|------|------|",
    ]

    for r in domestic_results:
        icon = status_icon(r.status)
        price = clean_price(r.price) or "-"
        note = (r.note or "").replace("|", "/")
        lines.append(f"| {icon} [{r.shop}]({r.url}) | {r.status} | {price} | {note} |")

    if in_stock:
        lines += [
            f"",
            f"---",
            f"",
            f"## 購入可能なショップ",
            f"",
        ]
        for r in in_stock:
            price_str = f" - {r.price}" if r.price else ""
            lines.append(f"- **[{r.shop}]({r.url})**{price_str}")

    lines += [
        f"",
        f"---",
        f"",
        f"> **注意事項**",
        f"> - Amazon等の大手サイトはBot検出により正確に取得できない場合があります",
        f"> - 最新の在庫状況は各サイトで直接ご確認ください",
        f"",
    ]

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"  >> 結果を {filepath} に出力しました")


def main():
    print()
    print("  ┌──────────────────────────────────────────────┐")
    print("  │  Raspberry Pi AI HAT+ 2 在庫チェッカー       │")
    print("  │  Hailo-10H / 40 TOPS / 8GB RAM / $130        │")
    print("  │  日本国内ショップ特化版                       │")
    print("  └──────────────────────────────────────────────┘")
    print()
    print(f"  {len(SHOPS)} ショップの在庫を確認中...")
    print()

    results = run_check()
    for r in results:
        icon = status_icon(r.status)
        print(f"    {icon} {r.shop}: {r.status}")

    print_results(results)
    export_markdown(results)


def run_check() -> list[StockResult]:
    """在庫チェックを実行し結果を返す"""
    results = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(check_shop, shop): shop for shop in SHOPS}
        for future in as_completed(futures):
            shop = futures[future]
            try:
                results.append(future.result())
            except Exception as e:
                results.append(StockResult(shop["shop"], shop["url"], "確認不可", note=str(e)))

    shop_order = {s["shop"]: i for i, s in enumerate(SHOPS)}
    results.sort(key=lambda r: shop_order.get(r.shop, 999))
    return results


# AI HAT+ 2 (40TOPS) の在庫監視対象ショップ名
TARGET_SHOPS_40TOPS = {
    "Amazon.co.jp (AI HAT+ 2 / 40TOPS)",
    "スイッチサイエンス",
    "KSY (公式代理店)",
    "秋月電子通商",
    "マルツ",
    "千石電商",
}


def watch_mode(interval_min: int = 5):
    """在庫監視モード: AI HAT+ 2 (40TOPS) の在庫が出たら通知"""
    print()
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║  AI HAT+ 2 (40TOPS) 在庫監視モード              ║")
    print(f"  ║  チェック間隔: {interval_min}分                             ║")
    print("  ║  在庫が見つかったら通知します                    ║")
    print("  ║  Ctrl+C で停止                                  ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print()

    check_count = 0
    alert_file = "/home/user/test/stock_alert.json"

    try:
        while True:
            check_count += 1
            now = datetime.now().strftime("%H:%M:%S")
            print(f"  [{now}] チェック #{check_count} 実行中...", flush=True)

            results = run_check()

            # 40TOPS対象ショップで在庫ありを探す
            in_stock_40tops = [
                r for r in results
                if r.shop in TARGET_SHOPS_40TOPS and "在庫あり" in r.status
            ]

            if in_stock_40tops:
                # 在庫発見！
                print()
                print("  " + "!" * 60)
                print("  !!!  AI HAT+ 2 (40TOPS) の在庫が見つかりました！ !!!")
                print("  " + "!" * 60)
                print()
                for r in in_stock_40tops:
                    price_str = f" ({r.price})" if r.price else ""
                    print(f"  >>> {r.shop}{price_str}")
                    print(f"      {r.url}")
                print()

                # ターミナルベル
                print("\a\a\a", flush=True)

                # アラートファイル出力
                alert_data = {
                    "found_at": datetime.now().isoformat(),
                    "shops": [
                        {"shop": r.shop, "url": r.url, "price": r.price, "status": r.status}
                        for r in in_stock_40tops
                    ],
                }
                with open(alert_file, "w", encoding="utf-8") as f:
                    json.dump(alert_data, f, ensure_ascii=False, indent=2)
                print(f"  >> アラート情報を {alert_file} に保存しました")

                # Markdownも更新
                export_markdown(results)
                return in_stock_40tops
            else:
                # 在庫なし - 状況を1行で表示
                statuses = []
                for r in results:
                    if r.shop in TARGET_SHOPS_40TOPS:
                        icon = status_icon(r.status)
                        statuses.append(f"{icon}{r.shop.split('(')[0].strip()}")
                print(f"    在庫なし | {' / '.join(statuses)}")

                next_time = datetime.now().strftime("%H:%M:%S")
                print(f"    次回チェック: {interval_min}分後", flush=True)
                time.sleep(interval_min * 60)

    except KeyboardInterrupt:
        print()
        print("  監視を停止しました。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Raspberry Pi AI HAT+ 2 在庫チェッカー")
    parser.add_argument("--watch", action="store_true", help="在庫監視モード（在庫が出るまで繰り返しチェック）")
    parser.add_argument("--interval", type=int, default=5, help="監視間隔（分）デフォルト: 5分")
    args = parser.parse_args()

    if args.watch:
        watch_mode(args.interval)
    else:
        main()
