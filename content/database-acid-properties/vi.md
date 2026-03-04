---
title: "Database: ACID Properties"
tags:
  - "database"
  - "acid"
  - "transaction"
  - "backend"
  - "interview"
  - "postgresql"
date: "2026-03-04"
author: "nathan.huynh"
summary: "> > ACID là bộ 4 tính chất tiêu chuẩn mà một hệ quản trị cơ sở dữ liệu (DBMS) như PostgreSQL, MySQL phải đảm bảo để một Giao dịch (Transaction) được coi là hợp lệ và an toàn."
---

# Database: ACID Properties

## 1. Tổng quan

> [!SUMMARY] Định nghĩa
> 
> **ACID** là bộ 4 tính chất tiêu chuẩn mà một hệ quản trị cơ sở dữ liệu (DBMS) như PostgreSQL, MySQL phải đảm bảo để một **Giao dịch (Transaction)** được coi là hợp lệ và an toàn.

Một **Transaction** là một tập hợp các thao tác (Insert, Update, Delete) được coi là một khối công việc duy nhất.

---

## 2. Chi tiết 4 tính chất (Banking Context)

### A - Atomicity (Tính Nguyên Tử)

> **"Tất cả hoặc không gì cả" (All or Nothing).**

- **Khái niệm:** Một transaction bao gồm nhiều bước. Nếu **BẤT KỲ** bước nào thất bại, **TOÀN BỘ** transaction phải bị hủy bỏ (Rollback) về trạng thái ban đầu. Không bao giờ được phép có trạng thái "làm xong một nửa".
    
- **Ví dụ Bank:** Chuyển tiền từ A sang B.
    
    1. Trừ tiền A ($100).
        
    2. Cộng tiền B ($100).
        
    
    - _Lỗi:_ Nếu bước 1 thành công nhưng bước 2 lỗi (do sập mạng), hệ thống phải **trả lại** $100 cho A.
        
- **Cài đặt trong SQL:**
    

SQL

```sql
BEGIN; -- Bắt đầu transaction
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
-- Giả sử lỗi xảy ra ở đây (VD: constraint violation)
UPDATE accounts SET balance = balance + 100 WHERE id = 2;
COMMIT; -- Nếu mọi thứ OK thì lưu
-- ROLLBACK; -- Nếu lỗi thì hủy hết
```

### C - Consistency (Tính Nhất Quán)

> **"Luật là luật" (From Valid State to Valid State).**

- **Khái niệm:** Dữ liệu phải thỏa mãn tất cả các quy tắc ràng buộc (Constraints, Triggers, Data types) do Database quy định. Transaction không được phép tạo ra dữ liệu phạm luật.
    
- **Ví dụ Bank:**
    
    - _Luật:_ Số dư tài khoản không được âm (`CHECK balance >= 0`).
        
    - _Tình huống:_ A có $50, muốn chuyển $100.
        
    - _Xử lý:_ Database sẽ chặn ngay lập tức, báo lỗi vi phạm Consistency. Giao dịch bị hủy, dữ liệu vẫn nguyên vẹn (A vẫn có $50).
        
- **Lưu ý:** Consistency trong ACID khác với Consistency trong CAP theorem (Distributed Systems).
    

### I - Isolation (Tính Cô Lập)

> **"Việc ai người nấy làm" (Concurrency Control).**

- **Khái niệm:** Nhiều transaction chạy song song (concurrently) nhưng không được làm ảnh hưởng lẫn nhau. Kết quả của chúng phải giống như thể chúng được chạy tuần tự (sequentially).
    
- **Ví dụ Bank:**
    
    - Transaction 1: Tổng kết tài sản toàn ngân hàng (đang chạy mất 10s).
        
    - Transaction 2: Khách hàng A rút tiền (chạy mất 0.1s).
        
    - _Yêu cầu:_ Transaction 1 không được đếm thiếu số tiền A vừa rút (hoặc đếm thừa), tùy thuộc vào **Isolation Level**.
        
- **Cơ chế:** Thường dùng **Locking** hoặc **MVCC** (Multi-Version Concurrency Control).
    

### D - Durability (Tính Bền Vững)

> **"Bút sa gà chết" (Permanent Storage).**

- **Khái niệm:** Một khi transaction đã thông báo `COMMIT` thành công, dữ liệu đó phải được lưu vĩnh viễn, kể cả khi 1 giây sau đó Server bị rút điện, cháy ổ cứng, hay crash OS.
    
- **Cơ chế:** Database sử dụng kỹ thuật **Write-Ahead Logging (WAL)**.
    
    1. Ghi hành động vào file Log (trên đĩa cứng) trước.
        
    2. Sau đó mới ghi vào file dữ liệu chính.
        
    
    - Nếu sập nguồn, khi khởi động lại, DB sẽ đọc file Log để khôi phục (Redo) lại dữ liệu.
        

---

## 3. Code Demo: ACID trong Golang

Khi làm việc với Go, bạn quản lý ACID thông qua `sql.Tx`.

Go

```go
package main

import (
	"context"
	"database/sql"
	"fmt"
	"log"
)

// Hàm chuyển tiền đảm bảo ACID
func TransferMoney(ctx context.Context, db *sql.DB, fromID, toID int, amount float64) error {
	// 1. Bắt đầu Transaction (Atomicity start)
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}

	// Hàm defer này đảm bảo nếu có panic hoặc return lỗi, transaction sẽ Rollback
	defer func() {
		if p := recover(); p != nil {
			tx.Rollback()
			panic(p) // Rethrow panic sau khi rollback
		} else if err != nil {
			tx.Rollback() // Rollback nếu có lỗi
		} else {
			err = tx.Commit() // Commit nếu mọi thứ OK (Durability start)
		}
	}()

	// 2. Trừ tiền người gửi
	_, err = tx.ExecContext(ctx, "UPDATE accounts SET balance = balance - $1 WHERE id = $2", amount, fromID)
	if err != nil {
		return err // Kích hoạt Rollback
	}

	// 3. Cộng tiền người nhận
	_, err = tx.ExecContext(ctx, "UPDATE accounts SET balance = balance + $1 WHERE id = $2", amount, toID)
	if err != nil {
		return err // Kích hoạt Rollback
	}

	// 4. Kiểm tra Consistency (Ví dụ logic ứng dụng)
	// Giả sử DB chưa có check constraint, ta check bằng code
	var currentBalance float64
	err = tx.QueryRowContext(ctx, "SELECT balance FROM accounts WHERE id = $1", fromID).Scan(&currentBalance)
	if err != nil {
		return err
	}
	if currentBalance < 0 {
		err = fmt.Errorf("số dư không đủ")
		return err // Kích hoạt Rollback
	}

	return nil // Commit sẽ được gọi ở defer
}
```

---

## 4. Câu hỏi phỏng vấn Bank (Deep Dive)

> [!QUESTION] Q: Giữa Atomicity và Durability, cái nào quan trọng hơn?
> 
> **A:** Cả hai đều sống còn.
> 
> - Mất **Atomicity**: Tiền bốc hơi hoặc tự sinh ra -> Dữ liệu sai lệch logic.
>     
> - Mất **Durability**: Mất dữ liệu giao dịch đã báo thành công -> Mất niềm tin (và tiền) khi sập hệ thống.
>     

> [!QUESTION] Q: Postgres đảm bảo Atomicity như thế nào khi máy bị sập giữa chừng transaction?
> 
> **A:** Postgres dùng **WAL (Write-Ahead Log)**. Mọi thao tác đều được ghi vào log trước. Nếu sập giữa chừng (chưa Commit), khi khởi động lại, Postgres thấy transaction đó chưa hoàn tất trong Log -> Nó sẽ tự động Rollback (Undo) các thay đổi đó.

> [!QUESTION] Q: Tại sao NoSQL (như MongoDB, Cassandra) thường đánh đổi ACID?
> 
> **A:** Theo **CAP Theorem**, để đạt được khả năng phân tán (Partition Tolerance) và sẵn sàng cao (Availability), NoSQL thường hy sinh tính Consistency tức thì (Strong Consistency) của ACID để đổi lấy **BASE** (Basically Available, Soft state, Eventual consistency).
> 
> _Tuy nhiên, Bank Core (Core Banking) thì **bắt buộc dùng RDBMS (SQL)** vì cần ACID tuyệt đối._

---

_Ghi chú: Copy nội dung trên vào Obsidian._