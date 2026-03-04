---
title: "System Design - Idempotency"
tags:
  - "system-design"
  - "payment"
  - "api"
  - "reliability"
  - "stripe"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Stripe Engineering: Idempotency (Designing Robust APIs)"
---

Stripe Engineering: Idempotency (Designing Robust APIs)

## 1. Vấn đề cốt lõi (The "Double Charge" Problem)

Trong hệ thống phân tán (Distributed Systems), giao tiếp qua mạng là không tin cậy.

> [!DANGER] Kịch bản lỗi
> 
> 1. Khách hàng bấm nút "Thanh toán $10".
>     
> 2. Server nhận được, trừ tiền thành công trong DB.
>     
> 3. Server gửi phản hồi "OK" về cho khách.
>     
> 4. **Mạng rớt!** Khách hàng không nhận được chữ "OK".
>     
> 5. App khách hàng (hoặc user sốt ruột) tự động **Retry** (gửi lại yêu cầu).
>     
> 6. Server nhận yêu cầu lần 2 -> **Trừ tiếp $10 nữa.**
>     
> 
> -> **Hậu quả:** Khách mất $20. Đây là lỗi nghiêm trọng nhất trong Banking.

**Idempotency (Tính lũy đẳng)** giải quyết việc này bằng toán học:

$$f(f(x)) = f(x)$$

_Thực hiện một hành động nhiều lần cũng chỉ cho ra kết quả giống hệt như thực hiện một lần._

---

## 2. Giải pháp: Idempotency Key

Stripe (và các chuẩn Payment hiện đại) yêu cầu Client (App/Frontend) gửi thêm một Header đặc biệt trong mỗi Request quan trọng (POST/PUT/PATCH).

Header: `Idempotency-Key: <UUID-V4>`

### Cơ chế hoạt động (Server-side Workflow)

Khi Server nhận được request:

1. **Check Key:** Tìm trong database bảng `idempotency_keys` xem cái UUID này đã tồn tại chưa.
    
2. **Case 1: Key chưa tồn tại (Request mới)**
    
    - Lưu Key vào DB với trạng thái `PROCESSING`.
        
    - Thực hiện xử lý nghiệp vụ (Trừ tiền, gọi Bank...).
        
    - Lưu kết quả trả về (Response Body) vào bản ghi của Key đó.
        
    - Update trạng thái `SUCCESS`.
        
    - Trả về kết quả cho Client.
        
3. **Case 2: Key đã tồn tại & Trạng thái SUCCESS (Request lặp lại)**
    
    - Server **KHÔNG** xử lý nghiệp vụ nữa (Không trừ tiền lại).
        
    - Lấy cái Response Body đã lưu trong quá khứ trả về y hệt cho Client.
        
    - _Client cảm thấy như request vừa được xử lý xong, dù thực ra là hàng fake (cached)._
        
4. **Case 3: Key đã tồn tại & Trạng thái PROCESSING (Race Condition)**
    
    - Một request khác cùng Key đang chạy nhưng chưa xong.
        
    - Trả về lỗi `409 Conflict` hoặc `429 Too Many Requests` để bảo Client chờ chút rồi quay lại.
        

---

## 3. Database Schema Design

Để thực hiện điều này, ta cần một bảng lưu trữ keys. Quan trọng nhất là ràng buộc **Unique Constraint** trên `key` và `user_id`.

SQL

```
CREATE TABLE idempotency_keys (
    id bigserial PRIMARY KEY,
    key UUID NOT NULL, -- Client sinh ra
    user_id BIGINT NOT NULL, -- Scope theo user để bảo mật
    request_params JSONB, -- Hash của params để check xem client có đổi ý không
    response_body JSONB, -- Lưu kết quả để trả lại (Cache)
    status_code INT, -- HTTP Status (200, 400, 500)
    recovery_point VARCHAR(50), -- Dùng cho các giao dịch phức tạp (Advanced)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Đảm bảo mỗi user chỉ có 1 key duy nhất
    UNIQUE (user_id, key)
);
```

---

## 4. Code Implementation (Golang Pattern)

Cách triển khai "Atomic" sử dụng Transaction của Database (Postgres) để đảm bảo an toàn tuyệt đối.

Go

```
func (s *Server) CreateCharge(ctx context.Context, req ChargeRequest, idemKey string) (*ChargeResponse, error) {
    // 1. Bắt đầu Transaction
    tx, _ := s.db.BeginTx(ctx, nil)
    defer tx.Rollback()

    // 2. Thử Insert Key (Dùng ON CONFLICT để check)
    // "recovery_point" giúp ta biết transaction trước đó chết ở đoạn nào
    var savedResponse []byte
    err := tx.QueryRow(`
        INSERT INTO idempotency_keys (key, user_id, status) 
        VALUES ($1, $2, 'PROCESSING')
        ON CONFLICT (key, user_id) DO NOTHING
        RETURNING response_body
    `, idemKey, req.UserID).Scan(&savedResponse)

    // Case: Key đã tồn tại (Insert không trả về row nào)
    if err == sql.ErrNoRows {
        // Query lại lấy response cũ trả về luôn
        return GetSavedResponse(idemKey), nil
    }

    // 3. Xử lý nghiệp vụ (Chỉ chạy khi key mới)
    result, err := s.bankGateway.Charge(req.Amount)
    if err != nil {
        return nil, err
    }

    // 4. Update kết quả vào bảng Idempotency
    tx.Exec(`
        UPDATE idempotency_keys 
        SET response_body = $1, status = 'SUCCESS' 
        WHERE key = $2
    `, result, idemKey)

    tx.Commit()
    return result, nil
}
```

---

## 5. Những bài học xương máu (Critical Details)

### A. Idempotency Key tồn tại bao lâu?

Stripe chỉ lưu key trong **24 giờ**.

Sau 24h, nếu Client gửi lại key cũ -> Server sẽ coi như key mới và trừ tiền lần nữa. Tại sao?

- Để tiết kiệm DB.
    
- Transaction banking cũ quá 24h thường được coi là fail hoặc cần tạo giao dịch mới.
    

### B. Kiểm tra Params (Request Mismatch)

Hacker hoặc Code lỗi có thể gửi:

1. Request 1: Key=`UUID-A`, Amount=`$10`.
    
2. Request 2: Key=`UUID-A`, Amount=`$100`. (Cùng Key nhưng đổi tiền).
    

Server phải lưu hash của params lần đầu. Nếu lần 2 gửi lên cùng Key nhưng hash khác -> **Báo lỗi ngay** (400 Bad Request - Parameter Mismatch).

### C. Lỗi ở bước cuối cùng (The Atomic Phase)

> **Hỏi:** Điều gì xảy ra nếu Server trừ tiền xong ($10), nhưng sập nguồn _trước khi_ kịp lưu `response_body` vào bảng `idempotency_keys`?

**Đáp (Stripe Way):**

Đây là lý do bảng `idempotency_keys` và bảng `transactions` (Lịch sử giao dịch) nên nằm trong **cùng một Database Transaction (ACID)**.

- `BEGIN`
    
- Insert Transaction ($10).
    
- Update Idempotency Key (SUCCESS).
    
- `COMMIT`.
    
    -> Nếu sập giữa chừng, cả 2 đều Rollback. Tiền không mất, Key không được đánh dấu là xong. Client retry sẽ làm lại từ đầu an toàn.
    

---

## 6. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Tại sao không dùng Redis cho Idempotency Key cho nhanh?
> 
> **A:** Redis rất nhanh, nhưng nó **không đảm bảo ACID** cùng với Database chính (Postgres).
> 
> Nếu Redis lưu "Đang xử lý", nhưng Postgres sập, trạng thái sẽ bị lệch (Inconsistent). Với dữ liệu tiền tệ, ta chấp nhận chậm một chút (dùng Postgres) để đảm bảo **Consistency** (Tính nhất quán) tuyệt đối. Redis chỉ nên dùng làm cache lớp ngoài để chặn spam (Rate Limiting).

> [!QUESTION] Q: Idempotency có áp dụng cho GET request không?
> 
> **A:** Theo chuẩn RESTful, `GET` bản chất đã là **Idempotent** và **Safe** (Không thay đổi dữ liệu). Bạn gọi GET 1000 lần thì dữ liệu server vẫn thế. Nên không cần header `Idempotency-Key` cho GET. Nó chỉ cần thiết cho `POST` (Tạo mới) và `PATCH` (Sửa đổi không idempotent).