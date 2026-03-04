---
title: "Database - Table Partitioning (Range, Hash)"
tags:
  - "database"
  - "postgresql"
  - "partitioning"
  - "big-data"
  - "performance"
  - "system-design"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "> > Khi một bảng (như của ngân hàng) lớn tới hàng trăm GB hoặc vài TB: > > 1. Index phình to: Index B-Tree không còn nhét vừa RAM -> Truy vấn chậm (Disk I/O). > > 2. Maintenance ác mộng: Vacuum,..."
---

## 1. Tổng quan (Mental Model)

> [!SUMMARY] Vấn đề & Giải pháp
> 
> Khi một bảng (như `transactions` của ngân hàng) lớn tới **hàng trăm GB hoặc vài TB**:
> 
> 1. **Index phình to:** Index B-Tree không còn nhét vừa RAM -> Truy vấn chậm (Disk I/O).
>     
> 2. **Maintenance ác mộng:** Vacuum, Reindex mất hàng ngày trời.
>     
> 3. **Xóa dữ liệu cũ:** `DELETE FROM logs WHERE date < '2023'` là thao tác cực kỳ tốn kém (gây bloat).
>     
> 
> **Partitioning** là kỹ thuật "Chia để trị". Về mặt Logic, App vẫn thấy 1 bảng to. Về mặt Vật lý, Postgres chia nó thành nhiều bảng nhỏ (Partitions) lưu ở các file riêng biệt.

### Vũ khí bí mật: Partition Pruning

Khi bạn Query: `SELECT * FROM transactions WHERE date = '2024-02-01'`.

Postgres đủ thông minh để **chỉ tìm trong bảng con tháng 2/2024**. Nó bỏ qua (Prune) hoàn toàn các bảng tháng 1, tháng 3... -> Tốc độ nhanh gấp N lần.

---

## 2. Các loại Partitioning phổ biến

### A. Range Partitioning (Phân chia theo dải)

- **Use Case:** Dữ liệu Time-series (Lịch sử giao dịch, Audit Logs, Sao kê).
    
- **Cách chia:** Theo ngày, tháng, năm.
    

SQL

```sql
-- 1. Tạo bảng cha (Master Table)
-- Lưu ý: Không lưu dữ liệu vào bảng này
CREATE TABLE transactions (
    id bigserial,
    user_id int,
    amount decimal,
    created_at timestamptz,
    PRIMARY KEY (id, created_at) -- Partition Key BẮT BUỘC phải nằm trong PK
) PARTITION BY RANGE (created_at);

-- 2. Tạo các bảng con (Partitions)
-- Bảng tháng 1
CREATE TABLE transactions_2024_01 PARTITION OF transactions
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- Bảng tháng 2
CREATE TABLE transactions_2024_02 PARTITION OF transactions
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- App chỉ cần Insert vào 'transactions', Postgres tự điều hướng vào đúng bảng con.
```

### B. Hash Partitioning (Phân chia theo băm)

- **Use Case:** Dữ liệu không có tính thời gian, cần chia đều tải (Load Balancing). Ví dụ: Bảng `users` quá lớn (100 triệu users).
    
- **Cách chia:** Dựa trên Modulo của ID.
    

SQL

```sql
-- Tạo bảng cha chia làm 4 phần
CREATE TABLE users (
    uuid uuid PRIMARY KEY,
    name text
) PARTITION BY HASH (uuid);

-- Tạo 4 bảng con
CREATE TABLE users_p0 PARTITION OF users FOR VALUES WITH (MODULUS 4, REMAINDER 0);
CREATE TABLE users_p1 PARTITION OF users FOR VALUES WITH (MODULUS 4, REMAINDER 1);
CREATE TABLE users_p2 PARTITION OF users FOR VALUES WITH (MODULUS 4, REMAINDER 2);
CREATE TABLE users_p3 PARTITION OF users FOR VALUES WITH (MODULUS 4, REMAINDER 3);
```

---

## 3. Lợi ích bảo trì (The "Killer Feature" for Bank)

Trong ngân hàng, quy định thường là: "Lưu nóng 1 năm, sau đó chuyển sang kho lạnh (Archive)".

Nếu không dùng Partition:

- Chạy `DELETE FROM transactions WHERE date < '2023-01-01'`.
    
- **Hậu quả:** Treo DB, transaction log phình to, bảng bị Bloat khủng khiếp, phải chạy Vacuum Full sau đó.
    

Nếu dùng Range Partition:

SQL

```sql
-- 1. Gỡ bảng cũ ra khỏi bảng cha (Nhanh như chớp mắt - Metadata operation)
ALTER TABLE transactions DETACH PARTITION transactions_2023_01;

-- 2. Lúc này bảng transactions_2023_01 thành bảng độc lập.
-- Bạn có thể dump nó ra file rồi Drop, hoặc nén lại.
-- Không ảnh hưởng gì đến hiệu năng hệ thống đang chạy.
```

---

## 4. Những cái bẫy (Pitfalls) khi phỏng vấn

> [!WARNING] Primary Key Constraint
> 
> **Q:** Tôi muốn `id` là Primary Key (Unique) trên toàn bộ bảng to, nhưng tôi partition theo `created_at`. Có được không?
> 
> **A:** **Không.**
> 
> Trong Postgres, Partition Key (`created_at`) **BẮT BUỘC** phải là một phần của Primary Key.
> 
> -> PK phải là composite: `PRIMARY KEY (id, created_at)`.
> 
> _Lý do:_ Postgres không thể đảm bảo tính duy nhất của `id` trên toàn cầu nếu không check tất cả các partition (điều này quá chậm).

> [!WARNING] Global Index
> 
> **Q:** Postgres có hỗ trợ Global Index (Index trỏ tới tất cả partition) không?
> 
> **A:** Hiện tại là **KHÔNG** (khác với Oracle).
> 
> Postgres chỉ tạo **Local Index** trên từng bảng con.
> 
> -> Nếu bạn tìm kiếm `WHERE id = 123` (không có ngày tháng), Postgres buộc phải quét Index của **TẤT CẢ** các bảng con (Scatter Gather) -> Chậm hơn bảng thường.
> 
> _Bài học:_ Luôn cố gắng kèm Partition Key vào câu query (`WHERE id=123 AND date='...'`).

---

## 5. Chiến lược tự động hóa (pg_partman)

Không ai ngồi tạo tay bảng mới mỗi tháng cả. Trong thực tế, chúng ta dùng extension `pg_partman`.

SQL

```sql
SELECT partman.create_parent(
    p_parent_table => 'public.transactions',
    p_control => 'created_at',
    p_interval => '1 month',
    p_premake => 3 -- Tạo sẵn trước 3 tháng tương lai
);
-- Cronjob sẽ tự động chạy để tạo bảng mới và detach bảng cũ.
```