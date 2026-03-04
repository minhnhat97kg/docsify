---
title: "Database - Locking: Pessimistic vs Optimistic"
tags:
  - "database"
  - "postgresql"
  - "locking"
  - "concurrency"
  - "performance"
  - "interview"
  - "backend"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Khi nhiều transaction cùng muốn sửa một dòng dữ liệu (ví dụ: cùng trừ tiền một tài khoản), ta cần cơ chế để quyết định ai được làm trước, ai phải chờ, hoặc ai bị từ chối."
---

## 1. Tổng quan (The Dilemma)

Khi nhiều transaction cùng muốn sửa một dòng dữ liệu (ví dụ: cùng trừ tiền một tài khoản), ta cần cơ chế để quyết định ai được làm trước, ai phải chờ, hoặc ai bị từ chối.

Có 2 chiến lược đối lập:

1. **Pessimistic (Bi quan):** "Đời là bể khổ, kiểu gì cũng có tranh chấp". -> Khóa ngay từ đầu.
    
2. **Optimistic (Lạc quan):** "Đời vẫn đẹp, chắc ít khi tranh chấp đâu". -> Cứ làm, cuối cùng check lại.
    

---

## 2. Pessimistic Locking (Khóa Bi Quan)

Đây là chiến lược mặc định và an toàn nhất cho các nghiệp vụ **Core Banking (Chuyển tiền, Thanh toán)**.

> [!SUMMARY] Cơ chế
> 
> Sử dụng tính năng Lock của Database.
> 
> Khi Transaction A đọc dữ liệu để chuẩn bị sửa, nó sẽ **giữ khóa** dòng đó. Transaction B muốn đọc/sửa dòng đó sẽ bị **treo (block)** cho đến khi A xong việc (Commit/Rollback).

### Cú pháp: `SELECT ... FOR UPDATE`

SQL

```sql
BEGIN;

-- 1. Đọc số dư và KHÓA dòng này lại.
-- Nếu có ai đang giữ khóa, lệnh này sẽ CHỜ (Wait) đến khi lấy được khóa.
SELECT balance FROM accounts WHERE id = 101 FOR UPDATE;

-- 2. Tính toán logic (trong code backend)
-- ... (balance = 1000 - 100) ...

-- 3. Cập nhật
UPDATE accounts SET balance = 900 WHERE id = 101;

COMMIT; -- 4. Nhả khóa. Các transaction khác đang chờ giờ mới được vào.
```

### Các biến thể của `FOR UPDATE`

- `FOR UPDATE`: Khóa hoàn toàn (ngăn cả update và delete).
    
- `FOR SHARE`: Khóa không cho người khác sửa/xóa, nhưng cho phép người khác cũng `FOR SHARE` (dùng khi chỉ muốn đảm bảo dòng này không bị đổi giá trị khi đang đọc).
    
- `NOWAIT`: Nếu dòng đang bị khóa, **báo lỗi ngay** chứ không chờ.
    
    - `SELECT ... FOR UPDATE NOWAIT;` -> "Tao bận lắm, không chờ được".
        
- `SKIP LOCKED`: Bỏ qua các dòng đang bị khóa (Dùng cho hàng đợi công việc - Job Queue).
    

> [!DANGER] Rủi ro: Deadlock (Khóa chết)
> 
> - Tx A khóa User 1, chờ User 2.
>     
> - Tx B khóa User 2, chờ User 1.
>     
> - -> Cả 2 chờ nhau mãi mãi. Postgres sẽ phát hiện và Kill 1 thằng.
>     
> - **Giải pháp:** Luôn lock các resource theo một **thứ tự nhất định** (ví dụ: Lock ID nhỏ trước, ID lớn sau).
>     

---

## 3. Optimistic Locking (Khóa Lạc Quan)

Dùng cho các nghiệp vụ ít va chạm hơn (Cập nhật thông tin User, CMS, Đặt vé).

> [!SUMMARY] Cơ chế
> 
> **Không dùng Lock của Database** (giúp giảm tải DB connection).
> 
> Thay vào đó, dùng một cột `version` (hoặc `updated_at`) để kiểm soát phiên bản dữ liệu ở tầng Ứng dụng (Application Level).

### Cách hoạt động

1. **Đọc:** Lấy dữ liệu kèm theo `version`.
    
2. **Sửa:** Tính toán trong code.
    
3. **Ghi:** Khi Update, kiểm tra xem `version` trong DB có còn giống `version` lúc mình đọc không.
    

### SQL Implementation

**Bước 1: Đọc**

SQL

```sql
SELECT id, balance, version FROM accounts WHERE id = 101;
-- Giả sử trả về: balance=1000, version=5
```

**Bước 2: Update (Logic Check)**

SQL

```sql
-- Chỉ update nếu version vẫn là 5
UPDATE accounts
SET balance = 900,
    version = version + 1 -- Tăng version lên 6
WHERE id = 101 AND version = 5;
```

### Code Golang xử lý Optimistic Lock

Go

```go
func UpdateBalanceOptimistic(db *sql.DB, id int, amount int) error {
    for {
        // 1. Đọc dữ liệu hiện tại
        var currentVer int
        err := db.QueryRow("SELECT version FROM accounts WHERE id = $1", id).Scan(&currentVer)
        if err != nil { return err }

        // 2. Cố gắng update
        res, err := db.Exec(`
            UPDATE accounts
            SET balance = balance + $1, version = version + 1
            WHERE id = $2 AND version = $3`,
            amount, id, currentVer)

        if err != nil { return err }

        // 3. Kiểm tra xem có dòng nào được update không
        rowsAffected, _ := res.RowsAffected()
        if rowsAffected == 0 {
            // Không update được dòng nào -> Có người khác đã sửa trước đó (Version mismatch)
            // QUYẾT ĐỊNH: Retry (thử lại) hay Báo lỗi?
            continue // Ở đây chọn Retry
        }

        return nil // Thành công
    }
}
```

---

## 4. So sánh & Lựa chọn (Interview Cheat Sheet)

|**Đặc điểm**|**Pessimistic Locking (FOR UPDATE)**|**Optimistic Locking (version)**|
|---|---|---|
|**Cơ chế**|Database Lock (Khóa cứng).|Application Versioning (Logic mềm).|
|**Hiệu năng**|Thấp hơn (do phải chờ đợi/blocking).|Cao hơn (không ai chặn ai).|
|**Xung đột**|Ngăn chặn xung đột xảy ra.|Phát hiện xung đột khi Commit.|
|**Rủi ro**|**Deadlock**. Giữ connection lâu.|**Lãng phí tài nguyên** nếu phải retry liên tục.|
|**Use Case Bank**|Chuyển tiền, Rút tiền (High Integrity).|Đổi mật khẩu, Cập nhật địa chỉ, Form nhập liệu dài.|

> [!QUESTION] Câu hỏi phỏng vấn: "Tại sao không dùng Pessimistic Lock cho màn hình Edit Profile của Admin?"
> 
> **A:** Vì User có thể mở màn hình Edit rồi đi... uống cafe 30 phút.
> 
> Nếu dùng `SELECT FOR UPDATE` lúc mở form, dòng dữ liệu đó sẽ bị khóa 30 phút. Không ai khác xem hay sửa được.
> 
> -> Phải dùng Optimistic Lock. Khi User bấm Save sau 30 phút, ta check version xem dữ liệu có bị ai đổi trong lúc đó không.