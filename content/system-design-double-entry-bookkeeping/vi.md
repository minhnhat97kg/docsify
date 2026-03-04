---
title: "System Design - Double Entry Bookkeeping"
tags:
  - "system-design"
  - "fintech"
  - "accounting"
  - "database"
  - "architecture"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Trong lập trình cơ bản, khi cộng tiền cho user, ta thường viết:"
---

## 1. Nguyên lý cốt lõi: Không có tiền "tự sinh ra"

Trong lập trình cơ bản, khi cộng tiền cho user, ta thường viết:

`UPDATE users SET balance = balance + 100 WHERE id = 1;`

> [!DANGER] Vấn đề của Single Entry (Kế toán đơn)
> 
> 100 đồng này ở đâu ra? Tại sao user lại có nó?
> 
> Nếu có lỗi hệ thống cộng nhầm thành 1000 đồng, làm sao truy vết?
> 
> -> **Trong Fintech, tiền không bao giờ tự sinh ra hay tự mất đi. Nó chỉ DI CHUYỂN từ tài khoản này sang tài khoản khác.**

**Double Entry Bookkeeping (Kế toán kép)** là quy tắc bất di bất dịch:

- Mọi giao dịch (Transaction) phải bao gồm ít nhất **2 bút toán (Entries)**.
    
- Một bên là **Nợ (Debit)**, một bên là **Có (Credit)**.
    
- Tổng giá trị Nợ phải luôn bằng Tổng giá trị Có.
    
    $$Total Credits + Total Debits = 0$$
    

---

## 2. Quy ước dấu (Signed Amount)

Để dễ lập trình (thay vì nhớ Nợ/Có lằng nhằng), Developer thường quy ước:

- **Credit (Có):** Tiền đi ra khỏi tài khoản -> Dấu **Âm (-)**.
    
- **Debit (Nợ):** Tiền đi vào tài khoản -> Dấu **Dương (+)**.
    

**Ví dụ:** Alice chuyển $100 cho Bob.

1. Tài khoản Alice: **-100** (Credit).
    
2. Tài khoản Bob: **+100** (Debit).
    
    -> Tổng: $(-100) + (+100) = 0$. Hệ thống cân bằng.
    

---

## 3. Database Schema Design

Ta cần tách biệt **Transaction** (Sự kiện) và **Ledger Entry** (Chi tiết dòng tiền).

SQL

```
-- 1. Bảng Tài khoản (Chart of Accounts)
CREATE TABLE accounts (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    type VARCHAR(20), -- ASSET, LIABILITY, REVENUE, EXPENSE
    balance DECIMAL(20, 4) DEFAULT 0 -- Cache số dư (Denormalization)
);

-- 2. Bảng Giao dịch (Header) - Lưu metadata
CREATE TABLE transactions (
    id UUID PRIMARY KEY,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Bảng Bút toán (Ledger Entries) - Lưu dòng tiền
CREATE TABLE entries (
    id UUID PRIMARY KEY,
    transaction_id UUID REFERENCES transactions(id),
    account_id UUID REFERENCES accounts(id),
    amount DECIMAL(20, 4) NOT NULL, -- Có thể âm hoặc dương
    direction VARCHAR(10) -- 'DEBIT' hoặc 'CREDIT' (Optional, để dễ đọc)
);

-- Index để query lịch sử giao dịch nhanh
CREATE INDEX idx_entries_account ON entries(account_id);
CREATE INDEX idx_entries_tx ON entries(transaction_id);
```

---

## 4. Code Implementation (Golang)

Logic chuyển tiền đảm bảo tính toàn vẹn dữ liệu (Data Integrity).

Go

```
func TransferMoney(ctx context.Context, db *sql.DB, fromAcc, toAcc uuid.UUID, amount decimal.Decimal) error {
    tx, _ := db.BeginTx(ctx, nil)
    defer tx.Rollback()

    // 1. Tạo Transaction Header
    txID := uuid.New()
    tx.Exec(`INSERT INTO transactions (id, description) VALUES ($1, 'Transfer P2P')`, txID)

    // 2. Tạo Entry trừ tiền người gửi (Credit - Amount Âm)
    // Lưu ý: amount.Neg() để đổi dấu
    _, err := tx.Exec(`
        INSERT INTO entries (transaction_id, account_id, amount) 
        VALUES ($1, $2, $3)`, 
        txID, fromAcc, amount.Neg())
    if err != nil { return err }

    // 3. Tạo Entry cộng tiền người nhận (Debit - Amount Dương)
    _, err = tx.Exec(`
        INSERT INTO entries (transaction_id, account_id, amount) 
        VALUES ($1, $2, $3)`, 
        txID, toAcc, amount)
    if err != nil { return err }

    // 4. Update Balance Cache (Optional nhưng cần cho performance)
    // Cập nhật tài khoản A
    tx.Exec(`UPDATE accounts SET balance = balance - $1 WHERE id = $2`, amount, fromAcc)
    // Cập nhật tài khoản B
    tx.Exec(`UPDATE accounts SET balance = balance + $1 WHERE id = $2`, amount, toAcc)

    // 5. QUAN TRỌNG: Kiểm tra lại tổng bằng 0 (Constraint Check)
    var sum decimal.Decimal
    tx.QueryRow(`SELECT SUM(amount) FROM entries WHERE transaction_id = $1`, txID).Scan(&sum)
    
    if !sum.IsZero() {
        return fmt.Errorf("transaction imbalance: sum is %v", sum)
    }

    return tx.Commit()
}
```

---

## 5. Những tài khoản đặc biệt (System Accounts)

**Câu hỏi:** Khi User nạp tiền mặt vào (Deposit), tiền trong ví User tăng lên (+100). Vậy cái gì giảm đi (-100)?

**Trả lời:** Tiền không tự sinh ra. Nó đi từ "Thế giới bên ngoài" vào.

Ta cần một tài khoản đặc biệt gọi là **System Settlement Account** (Tài khoản đối soát hệ thống) hoặc **World Account**.

- **Nạp tiền (Deposit):**
    
    - User Wallet: +100 (Debit - Asset).
        
    - System Bank: +100 (Debit - Asset thực tế trong ngân hàng).
        
    - Liability Account: -100 (Credit - Hệ thống nợ user).
        
- **Tặng thưởng (Promotion):**
    
    - User Wallet: +10.
        
    - Marketing Expense Account (Quỹ Marketing): -10.
        

-> **Luôn luôn có đối ứng.** Nếu bạn query `SELECT SUM(balance) FROM accounts` trên toàn bộ hệ thống, kết quả phải **luôn bằng 0**. (Asset + Expense = Liability + Equity + Income).

---

## 6. Audit & Reconcile (Đối soát)

Với Double Entry, việc tìm lỗi cực kỳ dễ.

Hàng đêm, chạy job quét DB:

SQL

```
-- Tìm tất cả các giao dịch bị lệch (Không cân bằng)
SELECT transaction_id, SUM(amount) 
FROM entries 
GROUP BY transaction_id 
HAVING SUM(amount) != 0;
```

Nếu query này trả về bất kỳ dòng nào -> **BÁO ĐỘNG ĐỎ (Red Alert)**. Hệ thống đang bị lỗi nghiêm trọng hoặc bị tấn công.

---

## 7. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Tại sao cần bảng `entries` riêng mà không lưu JSON trong bảng `transactions`?
> 
> **A:**
> 
> 1. **Tính toán:** Để dễ dàng `SUM(amount)` theo từng `account_id` (tính số dư, sao kê). SQL không aggregate tốt trong JSON array.
>     
> 2. **Locking:** Khi update, ta chỉ lock các row trong bảng `entries` hoặc lock `accounts` liên quan, tránh lock toàn bộ bảng transaction.
>     

> [!QUESTION] Q: Làm sao xử lý phí giao dịch (Transaction Fee)?
> 
> **A:** Giao dịch sẽ có 3 entries (Split Transaction):
> 
> 1. Người gửi (Alice): **-105** (Gửi 100 + 5 phí).
>     
> 2. Người nhận (Bob): **+100**.
>     
> 3. Tài khoản Doanh thu (Revenue Account): **+5**.
>     
>     -> Tổng: -105 + 100 + 5 = 0.
>     

> [!QUESTION] Q: Immutable Ledger là gì?
> 
> **A:** Trong Double Entry, **TUYỆT ĐỐI KHÔNG DÙNG UPDATE/DELETE** lên bảng `entries`.
> 
> Nếu chuyển nhầm tiền?
> 
> - _Sai:_ Delete dòng cũ.
>     
> - _Đúng:_ Tạo một giao dịch mới ngược chiều (Reversal Transaction) để bù trừ.
>     
>     -> Đảm bảo lịch sử vĩnh viễn không bị xóa (Audit Trail).
>