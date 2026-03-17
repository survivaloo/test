#!/usr/bin/env python3
"""
Raspberry Pi AI HAT+ 2 在庫確認アプリ
Amazon (US/JP) を含む複数ショップの在庫状況をチェックします。
"""

import requests
from bs4 import BeautifulSoup
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional


@dataclass
class StockResult:
    shop: str
    region: str
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
    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
}

SHOPS = [
    # --- Amazon ---
    {
        "shop": "Amazon.co.jp (AI HAT+ 26TOPS)",
        "region": "日本",
        "url": "https://www.amazon.co.jp/dp/B0DPLR3RPQ",
        "checker": "amazon_jp",
    },
    {
        "shop": "Amazon.co.jp (AI HAT+ 13TOPS)",
        "region": "日本",
        "url": "https://www.amazon.co.jp/dp/B0DPLQ9TB9",
        "checker": "amazon_jp",
    },
    {
        "shop": "Amazon.com (AI Kit 13T)",
        "region": "US",
        "url": "https://www.amazon.com/dp/B0F95W3446",
        "checker": "amazon_us",
    },
    # --- 日本ショップ ---
    {
        "shop": "スイッチサイエンス",
        "region": "日本",
        "url": "https://www.switch-science.com/products/10916",
        "checker": "switch_science",
    },
    {
        "shop": "KSY",
        "region": "日本",
        "url": "https://raspberry-pi.ksyic.com/main/index/pdp.id/1257/pdp.open/1257",
        "checker": "ksy",
    },
    # --- 海外ショップ ---
    {
        "shop": "Raspberry Pi 公式",
        "region": "UK",
        "url": "https://www.raspberrypi.com/products/ai-hat-plus-2/",
        "checker": "raspberrypi_official",
    },
    {
        "shop": "The Pi Hut",
        "region": "UK",
        "url": "https://thepihut.com/products/raspberry-pi-ai-hat-2",
        "checker": "pihut",
    },
    {
        "shop": "Pimoroni",
        "region": "UK",
        "url": "https://shop.pimoroni.com/products/raspberry-pi-ai-hat-2",
        "checker": "pimoroni",
    },
    {
        "shop": "PiShop.us",
        "region": "US",
        "url": "https://www.pishop.us/product/raspberry-pi-ai-hat-2/",
        "checker": "pishop",
    },
    {
        "shop": "Adafruit",
        "region": "US",
        "url": "https://www.adafruit.com/product/6451",
        "checker": "adafruit",
    },
    {
        "shop": "SparkFun",
        "region": "US",
        "url": "https://www.sparkfun.com/raspberry-pi-ai-hat-2.html",
        "checker": "sparkfun",
    },
    {
        "shop": "CanaKit",
        "region": "US/CA",
        "url": "https://www.canakit.com/raspberry-pi-ai-hat-2.html",
        "checker": "canakit",
    },
    {
        "shop": "Electrokit",
        "region": "EU",
        "url": "https://www.electrokit.com/en/raspberry-pi-ai-hat2",
        "checker": "electrokit",
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
        return StockResult(shop_info["shop"], shop_info["region"], shop_info["url"], "確認不可",
                           note="ページ取得失敗 (Bot検出の可能性)")

    text = soup.get_text(" ", strip=True)

    # 価格を探す
    price = None
    price_el = soup.select_one("#priceblock_ourprice, #priceblock_dealprice, .a-price .a-offscreen, #corePrice_feature_div .a-offscreen")
    if price_el:
        price = price_el.get_text(strip=True)

    # 在庫判定
    if "在庫あり" in text or "在庫残り" in text:
        return StockResult(shop_info["shop"], shop_info["region"], shop_info["url"], "在庫あり", price=price)
    elif "現在在庫切れ" in text or "この商品は現在お取り扱いできません" in text:
        return StockResult(shop_info["shop"], shop_info["region"], shop_info["url"], "在庫なし", price=price)
    elif "カートに入れる" in text:
        return StockResult(shop_info["shop"], shop_info["region"], shop_info["url"], "在庫あり（カート可）", price=price)
    else:
        return StockResult(shop_info["shop"], shop_info["region"], shop_info["url"], "確認不可",
                           price=price, note="在庫表示を検出できず")


def check_amazon_us(shop_info: dict) -> StockResult:
    """Amazon.com の在庫確認"""
    soup = fetch_page(shop_info["url"])
    if not soup:
        return StockResult(shop_info["shop"], shop_info["region"], shop_info["url"], "確認不可",
                           note="ページ取得失敗 (Bot検出の可能性)")

    text = soup.get_text(" ", strip=True)

    price = None
    price_el = soup.select_one(".a-price .a-offscreen, #priceblock_ourprice")
    if price_el:
        price = price_el.get_text(strip=True)

    if "In Stock" in text or "In stock" in text:
        return StockResult(shop_info["shop"], shop_info["region"], shop_info["url"], "在庫あり", price=price)
    elif "Currently unavailable" in text or "out of stock" in text.lower():
        return StockResult(shop_info["shop"], shop_info["region"], shop_info["url"], "在庫なし", price=price)
    elif "Add to Cart" in text:
        return StockResult(shop_info["shop"], shop_info["region"], shop_info["url"], "在庫あり（カート可）", price=price)
    else:
        return StockResult(shop_info["shop"], shop_info["region"], shop_info["url"], "確認不可",
                           price=price, note="在庫表示を検出できず")


def check_generic_page(shop_info: dict, in_stock_patterns: list, out_of_stock_patterns: list,
                        price_selector: Optional[str] = None) -> StockResult:
    """汎用的な在庫チェッカー"""
    soup = fetch_page(shop_info["url"])
    if not soup:
        return StockResult(shop_info["shop"], shop_info["region"], shop_info["url"], "確認不可",
                           note="ページ取得失敗")

    text = soup.get_text(" ", strip=True).lower()

    price = None
    if price_selector:
        price_el = soup.select_one(price_selector)
        if price_el:
            price = price_el.get_text(strip=True)

    for pattern in out_of_stock_patterns:
        if pattern.lower() in text:
            return StockResult(shop_info["shop"], shop_info["region"], shop_info["url"], "在庫なし", price=price)

    for pattern in in_stock_patterns:
        if pattern.lower() in text:
            return StockResult(shop_info["shop"], shop_info["region"], shop_info["url"], "在庫あり", price=price)

    return StockResult(shop_info["shop"], shop_info["region"], shop_info["url"], "確認不可",
                       price=price, note="在庫表示を検出できず")


def check_switch_science(shop_info: dict) -> StockResult:
    return check_generic_page(
        shop_info,
        in_stock_patterns=["カートに入れる", "在庫あり", "add to cart"],
        out_of_stock_patterns=["sold out", "在庫切れ", "入荷待ち", "notify me"],
        price_selector=".product-price, .price",
    )


def check_ksy(shop_info: dict) -> StockResult:
    return check_generic_page(
        shop_info,
        in_stock_patterns=["カートに入れる", "add to cart", "在庫あり", "buy now"],
        out_of_stock_patterns=["sold out", "在庫切れ", "品切れ", "入荷未定"],
    )


def check_raspberrypi_official(shop_info: dict) -> StockResult:
    return check_generic_page(
        shop_info,
        in_stock_patterns=["buy now", "add to cart", "in stock"],
        out_of_stock_patterns=["out of stock", "notify me", "sold out"],
    )


def check_pihut(shop_info: dict) -> StockResult:
    return check_generic_page(
        shop_info,
        in_stock_patterns=["add to cart", "in stock"],
        out_of_stock_patterns=["sold out", "out of stock", "notify me", "back soon"],
        price_selector=".product-price, .price",
    )


def check_pimoroni(shop_info: dict) -> StockResult:
    return check_generic_page(
        shop_info,
        in_stock_patterns=["add to cart", "in stock", "ready to ship"],
        out_of_stock_patterns=["out of stock", "sold out", "back in stock", "notify me"],
        price_selector=".product-price, .price",
    )


def check_pishop(shop_info: dict) -> StockResult:
    return check_generic_page(
        shop_info,
        in_stock_patterns=["add to cart", "in stock"],
        out_of_stock_patterns=["out of stock", "sold out", "notify"],
        price_selector=".price",
    )


def check_adafruit(shop_info: dict) -> StockResult:
    return check_generic_page(
        shop_info,
        in_stock_patterns=["add to cart", "in stock"],
        out_of_stock_patterns=["out of stock", "sold out", "notify me"],
        price_selector=".prod-price",
    )


def check_sparkfun(shop_info: dict) -> StockResult:
    return check_generic_page(
        shop_info,
        in_stock_patterns=["add to cart", "in stock"],
        out_of_stock_patterns=["out of stock", "sold out", "backorder", "notify"],
        price_selector=".price",
    )


def check_canakit(shop_info: dict) -> StockResult:
    return check_generic_page(
        shop_info,
        in_stock_patterns=["add to cart", "in stock"],
        out_of_stock_patterns=["out of stock", "sold out", "notify", "unavailable"],
        price_selector=".price",
    )


def check_electrokit(shop_info: dict) -> StockResult:
    return check_generic_page(
        shop_info,
        in_stock_patterns=["add to cart", "in stock", "buy"],
        out_of_stock_patterns=["out of stock", "sold out", "notify", "enter your e-mail"],
        price_selector=".price",
    )


CHECKER_MAP = {
    "amazon_jp": check_amazon_jp,
    "amazon_us": check_amazon_us,
    "switch_science": check_switch_science,
    "ksy": check_ksy,
    "raspberrypi_official": check_raspberrypi_official,
    "pihut": check_pihut,
    "pimoroni": check_pimoroni,
    "pishop": check_pishop,
    "adafruit": check_adafruit,
    "sparkfun": check_sparkfun,
    "canakit": check_canakit,
    "electrokit": check_electrokit,
}


def check_shop(shop_info: dict) -> StockResult:
    """ショップの在庫をチェック"""
    checker = CHECKER_MAP.get(shop_info["checker"])
    if not checker:
        return StockResult(shop_info["shop"], shop_info["region"], shop_info["url"], "確認不可",
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
    """結果を表示"""
    print()
    print("=" * 80)
    print("  Raspberry Pi AI HAT+ 2 在庫確認結果")
    print("=" * 80)
    print()

    # 地域ごとにグループ化
    regions = {}
    for r in results:
        regions.setdefault(r.region, []).append(r)

    for region, items in regions.items():
        print(f"  [{region}]")
        print(f"  {'─' * 74}")
        for r in items:
            icon = status_icon(r.status)
            price_str = f" | {r.price}" if r.price else ""
            note_str = f" ({r.note})" if r.note else ""
            print(f"  {icon} {r.shop:<35} {r.status:<15}{price_str}{note_str}")
            print(f"    {r.url}")
        print()

    # サマリー
    in_stock = [r for r in results if "在庫あり" in r.status]
    out_stock = [r for r in results if "在庫なし" in r.status]
    unknown = [r for r in results if "確認不可" in r.status]

    print("─" * 80)
    print(f"  ● 在庫あり: {len(in_stock)}  |  ✕ 在庫なし: {len(out_stock)}  |  ? 確認不可: {len(unknown)}")
    print("─" * 80)

    if in_stock:
        print()
        print("  >>> 購入可能なショップ:")
        for r in in_stock:
            print(f"      {r.shop} - {r.url}")

    print()
    print("  ※ Amazonなどの大手サイトはBot検出により正確に取得できない場合があります。")
    print("  ※ AI HAT+ 2 はまだAmazonに未掲載の可能性があります（旧モデルのみ表示）。")
    print("  ※ 最新の在庫状況は各サイトで直接ご確認ください。")
    print()


def main():
    print()
    print("  Raspberry Pi AI HAT+ 2 在庫チェッカー")
    print("  Hailo-10H / 40 TOPS / 8GB RAM / $130")
    print("  ─────────────────────────────────────")
    print(f"  {len(SHOPS)} ショップの在庫を確認中...")
    print()

    results = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(check_shop, shop): shop for shop in SHOPS}
        for future in as_completed(futures):
            shop = futures[future]
            try:
                result = future.result()
                icon = status_icon(result.status)
                print(f"    {icon} {result.shop}: {result.status}")
                results.append(result)
            except Exception as e:
                print(f"    ? {shop['shop']}: エラー ({e})")
                results.append(StockResult(shop["shop"], shop["region"], shop["url"], "確認不可",
                                           note=str(e)))

    # 元の順序でソート
    shop_order = {s["shop"]: i for i, s in enumerate(SHOPS)}
    results.sort(key=lambda r: shop_order.get(r.shop, 999))

    print_results(results)


if __name__ == "__main__":
    main()
