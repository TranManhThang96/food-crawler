"""
ShopeeFood Crawler
------------------
Crawl danh sách cửa hàng theo thành phố.
Dùng Playwright: mở trang shopeefood.vn/{slug} và đọc JSON từ response
get_browsing_infos (request do SPA gửi — page.request trực tiếp tới gappapi thường bị 403).

Chạy:
    python shopeefood_crawler.py --cities "Hà Nội,Hồ Chí Minh" --out shopee.csv
"""

import argparse
import csv
import time
from dataclasses import dataclass, asdict
from typing import Iterable, Optional

from playwright.sync_api import Page, Response

from playwright_browser import browser_page


SHOPEE_BASE = "https://shopeefood.vn"

# city_id (legacy) + slug trên web — dùng slug để goto
CITY_SLUGS = {
    "Hồ Chí Minh": ("tp-hcm", 217),
    "Hà Nội": ("ha-noi", 218),
    "Đà Nẵng": ("da-nang", 219),
    "Hải Phòng": ("hai-phong", 220),
    "Cần Thơ": ("can-tho", 221),
    "Biên Hòa": ("bien-hoa", 224),
    "Vũng Tàu": ("vung-tau", 225),
    "Nha Trang": ("nha-trang", 226),
    "Huế": ("hue", 227),
    "Buôn Ma Thuột": ("buon-ma-thuot", 228),
}


@dataclass
class Restaurant:
    source: str
    delivery_id: str
    name: str
    phone: str
    address: str
    city: str
    district: str
    lat: float
    lng: float
    rating: Optional[float]
    total_reviews: Optional[int]
    is_open: bool
    url: str


def _response_json(resp: Response) -> dict:
    if not resp.ok:
        raise RuntimeError(f"HTTP {resp.status} {resp.url}")
    return resp.json()


def parse_browsing_item(item: dict, city_name: str) -> Optional[Restaurant]:
    """Map one delivery_info from get_browsing_infos."""
    did = item.get("delivery_id") or item.get("id")
    if not did:
        return None
    name = (item.get("name") or "").strip()
    phones = item.get("phones") or []
    phone = (phones[0] or "").strip() if phones else ""
    address = (item.get("address") or "").strip()
    pos = item.get("position") or {}
    lat = float(pos.get("latitude") or 0)
    lng = float(pos.get("longitude") or 0)
    rating_obj = item.get("rating") or {}
    rating = rating_obj.get("avg")
    total_reviews = rating_obj.get("total_review")
    op = item.get("operating") or {}
    is_open = bool(item.get("is_open", True))
    if op:
        is_open = op.get("status") == 1
    url = (item.get("url") or "").strip()
    district = ""
    return Restaurant(
        source="shopeefood",
        delivery_id=str(did),
        name=name,
        phone=phone,
        address=address,
        city=city_name,
        district=district,
        lat=lat,
        lng=lng,
        rating=float(rating) if rating is not None else None,
        total_reviews=int(total_reviews) if total_reviews is not None else None,
        is_open=is_open,
        url=url,
    )


def contains_blacklist(r: Restaurant, keywords: list[str]) -> bool:
    if not keywords:
        return False
    hay = f"{r.name} {r.address}".lower()
    return any(kw.strip().lower() in hay for kw in keywords if kw.strip())


def crawl_city(
    page: Page,
    city_name: str,
    slug: str,
    blacklist: list[str],
    sleep_after: float = 0.5,
) -> Iterable[Restaurant]:
    """
    Load city landing page; first successful get_browsing_infos response yields merchants.
    (API gappapi chặn page.request — chỉ lấy batch SPA tải được.)
    """
    url = f"{SHOPEE_BASE}/{slug}"
    with page.expect_response(
        lambda r: "get_browsing_infos" in r.url and r.status == 200,
        timeout=90_000,
    ) as resp_info:
        page.goto(url, wait_until="domcontentloaded", timeout=120_000)
    data = _response_json(resp_info.value)
    items = ((data.get("reply") or {}).get("delivery_infos")) or []
    print(f"  [{city_name}] get_browsing_infos: {len(items)} cửa hàng")

    seen = set()
    for item in items:
        r = parse_browsing_item(item, city_name)
        if not r or r.delivery_id in seen:
            continue
        seen.add(r.delivery_id)
        if not contains_blacklist(r, blacklist):
            yield r

    time.sleep(sleep_after)


def load_blacklist(path: Optional[str]) -> list[str]:
    if not path:
        return []
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def write_csv(path: str, rows: Iterable[Restaurant]):
    rows = list(rows)
    if not rows:
        print("Không có dữ liệu.")
        return
    fields = list(asdict(rows[0]).keys())
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(asdict(r))
    print(f"Đã lưu {len(rows)} cửa hàng -> {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--cities",
        default="Hà Nội,Hồ Chí Minh",
        help="Danh sách tỉnh/thành, phẩy ngăn cách",
    )
    ap.add_argument("--blacklist", help="File txt chứa keyword loại trừ, mỗi dòng 1 keyword")
    ap.add_argument("--out", default="shopeefood.csv")
    ap.add_argument(
        "--sleep",
        type=float,
        default=0.5,
        help="Pause sau mỗi thành phố",
    )
    ap.add_argument(
        "--headed",
        action="store_true",
        help="Show browser window (useful if headless is blocked)",
    )
    args = ap.parse_args()

    blacklist = load_blacklist(args.blacklist)
    if blacklist:
        print(f"Blacklist ({len(blacklist)} keywords): {blacklist[:5]}{'...' if len(blacklist) > 5 else ''}")

    all_rows: list[Restaurant] = []

    with browser_page(headless=not args.headed) as page:
        for city in [c.strip() for c in args.cities.split(",") if c.strip()]:
            if city not in CITY_SLUGS:
                print(f"⚠ Bỏ qua '{city}' (chưa có slug, bổ sung vào CITY_SLUGS)")
                continue
            slug, _cid = CITY_SLUGS[city]
            print(f"\n=== Crawl {city} (slug={slug}) ===")
            for r in crawl_city(page, city, slug, blacklist, sleep_after=args.sleep):
                all_rows.append(r)

    write_csv(args.out, all_rows)


if __name__ == "__main__":
    main()
