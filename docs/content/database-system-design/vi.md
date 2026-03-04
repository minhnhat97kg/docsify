---
title: "Database System Design: Scalability & Reliability"
tags:
  - "system-design"
  - "database"
  - "scalability"
  - "reliability"
  - "sharding"
  - "replication"
  - "microservices"
date: "2026-03-04"
author: "nathan.huynh"
summary: "---"
---

---

# Database System Design: Scalability & Reliability

## 1. Replication (Sao chép dữ liệu)

> [!SUMMARY] Mục tiêu
> 
> Tăng khả năng sẵn sàng (High Availability) và phân tải đọc (Read Scalability).
> 
> Không một ngân hàng nào chạy trên 1 server DB duy nhất. Nếu server đó cháy, ngân hàng ngừng hoạt động.

### Các mô hình Replication

1. **Single Leader (Master-Slave):**
    
    - **Master:** Nhận lệnh Ghi (Write) + Đọc.
        
    - **Slaves:** Chỉ nhận lệnh Đọc. Dữ liệu được sync từ Master sang.
        
    - _Ưu điểm:_ Đơn giản, đảm bảo Consistency (trên Master).
        
    - _Nhược điểm:_ Master là điểm nghẽn (Single point of failure) cho lệnh Ghi.
        
2. **Multi-Leader (Master-Master):**
    
    - Nhiều node cùng nhận lệnh Ghi.
        
    - _Ưu điểm:_ Ghi nhanh hơn, chịu lỗi tốt hơn.
        
    - _Nhược điểm:_ **Xung đột dữ liệu** (Conflict Resolution) cực khó. (Ví dụ: Cùng lúc A sửa số dư thành 100, B sửa thành 200 tại 2 node khác nhau -> Ai đúng?). _Ít dùng trong Core Banking._
        

### Sync vs. Async Replication (Quan trọng)

- **Synchronous (Đồng bộ):** Master chờ Slave ghi xong mới báo thành công cho Client.
    
    - _Bank:_ Bắt buộc dùng cho dữ liệu tiền tệ (Zero Data Loss).
        
- **Asynchronous (Bất đồng bộ):** Master ghi xong báo thành công luôn. Slave tự copy sau.
    
    - _Bank:_ Dùng cho Log, Lịch sử giao dịch (Chấp nhận lag vài giây).
        

---

## 2. Sharding (Phân mảnh ngang)

Khác với **Partitioning** (chia bảng trong 1 server), **Sharding** là chia dữ liệu ra **nhiều server vật lý khác nhau**.

> [!DANGER] Khi nào cần Sharding?
> 
> Chỉ khi dữ liệu quá lớn (TB/PB) mà một máy chủ mạnh nhất không thể chứa nổi hoặc không chịu nổi tải Write.
> 
> **Đừng Sharding quá sớm (Premature Optimization).** Nó làm hệ thống phức tạp gấp 10 lần.

### Chiến lược chọn Sharding Key (Vô cùng quan trọng)

Giả sử ta Sharding bảng `transactions`.

1. **Theo User ID (Hash Based):**
    
    - User A -> Shard 1.
        
    - User B -> Shard 2.
        
    - _Ưu điểm:_ Load Balancing đều.
        
    - _Nhược điểm:_ Query tổng hợp (Lấy sao kê toàn hệ thống) phải query tất cả Shard rồi gộp lại (Scatter-Gather) -> Rất chậm.
        
2. **Theo Geo/Location:**
    
    - User VN -> Shard VN.
        
    - User US -> Shard US.
        
    - _Ưu điểm:_ Dữ liệu gần người dùng (Low Latency).
        
    - _Nhược điểm:_ Hotspot (Shard VN có thể quá tải trong khi Shard Lào vắng tanh).
        

---

# Database System Design: Data Integrity Patterns

## 1. Idempotency (Tính lũy đẳng) - _Sống còn trong Payment_

> [!SUMMARY] Vấn đề
> 
> Mạng bị lag. App gửi lệnh "Chuyển tiền" (Request 1). Server xử lý xong nhưng phản hồi bị mất trên đường về.
> 
> App tưởng lỗi -> Retry gửi lại lệnh "Chuyển tiền" (Request 2).
> 
> -> **Hậu quả:** Khách hàng bị trừ tiền 2 lần.

### Giải pháp: Idempotency Key

Trong Database, tạo một bảng riêng để theo dõi các key này.

SQL

```
CREATE TABLE processed_requests (
    idempotency_key UUID PRIMARY KEY,
    user_id BIGINT,
    request_payload JSONB,
    response_payload JSONB,
    status VARCHAR(20), -- 'PROCESSING', 'SUCCESS', 'FAILED'
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Luồng xử lý:**

1. Client gửi Request kèm Header `Idempotency-Key: uuid-gen-tu-client`.
    
2. Server nhận Request:
    
    - `INSERT` key vào bảng `processed_requests`.
        
    - Nếu lỗi **Duplicate Key** -> Nghĩa là request này đã/đang xử lý -> Trả về kết quả cũ (hoặc báo "Đang xử lý") mà **KHÔNG** thực hiện trừ tiền lần 2.
        
    - Nếu Insert thành công -> Thực hiện trừ tiền -> Update trạng thái `SUCCESS`.
        

## 2. Transactional Outbox Pattern (Dual Write Problem)

Vấn đề kinh điển của Microservices:

1. Lưu giao dịch vào DB (Postgres).
    
2. Bắn event sang Kafka để báo cho service khác (Email, Loyalty).
    

**Lỗi:** Bước 1 xong, sập nguồn trước khi làm bước 2. -> DB có tiền, nhưng không có Email, không tích điểm. Dữ liệu không nhất quán.

### Giải pháp: Outbox Table

Thay vì bắn Kafka ngay, hãy lưu message đó vào chính Database (cùng transaction với nghiệp vụ).

SQL

```
BEGIN;
-- 1. Nghiệp vụ chính
INSERT INTO transactions (...) VALUES (...);

-- 2. Lưu event vào bảng Outbox (Cùng transaction -> Đảm bảo Atomicity)
INSERT INTO outbox_events (topic, payload, status) 
VALUES ('transaction_created', '{...}', 'PENDING');

COMMIT;
```

Sau đó, có một tiến trình riêng (Worker/CDC) đọc bảng `outbox_events` để bắn sang Kafka. Nếu bắn thành công thì xóa dòng trong Outbox.

---

## 3. Soft Delete vs. Hard Delete

Trong Bank, dữ liệu **không bao giờ được phép biến mất hoàn toàn** (để phục vụ Audit/Kiểm toán).

- **Hard Delete:** `DELETE FROM users WHERE id = 1`. (Mất vĩnh viễn).
    
- **Soft Delete:** Thêm cột `deleted_at` hoặc `is_deleted`.
    

SQL

```
-- Thay vì DELETE, ta Update
UPDATE users SET deleted_at = NOW() WHERE id = 1;

-- Khi Query, luôn phải nhớ filter
SELECT * FROM users WHERE deleted_at IS NULL;
```

> [!TIP] Partial Index cho Soft Delete
> 
> Để query nhanh và không đánh index cho các dòng đã xóa (tiết kiệm không gian):
> 
> SQL
> 
> ```
> CREATE INDEX idx_users_active ON users (email) WHERE deleted_at IS NULL;
> ```

---

## 4. Surrogate Key vs. Natural Key (Chọn ID thế nào?)

### A. Natural Key (Khóa tự nhiên)

Dùng dữ liệu thực tế làm ID: Số CCCD, Email, Số điện thoại.

- _Nhược điểm:_ Dữ liệu này có thể thay đổi (User đổi email) hoặc trùng lặp bất ngờ. **Không nên dùng làm Primary Key.**
    

### B. Surrogate Key (Khóa nhân tạo)

1. **Auto Increment (Serial/BigSerial):** `1, 2, 3...`
    
    - _Ưu điểm:_ Gọn nhẹ (8 bytes), Insert nhanh (B-Tree luôn append vào cuối).
        
    - _Nhược điểm:_ Lộ quy mô hệ thống (Hacker tạo user thấy ID=1000, hôm sau ID=1005 -> Biết web vắng). Khó merge dữ liệu từ nhiều Shard.
        
2. **UUID (v4):** `a0eebc99-9c0b...`
    
    - _Ưu điểm:_ Duy nhất toàn cầu, bảo mật, dễ sharding.
        
    - _Nhược điểm:_ Quá dài (16 bytes = 128 bit). Ngẫu nhiên hoàn toàn -> Gây **phân mảnh Index** (Random I/O) khi Insert. Hiệu năng Insert kém Serial rất nhiều.
        
3. **TSID / ULID (Sortable UUID) - _Khuyên dùng cho Modern App_**
    
    - Kết hợp Timestamp + Random.
        
    - _Ưu điểm:_ Duy nhất như UUID, nhưng **sắp xếp được theo thời gian** (như Serial).
        
    - Giúp B-Tree Index hoạt động hiệu quả (Append-only pattern).
        

Go

```
// Ví dụ dùng thư viện ksuid hoặc ulid trong Go
id := ulid.Make()
fmt.Println(id) // 01ARZ3NDEKTSV4RRFFQ69G5FAV (Vừa unique, vừa sort được)
```

---

## 5. Audit Logging (Nhật ký thay đổi)

Ai đã sửa số dư của khách hàng? Sửa từ bao nhiêu thành bao nhiêu? Vào lúc nào?

Không thể dựa vào log file (text) vì khó query. Cần lưu trong DB.

**Thiết kế bảng Audit Log:**

SQL

```
CREATE TABLE audit_logs (
    id bigserial PRIMARY KEY,
    table_name text,
    record_id bigint,
    action text, -- INSERT, UPDATE, DELETE
    old_data jsonb, -- Dữ liệu trước khi sửa
    new_data jsonb, -- Dữ liệu mới
    changed_by_user_id bigint,
    created_at timestamptz DEFAULT NOW()
);
```

- **Implementation:** Có thể dùng **Database Triggers** (tự động lưu khi data đổi) hoặc xử lý tại tầng **Application Code**. (Bank thường dùng Trigger hoặc CDC - Change Data Capture để đảm bảo không ai "luồn lách" sửa data mà bypass qua code).