# Food Platform Crawler (ShopeeFood + GrabFood)

## Cài đặt
```bash
pip install requests
```

## Chạy

### ShopeeFood (khuyến nghị - có đủ SĐT)
```bash
python shopeefood_crawler.py \
    --cities "Hà Nội,Hồ Chí Minh,Đà Nẵng" \
    --blacklist blacklist.txt \
    --out shopee.csv \
    --sleep 0.4
```

### GrabFood
```bash
python grabfood_crawler.py --blacklist blacklist.txt --out grab.csv
```

## Output columns
| Field | ShopeeFood | GrabFood |
|---|---|---|
| name | ✅ | ✅ |
| phone | ✅ | ❌ (Grab ẩn) |
| address | ✅ | ✅ |
| city/tỉnh thành | ✅ (chính xác) | ⚠ (parse từ address) |
| lat, lng | ✅ | ✅ |
| rating | ✅ | ✅ |
| is_open | ✅ | ✅ |

## Lưu ý thực chiến

1. **Rate limit**: ShopeeFood chặn khá nhẹ, sleep 0.3-0.5s là ổn. GrabFood gắt hơn, nếu bị 429 phải tăng sleep lên 2s hoặc dùng proxy rotate.

2. **city_id ShopeeFood**: File hiện có ~10 thành phố. Để lấy full list, call:
   ```
   GET https://gappapi.deliverynow.vn/api/city/get_all_cities
   ```
   rồi cập nhật dict `CITY_IDS`.

3. **GrabFood seed points**: Crawl theo toạ độ + bán kính ~5km. Muốn cover tỉnh mới, thêm toạ độ trung tâm vào `SEED_POINTS`. Có thể grid-search (chia lưới 0.05 độ) để quét triệt để.

4. **Dedupe**: ShopeeFood dedupe theo `delivery_id`, GrabFood theo `merchant_id`. Nếu muốn merge 2 nguồn → dùng fuzzy match trên `(name, lat, lng)` với threshold khoảng cách < 50m.

5. **SĐT GrabFood**: Không có cách lấy legit ở scale. Workaround: cross-reference với ShopeeFood theo tên + toạ độ để suy ra.

6. **Ethic/Legal**: 2 trang này đều có ToS cấm scraping. Dùng cho nội bộ / research, giới hạn request rate, không bán lại dữ liệu. Nếu là dự án thương mại → nên liên hệ API partner của họ.

## Scale up
Nếu cần crawl toàn VN (>100k cửa hàng):
- Chuyển sang async với `httpx` + `asyncio` (concurrency 5-10)
- Proxy pool (đặc biệt cho Grab)
- Queue job (Redis/RabbitMQ) + worker pool
- Lưu vào Postgres thay CSV, có `UNIQUE(source, merchant_id)` để resume
