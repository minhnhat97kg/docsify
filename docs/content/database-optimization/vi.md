---
title: "Database - Query Optimization"
tags:
  - "database"
  - "optimization"
  - "performance"
  - "postgresql"
  - "sql"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Trước khi optimize, bạn phải biết chậm ở đâu. Đừng đoán mò."
---

## 1. The Microscope: `EXPLAIN (ANALYZE, BUFFERS)`

Trước khi optimize, bạn phải biết chậm ở đâu. Đừng đoán mò.

> [!TIP] Quy tắc vàng
> 
> Đừng chỉ dùng `EXPLAIN`. Hãy dùng `EXPLAIN (ANALYZE, BUFFERS)`.

- **ANALYZE:** Chạy thật câu lệnh để lấy thời gian thực thi chính xác (Execution Time).
    
- **BUFFERS:** Cho biết query này đã đọc bao nhiêu block từ RAM (Shared Hit) và bao nhiêu từ Ổ cứng (Read).
    

**Cách đọc Output:**

1. **Seq Scan (Quét toàn bộ):** Tệ nếu bảng lớn. Cần Index.
    
2. **Index Scan:** Tốt.
    
3. **Bitmap Heap Scan:** Tốt cho các query kết hợp nhiều điều kiện.
    
4. **Loops:** Nếu thấy `Nested Loop` với số rows lớn -> Coi chừng chết DB.
    

SQL

```
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM transactions WHERE user_id = 123;
```

---

## 2. Partial Indexing (Index Một Phần)

Đây là kỹ thuật "Sniper" (Bắn tỉa). Thay vì đánh index cho toàn bộ 1 tỷ dòng, ta chỉ đánh index cho 1 triệu dòng quan trọng.

**Use Case:** Hệ thống xử lý Order.

- 99% đơn hàng là `SUCCESS` (Thành công) -> Ít khi cần query lại.
    
- 1% đơn hàng là `PENDING` hoặc `FAILED` -> Cần query liên tục để Retry.
    

**Giải pháp:** Chỉ tạo index cho các đơn chưa xong.

SQL

```
-- Index này nhỏ hơn 100 lần so với index thường
-- Update/Insert các đơn SUCCESS sẽ không phải tốn công cập nhật Index này
CREATE INDEX idx_orders_pending 
ON orders (created_at) 
WHERE status IN ('PENDING', 'FAILED');
```

---

## 3. Materialized Views (Báo cáo siêu tốc)

Trong Bank, các sếp thường cần xem Dashboard: _"Tổng doanh số theo chi nhánh hôm nay"_.

- Query gốc: `JOIN` 5 bảng, `SUM` 10 triệu dòng -> Mất 10 giây.
    
- Giải pháp: Dùng **Materialized View**.
    

> [!SUMMARY] Cơ chế
> 
> Khác với View thường (chạy query mỗi lần gọi), Materialized View **lưu kết quả query xuống đĩa cứng** (như một bảng thật).
> 
> Query vào đây mất **1ms**.

**Nhược điểm:** Dữ liệu bị cũ (Stale Data). Cần cơ chế làm mới (Refresh).

SQL

```
-- 1. Tạo View vật lý
CREATE MATERIALIZED VIEW report_daily_sales AS
SELECT branch_id, SUM(amount) as total
FROM transactions
WHERE date = CURRENT_DATE
GROUP BY branch_id;

-- 2. Đánh Index cho nó luôn (View thường không làm được)
CREATE INDEX idx_report_branch ON report_daily_sales(branch_id);

-- 3. Làm mới dữ liệu (Cronjob chạy 5 phút/lần)
-- CONCURRENTLY: Quan trọng! Giúp người dùng vẫn đọc được view cũ trong lúc đang refresh view mới.
REFRESH MATERIALIZED VIEW CONCURRENTLY report_daily_sales;
```

---

## 4. Denormalization (Phi chuẩn hóa)

> [!WARNING] Trade-off
> 
> Đây là sự đánh đổi giữa **Write Performance** và **Read Performance**.
> 
> Trong Bank, đôi khi ta chấp nhận dư thừa dữ liệu để đọc nhanh hơn.

**Ví dụ:** Hiển thị số dư tài khoản.

- **Cách chuẩn (Normalized):** `SELECT SUM(amount) FROM transactions WHERE user_id = 1`. (Chậm nếu lịch sử dài).
    
- **Cách phi chuẩn (Denormalized):** Thêm cột `current_balance` vào bảng `users`.
    
    - Mỗi khi có giao dịch mới -> Update cột `current_balance`.
        
    - Khi đọc -> Chỉ cần `SELECT current_balance FROM users` (Siêu nhanh).
        

**Rủi ro:** Race Condition (như bài trước đã bàn). Cần Locking cẩn thận.

---

## 5. Bulk Insert / Copy (Nhập liệu lô lớn)

Nếu bạn cần migrate dữ liệu hoặc xử lý file sao kê cuối ngày.

- **Tệ:** Loop `INSERT INTO` từng dòng. (Mỗi dòng là 1 round-trip mạng + 1 lần ghi WAL).
    
- **Tốt:** Dùng `INSERT INTO ... VALUES (...), (...), (...)` (Batch size ~1000).
    
- **Tốt nhất:** Dùng lệnh `COPY` (Postgres Protocol).
    

**Benchmark:** `COPY` nhanh hơn `INSERT` từng dòng khoảng **10-20 lần**.

Go

```
// Golang với pgx
// Sử dụng CopyFrom để stream dữ liệu trực tiếp vào DB
rows := [][]interface{}{
    {1, "Alice"},
    {2, "Bob"},
}
copyCount, err := conn.CopyFrom(
    context.Background(),
    pgx.Identifier{"users"},
    []string{"id", "name"},
    pgx.CopyFromRows(rows),
)
```

---

## 6. SARGable Queries (Viết SQL thân thiện với Index)

SARGable = **S**earch **ARG**ument **able**.

Nghĩa là viết SQL sao cho DB engine tận dụng được Index.

> [!DANGER] Anti-Pattern (Làm hỏng Index)
> 
> Không bao giờ bọc cột cần tìm trong một hàm (Function).

**Ví dụ:** Tìm giao dịch năm 2024.

- **Sai (Index Scan bị vô hiệu hóa):**
    
    Phải tính toán `YEAR(created_at)` cho toàn bộ 1 tỷ dòng rồi mới so sánh.
    
    SQL
    
    ```
    SELECT * FROM transactions WHERE EXTRACT(YEAR FROM created_at) = 2024;
    ```
    
- **Đúng (Index Range Scan):**
    
    So sánh trực tiếp cột thô.
    
    SQL
    
    ```
    SELECT * FROM transactions 
    WHERE created_at >= '2024-01-01' AND created_at < '2025-01-01';
    ```
    
- **Sai (Wildcard đầu):**
    
    SQL
    
    ```
    SELECT * FROM users WHERE name LIKE '%Tuan%'; -- Full Scan
    ```
    
- **Đúng (Wildcard cuối):**
    
    SQL
    
    ```
    SELECT * FROM users WHERE name LIKE 'Tuan%'; -- Index Scan
    ```
    

---

## 7. CTEs (Common Table Expressions) vs. Temporary Tables

Dùng `WITH` (CTE) để làm code dễ đọc hơn.

- **Trước PG 12:** CTE luôn được coi là một hàng rào tối ưu hóa (Optimization Fence). Postgres sẽ tính toán CTE riêng biệt rồi mới Join. Đôi khi làm chậm.
    
- **PG 12+:** Postgres thông minh hơn, có thể gộp CTE vào query chính để tối ưu (Inline).
    

**Mẹo:** Nếu query phức tạp, đôi khi tách ra lưu vào **Temporary Table** (`CREATE TEMP TABLE`) rồi đánh Index cho bảng tạm đó sẽ nhanh hơn là viết một câu SQL lồng nhau 10 tầng.

---

## 8. Index Fill Factor (Chống phân mảnh)

Mặc định, Postgres chèn đầy data vào các trang (Pages) của Index B-Tree (Fillfactor = 100).

- Nếu bảng `users` bị UPDATE liên tục -> Phải tách trang (Page Split) -> Gây phân mảnh Index và chậm.
    
- **Tối ưu:** Giảm Fillfactor xuống 90% hoặc 80%. Để dành chỗ trống trong trang cho các bản ghi update sau này.
    

SQL

```
ALTER INDEX idx_users_balance SET (fillfactor = 90);
REINDEX INDEX idx_users_balance;
```

---

## 9. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Tôi có bảng 100 triệu dòng, query `SELECT * FROM table ORDER BY id LIMIT 10 OFFSET 1000000` chạy rất chậm. Tại sao và sửa thế nào?
> 
> **A:**
> 
> - **Vấn đề:** `OFFSET` lớn. Postgres vẫn phải đọc và bỏ qua 1 triệu dòng đầu tiên (quét Index hoặc Table) để lấy 10 dòng cuối. Càng offset sâu càng chậm.
>     
> - **Giải pháp (Keyset Pagination / Cursor Pagination):**
>     
>     Thay vì dùng trang số (`page=100`), hãy dùng con trỏ (`last_id`).
>     

> SQL
> 
> ```
> -- Nhanh gấp ngàn lần vì dùng Index nhảy cóc tới ngay vị trí ID
> SELECT * FROM table WHERE id > 1000000 ORDER BY id LIMIT 10;
> ```

> [!QUESTION] Q: Khi nào nên dùng `UNION ALL` thay vì `OR`?
> 
> **A:**
> 
> Khi query trên các cột khác nhau có index riêng biệt.
> 
> `WHERE col_A = 1 OR col_B = 2`.
> 
> Đôi khi Postgres không dùng được Index hiệu quả. Tách thành 2 query `SELECT ... WHERE col_A = 1` UNION ALL `SELECT ... WHERE col_B = 2` có thể nhanh hơn vì nó chạy 2 cái Index Scan song song.