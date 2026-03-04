---
title: "Database - Indexing: GIN & GiST"
tags:
  - "database"
  - "postgresql"
  - "indexing"
  - "gin"
  - "gist"
  - "jsonb"
  - "search"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "B-Tree rất tuyệt vời cho các dữ liệu đơn giản (số, chuỗi ngắn). Nhưng trong Ngân hàng hiện đại, dữ liệu phức tạp hơn nhiều:"
---

## 1. Tại sao B-Tree là chưa đủ?

B-Tree rất tuyệt vời cho các dữ liệu đơn giản (số, chuỗi ngắn). Nhưng trong Ngân hàng hiện đại, dữ liệu phức tạp hơn nhiều:

- **Log giao dịch (JSONB):** Lưu thông tin thiết bị, IP, Location, Metadata của App.
    
- **Mô tả giao dịch (Text):** "Chuyen tien mung cuoi cho chu Ba..." (Cần tìm kiếm từ khóa).
    
- **Vị trí ATM (Geo):** Tìm cây ATM gần nhất.
    

B-Tree bó tay với các câu hỏi: _"Tìm giao dịch nào mà trong JSON metadata có chứa key 'device_id' là 'X'?"_. Đây là lúc GIN và GiST tỏa sáng.

---

## 2. GIN (Generalized Inverted Index)

> [!SUMMARY] Mental Model
> 
> **GIN giống như phần "Mục lục từ khóa" (Index) ở cuối một cuốn sách.**
> 
> Thay vì lật từng trang để tìm từ "Bank", bạn tra mục lục xem từ "Bank" xuất hiện ở trang 10, 50, 99.
> 
> - **Chuyên trị:** Dữ liệu chứa nhiều phần tử con (Composite values).
>     
> - **Use Case:** JSONB, Arrays, Full Text Search.
>     

### A. JSONB Indexing (Cực quan trọng cho NoSQL on Postgres)

Ngân hàng thường lưu log request/response dưới dạng JSONB để linh hoạt.

**Kịch bản:** Tìm tất cả giao dịch thực hiện trên iPhone 14.

SQL

```sql
-- Tạo bảng có cột JSONB
CREATE TABLE app_logs (
    id bigserial PRIMARY KEY,
    data JSONB
);

-- Insert dữ liệu
INSERT INTO app_logs (data) VALUES
('{"device": "iPhone 14", "app_version": "1.0", "action": "login"}'),
('{"device": "Samsung S23", "app_version": "1.1", "action": "transfer"}');

-- Tạo GIN Index cho cột JSONB
CREATE INDEX idx_logs_data ON app_logs USING GIN (data);

-- Query sử dụng Index (Toán tử @> nghĩa là "chứa")
-- Postgres sẽ tra GIN index để tìm key "device":"iPhone 14" -> Ra ngay ID dòng đó.
EXPLAIN ANALYZE
SELECT * FROM app_logs
WHERE data @> '{"device": "iPhone 14"}';
```

### B. Full Text Search

Tìm kiếm nội dung giao dịch ("Chuyển tiền tiền nhà tháng 10").

SQL

```sql
-- Tạo cột tsvector để chuẩn hóa văn bản (tách từ, bỏ dấu)
ALTER TABLE transactions ADD COLUMN search_vector tsvector;

-- Tự động cập nhật vector khi data thay đổi
UPDATE transactions
SET search_vector = to_tsvector('vietnamese', description);

-- Tạo GIN Index
CREATE INDEX idx_search ON transactions USING GIN (search_vector);

-- Tìm kiếm siêu tốc (Full Text Search)
SELECT * FROM transactions
WHERE search_vector @@ to_tsquery('vietnamese', 'tiền & nhà');
```

---

## 3. GiST (Generalized Search Tree)

> [!SUMMARY] Mental Model
> 
> **GiST là một bộ khung (Framework) để xây dựng cây chỉ mục tùy ý.**
> 
> Nó không lưu giá trị cụ thể, mà lưu các **"điều kiện bao phủ"** (như hình chữ nhật bao quanh một khu vực, hoặc khoảng thời gian).
> 
> - **Chuyên trị:** Dữ liệu Hình học (GIS), Khoảng thời gian (Range), Tìm kiếm lân cận (Nearest Neighbor).
>     

### A. Location Search (PostGIS - Tìm ATM gần nhất)

B-Tree không thể sắp xếp tọa độ không gian 2 chiều. GiST sử dụng R-Tree để chia bản đồ thành các hình chữ nhật lồng nhau.

SQL

```sql
-- Tìm 5 cây ATM gần vị trí của tôi nhất (KNN Search)
-- Toán tử <-> là khoảng cách
SELECT * FROM atms
ORDER BY location <-> ST_Point(106.7, 10.8)
LIMIT 5;
```

### B. Fuzzy Search (Tìm kiếm gần đúng - Trigram)

Dùng cho **KYC (Know Your Customer)**. Khách hàng tên "Nguyễn Văn **A**" nhưng nhập nhầm là "Nguyễn Văn **E**".

Extension `pg_trgm` sử dụng GiST index để tìm độ tương đồng chuỗi.

SQL

```sql
CREATE EXTENSION pg_trgm;
CREATE INDEX idx_name_trigram ON users USING GIST (full_name gist_trgm_ops);

-- Tìm tên gần giống nhất
SELECT * FROM users
WHERE full_name % 'Nguyen Van E'; -- Toán tử % (Similarity)
```

---

## 4. So sánh GIN vs. GiST (Interview Cheat Sheet)

Khi nào dùng cái nào cho Full Text Search hoặc Array?

|**Đặc điểm**|**GIN (Inverted Index)**|**GiST (Search Tree)**|
|---|---|---|
|**Tốc độ Đọc (Search)**|🚀 **Nhanh hơn gấp 3 lần** GiST.|Chậm hơn GIN.|
|**Tốc độ Ghi (Update)**|🐢 **Rất chậm**. (Tốn công update danh sách ngược).|🚀 Nhanh hơn GIN.|
|**Dung lượng đĩa**|Tốn nhiều chỗ hơn.|Gọn nhẹ hơn.|
|**Độ chính xác**|Chính xác tuyệt đối (Standard).|Có thể Lossy (cần check lại Heap).|
|**Lời khuyên**|Dùng cho dữ liệu **ít thay đổi**, cần tìm kiếm cực nhanh (Logs, Archive).|Dùng cho dữ liệu **thay đổi liên tục**, dữ liệu địa lý.|

---

## 5. Câu hỏi phỏng vấn thực tế

> [!QUESTION] Q: Tại sao Insert vào bảng có GIN Index lại chậm? Cách khắc phục?
> 
> **A:**
> 
> - Vì mỗi khi Insert một văn bản, Postgres phải tách từng từ ra và cập nhật vào mục lục GIN (Update rất nhiều chỗ trong Index).
>     
> - **Khắc phục:** Sử dụng tính năng **Pending List** của GIN. Dữ liệu mới sẽ vào danh sách chờ (Insert nhanh). Khi danh sách đầy hoặc chạy Vacuum, nó mới được merge vào Index chính (Bulk Update). `fastupdate = on` (Mặc định là on).
>     

> [!QUESTION] Q: Làm sao tối ưu tìm kiếm `LIKE '%abc%'` (Wildcard đầu và cuối)?
> 
> **A:** B-Tree bó tay.
> 
> Giải pháp là dùng `pg_trgm` (Trigram) kết hợp với **GIN** hoặc **GiST**. Nó sẽ tách chuỗi thành các đoạn 3 ký tự để đánh index.
> 
> SQL
>
> ```sql
> CREATE INDEX trgm_idx ON users USING GIN (email gin_trgm_ops);
> SELECT * FROM users WHERE email LIKE '%gmail%'; -- Index này chạy được!
> ```