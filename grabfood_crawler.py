"""
GrabFood Crawler
----------------
Crawl GrabFood theo danh sách toạ độ trung tâm các khu vực.
Dùng Playwright: sau khi mở food.grab.com, gọi API category qua APIRequestContext.fetch
(cùng cookie với trình duyệt — khác với requests thuần hay POST search cũ thường bị chặn).

Lưu ý: GrabFood KHÔNG expose phone number công khai -> cột phone để trống.

Chạy:
    python grabfood_crawler.py --out grab.csv
"""

import argparse
import csv
import re
import time
from dataclasses import dataclass, asdict
from typing import Optional

from playwright.sync_api import Page

from playwright_browser import browser_page, goto_ready


# Guest category API (GET) — thay thế flow search POST cũ.
GRAB_CATEGORY_URL = "https://portal.grab.com/foodweb/guest/v2/category"
GRAB_HOME = "https://food.grab.com/vn/vi/"

# Toạ độ trung tâm các khu vực để quét. Nhiều điểm hơn = cover tốt hơn.
# Format: (city_name, lat, lng)
SEED_POINTS = [
    ("Hà Nội", 21.0285, 105.8542),
    ("Hà Nội", 21.0333, 105.8000),  # Cầu Giấy
    ("Hà Nội", 20.9950, 105.8400),  # Hoàng Mai
    ("Hồ Chí Minh", 10.7769, 106.7009),  # Q1
    ("Hồ Chí Minh", 10.8030, 106.6432),  # Tân Bình
    ("Hồ Chí Minh", 10.7380, 106.7290),  # Q7
    # ("Đà Nẵng", 16.0544, 108.2022),
    # ("Cần Thơ", 10.0452, 105.7469),
    # ("Hải Phòng", 20.8449, 106.6881),
]


@dataclass
class Restaurant:
    source: str
    merchant_id: str
    name: str
    phone: str
    address: str
    city: str
    lat: float
    lng: float
    rating: Optional[float]
    total_reviews: Optional[int]
    is_open: bool
    url: str


def search_grab(
    page: Page,
    lat: float,
    lng: float,
    offset: int,
    page_size: int = 32,
    category_shortcut_id: int = 305,
) -> dict:
    """
    GET guest/v2/category via APIRequestContext.fetch (uses browser cookie jar after visiting GRAB_HOME).
    category_shortcut_id 305 = Khuyến mãi (mặc định trên web).
    """
    params = (
        f"latlng={lat},{lng}"
        f"&categoryShortcutID={category_shortcut_id}"
        f"&searchID="
        f"&offset={offset}"
        f"&pageSize={page_size}"
    )
    url = f"{GRAB_CATEGORY_URL}?{params}"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://food.grab.com",
        "Referer": "https://food.grab.com/",
        "x-country-code": "VN",
        "x-gfc-country": "VN",
    }
    resp = page.request.fetch(url, headers=headers)
    if not resp.ok:
        body = resp.text()
        raise RuntimeError(f"HTTP {resp.status}: {body[:400]}")
    return resp.json()


def extract_province(address: str) -> str:
    """Heuristic: parse tỉnh/thành từ cuối địa chỉ Việt Nam."""
    if not address:
        return ""
    parts = [p.strip() for p in address.split(",")]
    for tail in reversed(parts):
        t = re.sub(r"^(tp\.?|thành phố|tỉnh)\s+", "", tail.lower()).strip()
        if t:
            return t.title()
    return ""


def parse_merchant(m: dict, default_city: str) -> Optional[Restaurant]:
    """Parse merchant from guest/v2/category or legacy search shape."""
    try:
        merchant = m.get("merchantBrief") or {}
        chain = m.get("chain") or {}
        mid = m.get("id") or chain.get("ID") or ""
        name = (
            merchant.get("displayInfo", {}).get("primaryText")
            or merchant.get("displayName")
            or ""
        )
        addr_obj = m.get("address") or merchant.get("address") or {}
        address = (addr_obj.get("name") if isinstance(addr_obj, dict) else "") or ""

        latlng = m.get("latlng") or merchant.get("address", {}).get("latlng") or {}
        lat = float(latlng.get("latitude") or 0)
        lng = float(latlng.get("longitude") or 0)

        rating = merchant.get("rating")
        vote_count = merchant.get("voteCount") or merchant.get("vote_count")

        closed = merchant.get("closed", False)
        oh = merchant.get("openHours") or {}
        if oh:
            is_open = bool(oh.get("open", True))
        else:
            is_open = not closed

        province = extract_province(address) or default_city

        return Restaurant(
            source="grabfood",
            merchant_id=str(mid),
            name=str(name).strip(),
            phone="",
            address=address.strip(),
            city=province,
            lat=lat,
            lng=lng,
            rating=float(rating) if rating is not None else None,
            total_reviews=int(vote_count) if vote_count is not None else None,
            is_open=is_open,
            url=f"https://food.grab.com/vn/vi/restaurant/{mid}",
        )
    except Exception as e:
        print(f"    ! parse err: {e}")
        return None


def contains_blacklist(r: Restaurant, keywords: list[str]) -> bool:
    if not keywords:
        return False
    hay = f"{r.name} {r.address}".lower()
    return any(kw.strip().lower() in hay for kw in keywords if kw.strip())


def crawl_point(
    page,
    city,
    lat,
    lng,
    blacklist,
    max_offset=1000,
    page_size=32,
    sleep=1.0,
    category_shortcut_id: int = 305,
):
    seen = set()
    offset = 0
    fail_streak = 0
    while offset < max_offset:
        try:
            data = search_grab(
                page,
                lat,
                lng,
                offset,
                page_size,
                category_shortcut_id=category_shortcut_id,
            )
            fail_streak = 0
        except Exception as e:
            err = str(e).lower()
            print(f"  ! offset {offset} failed: {e}")
            fail_streak += 1
            if fail_streak > 6:
                print(f"  ! bỏ qua offset {offset} sau nhiều lần thử")
                fail_streak = 0
                offset += page_size
                continue
            time.sleep(8 if "429" in err or "rate" in err else 3)
            continue

        merchants = (data.get("searchResult") or {}).get("searchMerchants") or []
        if not merchants:
            break

        print(f"  [{city} @ {lat},{lng}] offset {offset}: {len(merchants)} merchants")
        for m in merchants:
            r = parse_merchant(m, city)
            if not r or not r.merchant_id or r.merchant_id in seen:
                continue
            seen.add(r.merchant_id)
            if not contains_blacklist(r, blacklist):
                yield r

        offset += page_size
        time.sleep(sleep)


def load_blacklist(path):
    if not path:
        return []
    with open(path, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def write_csv(path, rows):
    rows = list(rows)
    if not rows:
        print("Không có dữ liệu.")
        return
    uniq = {r.merchant_id: r for r in rows}
    rows = list(uniq.values())
    fields = list(asdict(rows[0]).keys())
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(asdict(r))
    print(f"Đã lưu {len(rows)} cửa hàng -> {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blacklist")
    ap.add_argument("--out", default="grabfood.csv")
    ap.add_argument(
        "--sleep",
        type=float,
        default=1.0,
        help="Pause between pagination requests (giảm 429)",
    )
    ap.add_argument(
        "--category-id",
        type=int,
        default=305,
        help="Grab categoryShortcutID (default 305 = Khuyến mãi)",
    )
    ap.add_argument(
        "--headed",
        action="store_true",
        help="Show browser window (useful if headless is blocked)",
    )
    args = ap.parse_args()

    blacklist = load_blacklist(args.blacklist)
    rows = []

    with browser_page(headless=not args.headed) as page:
        goto_ready(page, GRAB_HOME)
        page.wait_for_timeout(2500)
        for city, lat, lng in SEED_POINTS:
            print(f"\n=== {city} @ ({lat},{lng}) ===")
            for r in crawl_point(
                page,
                city,
                lat,
                lng,
                blacklist,
                sleep=args.sleep,
                category_shortcut_id=args.category_id,
            ):
                rows.append(r)

    write_csv(args.out, rows)


if __name__ == "__main__":
    main()
