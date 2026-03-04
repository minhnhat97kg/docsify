---
title: "System Design - E-Wallet (High Consistency)"
tags:
  - "system-design"
  - "architecture"
  - "fintech"
  - "database"
  - "microservices"
  - "security"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Trước khi vẽ hình, ta phải chốt các ràng buộc:"
---

## 1. Phân tích Yêu cầu (Requirements)

Trước khi vẽ hình, ta phải chốt các ràng buộc:

- **Functional:** Nạp tiền (Top-up), Chuyển tiền (P2P), Thanh toán (Payment), Rút tiền.
    
- **Non-Functional:**
    
    - **Strong Consistency:** Tiền không được tự sinh ra hay mất đi (Quan trọng nhất).
    - **Availability:** Hệ thống phải luôn online (99.99%).
    - **Security:** Tuân thủ PCI-DSS, mã hóa dữ liệu nhạy cảm.
    - **Scale:** 1 triệu Active Users, đỉnh điểm 1000 TPS (Transactions Per Second).
        

---

## 2. High-Level Architecture

Chúng ta sẽ sử dụng **Microservices Architecture** để scale từng phần riêng biệt.

Các service chính:

1. **API Gateway:** Cửa ngõ, Rate Limiting, xác thực JWT.
    
2. **Wallet Core Service:** Trái tim hệ thống. Quản lý số dư (Balance) và Ledger (Sổ cái).
    
3. **Payment Gateway Service:** Kết nối với Ngân hàng/Visa/Mastercard.
    
4. **Transaction History Service:** Lưu lịch sử giao dịch (để user xem lại).
    
5. **Notification Service:** Gửi Push/SMS/Email.
    

---

## 3. Database Design (Trái tim của vấn đề)

Đây là nơi "sống còn" của ví điện tử.

### Quyết định 1: SQL hay NoSQL?

- **Chọn:** **RDBMS (PostgreSQL/MySQL)**.
    
- **Lý do:**
    
    - Cần **ACID Transactions** tuyệt đối.
        
    - PostgreSQL xử lý concurrency và locking cực tốt (`SELECT FOR UPDATE`).
        
    - NoSQL (như MongoDB) chỉ phù hợp lưu _Lịch sử giao dịch_ (Transaction Logs) vì nó scale write tốt, nhưng không đảm bảo ACID mạnh bằng SQL cho việc tính toán số dư.
        

### Quyết định 2: Double-Entry Bookkeeping (Kế toán kép)

Đừng bao giờ thiết kế bảng `User` có cột `current_balance` rồi cộng trừ trực tiếp (`balance = balance - 100`). Rất dễ sai sót và khó truy vết.

**Mô hình chuẩn Banking:** Bảng `Ledger` (Sổ cái).

Mọi giao dịch đều sinh ra 2 dòng:

1. **Debit (Nợ):** Trừ tiền tài khoản A.
    
2. **Credit (Có):** Cộng tiền tài khoản B (hoặc tài khoản trung gian của hệ thống).
    
    -> Tổng của Debit và Credit luôn bằng 0.
    - [~] 

``` sql
-- Table: Balances (Snapshot số dư để query cho nhanh)
CREATE TABLE balances (
    user_id UUID PRIMARY KEY,
    amount DECIMAL(19, 4) NOT NULL,
    currency VARCHAR(3) DEFAULT 'VND',
    updated_at TIMESTAMP
);

-- Table: Ledger_Entries (Sự thật duy nhất - Source of Truth)
CREATE TABLE ledger_entries (
    id UUID PRIMARY KEY,
    transaction_id UUID, -- Link tới giao dịch
    account_id UUID,     -- Tài khoản bị tác động
    direction VARCHAR(10), -- 'DEBIT' hoặc 'CREDIT'
    amount DECIMAL(19, 4),
    balance_after DECIMAL(19, 4) -- Số dư sau khi đổi (Snapshot)
);
```

---

## 4. Xử lý Concurrency (Cuộc chiến chống Race Condition)

**Kịch bản:** Hacker gửi 2 request rút tiền cùng lúc. Nếu không chặn, tài khoản có 100k có thể rút được 200k.

### Giải pháp 1: Pessimistic Locking (Khuyên dùng cho Core Banking)

Sử dụng khóa dòng trong Database.

``` sql
BEGIN;
-- Khóa dòng này lại, không cho ai đọc/ghi cho đến khi Commit
SELECT amount FROM balances WHERE user_id = 'user_A' FOR UPDATE; 

-- Kiểm tra logic
IF amount < 100 THEN ROLLBACK;

-- Update
UPDATE balances SET amount = amount - 100 WHERE user_id = 'user_A';
COMMIT;
```

- _Ưu điểm:_ An toàn tuyệt đối.
    
- _Nhược điểm:_ Chậm nếu traffic quá cao vào cùng 1 tài khoản (Hot Account).
    

### Giải pháp 2: Optimistic Locking (Dùng cho ví cá nhân)

Dùng cột `version`.

SQL

```
UPDATE balances 
SET amount = amount - 100, version = version + 1 
WHERE user_id = 'user_A' AND version = 5;
```

- Nếu kết quả trả về là `0 rows affected` (do version đã bị đứa khác đổi lên 6 rồi) -> Báo lỗi cho User "Vui lòng thử lại".
    

---

## 5. Distributed Transactions (Saga Pattern)

**Kịch bản:** Chuyển tiền từ Ví MoMo sang Tài khoản Ngân hàng VCB.

Đây là giao dịch phân tán giữa 2 hệ thống khác nhau. Không thể dùng transaction DB thông thường.

Sử dụng **Orchestration Saga** (Có một nhạc trưởng điều phối).

1. **Wallet Service:** Trừ tiền ví User (Local Transaction). -> **Pending**.
    
2. **Payment Service:** Gọi API VCB để cộng tiền.
    
    - _Nếu VCB thành công:_ Wallet Service update trạng thái -> **Success**.
        
    - _Nếu VCB thất bại:_ Wallet Service thực hiện **Compensating Transaction** (Giao dịch bù) -> Cộng hoàn tiền lại cho User -> **Failed**.
        

> [!TIP] Transactional Outbox
> 
> Để đảm bảo bước 1 và bước 2 không bị lệch pha (Trừ tiền rồi mà server sập không gọi được VCB), ta dùng **Transactional Outbox Pattern** đã học. Lưu event "Cần gọi VCB" vào bảng `outbox` cùng lúc trừ tiền.

---

## 6. Scalability & Performance

Hệ thống phải chịu tải 1000 TPS.

1. **Read/Write Split:**
    
    - Tất cả lệnh trừ tiền/cộng tiền (Write) đi vào **Master DB**.
        
    - User mở app xem số dư (Read) đi vào **Replica DB** hoặc **Redis Cache**.
        
2. **Sharding:**
    
    - Khi bảng `Ledger` quá lớn (tỷ dòng), ta chia nhỏ (Shard) theo `user_id`. User 1-1tr ở DB Shard 1, User 1tr-2tr ở DB Shard 2.
        
3. **Caching Strategy:**
    
    - Cache `User Profile` và `Current Balance` trong Redis.
        
    - Khi có giao dịch thay đổi số dư -> Invalidate Cache ngay lập tức (Cache-Aside).
        

---

## 7. Security (Bảo mật)

1. **Data at Rest:** Dùng **AWS KMS** và cơ chế **Envelope Encryption** để mã hóa cột `balance` và thông tin cá nhân (PII) trong Database.
    
2. **Communication:** Dùng **mTLS** (Mutual TLS) cho kết nối giữa các Microservices nội bộ.
    
3. **Idempotency:**
    
    - Mọi API chuyển tiền phải bắt buộc Client gửi kèm `idempotency_key` (UUID).
        
    - Server check Redis, nếu key này đã xử lý rồi -> Trả về kết quả cũ, không trừ tiền lần 2.
        

---

## Tổng kết

Hệ thống Ví điện tử này hội tụ đủ tinh hoa của Backend:

- **Consistency:** PostgreSQL + Pessimistic Lock.
    
- **Reliability:** Saga Pattern + Transactional Outbox.
    
- **Security:** KMS + VPC Private Subnets.
    
- **Scalability:** Microservices + Redis + Sharding.
    

Đây là một thiết kế "Reference Architecture" giúp bạn tự tin trả lời phỏng vấn ở mức độ Senior/Architect.

**Lời cuối cùng từ Gemini:**

Hành trình học tập của chúng ta đã đi qua tất cả các tầng của một hệ thống hiện đại. Bạn đã có kiến thức, có tư duy, và có cả "vũ khí" (code patterns).

Hãy tự tin apply vào các vị trí Senior. Nếu cần review CV hay Mock Interview thêm, tôi luôn ở đây.

Chúc bạn may mắn! 🚀
