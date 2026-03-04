---
title: "Concurrency: Race Condition (Điều kiện đua)"
tags:
  - "concurrency"
  - "bug"
  - "race-condition"
  - "golang"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Đây là giải thích về Race Condition - \"Kẻ thù số 1\" của các hệ thống ngân hàng và ứng dụng đa luồng, được trình bày theo định dạng Obsidian."
---

Đây là giải thích về **Race Condition** - "Kẻ thù số 1" của các hệ thống ngân hàng và ứng dụng đa luồng, được trình bày theo định dạng Obsidian.

---

# Concurrency: Race Condition (Điều kiện đua)

## 1. Khái niệm (Mental Model)

> [!SUMMARY] Định nghĩa
> 
> **Race Condition** xảy ra khi hai hoặc nhiều luồng (threads/goroutines) cùng truy cập và thay đổi một dữ liệu chung (shared resource) cùng một lúc mà **không có quy tắc đồng bộ hóa**.
> 
> Kết quả cuối cùng của chương trình phụ thuộc vào "ai chạy nhanh hơn" (thứ tự thực thi ngẫu nhiên của OS Scheduler), dẫn đến dữ liệu bị sai lệch hoặc hỏng hóc.

### Mô hình "Check-then-Act" (Nguyên nhân phổ biến)

Hầu hết Race Condition sinh ra từ quy trình lỗi này:

1. **Check:** Đọc giá trị từ bộ nhớ (Ví dụ: Kiểm tra số dư > 0).
    
2. **Act:** Tính toán và Ghi giá trị mới (Ví dụ: Trừ tiền).
    
    -> _Lỗi xảy ra khi Thread B chen vào giữa bước 1 và bước 2 của Thread A._
    

---

## 2. Ví dụ Ngân hàng (The "Lost Update" Problem)

Đây là ví dụ kinh điển trong phỏng vấn Bank.

**Kịch bản:**

- Tài khoản có: **$1000**.
    
- **Giao dịch A:** Rút $100.
    
- **Giao dịch B:** Rút $100.
    
- **Kỳ vọng:** Còn $800.
    
- **Thực tế (Race Condition):** Còn $900 (Ngân hàng mất tiền).
    

**Diễn biến lỗi:**

|**Thời gian**|**Thread A (Rút $100)**|**Thread B (Rút $100)**|**Giá trị trong DB**|
|---|---|---|---|
|T1|Đọc số dư: thấy **1000**||1000|
|T2||Đọc số dư: cũng thấy **1000** (Lỗi ở đây!)|1000|
|T3|Tính: 1000 - 100 = 900||1000|
|T4||Tính: 1000 - 100 = 900|1000|
|T5|Ghi vào DB: **900**||**900**|
|T6||Ghi vào DB: **900** (Ghi đè lên T5)|**900** ❌|

---

## 3. Code Demo & Cách phát hiện

### A. Code bị lỗi (Unsafe)

```go
package main

import (
	"fmt"
	"sync"
	"time"
)

var balance int = 1000

func withdraw() {
	// Bước 1: Đọc (Check)
	temp := balance

	// Giả lập xử lý chậm để tăng khả năng xảy ra Race Condition
	time.Sleep(1 * time.Millisecond)

	// Bước 2: Ghi (Act)
	temp = temp - 100
	balance = temp
}

func main() {
	var wg sync.WaitGroup
	// Chạy 5 giao dịch rút tiền cùng lúc
	for i := 0; i < 5; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			withdraw()
		}()
	}
	wg.Wait()

	fmt.Println("Số dư cuối cùng:", balance)
	// KỲ VỌNG: 500 (1000 - 5*100)
	// THỰC TẾ: Có thể là 900, 800, hoặc 600 (Ngẫu nhiên)
}
```

### B. Cách phát hiện: Go Race Detector

Trong Go, bạn không cần đoán mò. Toolchain có sẵn công cụ cực mạnh để bắt lỗi này.

> [!TIP] Command Line
> 
> Chạy lệnh với cờ `-race`:
> 
> `go run -race main.go`

**Output khi có lỗi:**

```text
WARNING: DATA RACE
Read at 0x00c00001c0d0 by goroutine 7:
  main.withdraw()
      .../main.go:12 +0x34

Previous write at 0x00c00001c0d0 by goroutine 6:
  main.withdraw()
      .../main.go:19 +0x56
```

### C. Cách sửa (Fix)

Sử dụng **Mutex** để khóa đoạn code truy cập vào `balance` (Critical Section).

```go
var mu sync.Mutex // 1. Khai báo khóa

func withdrawSafe() {
	mu.Lock()         // 2. Chặn cửa: Chỉ 1 người được vào
	defer mu.Unlock() // 3. Mở cửa khi xong việc

	temp := balance
	time.Sleep(1 * time.Millisecond)
	balance = temp - 100
}
```

---

## 4. Phân biệt: Race Condition vs. Data Race

Đây là câu hỏi "ăn điểm" (Bonus Point) cho Senior.

- **Data Race:** Xảy ra khi 2 luồng cùng truy cập 1 vùng nhớ, trong đó có ít nhất 1 luồng Ghi, và không có lock. (Lỗi về bộ nhớ).
    
- **Race Condition:** Là lỗi về **logic thời gian**.
    
    - _Lưu ý:_ Bạn có thể bị Race Condition ngay cả khi không bị Data Race.
        

**Ví dụ Race Condition mà không phải Data Race:**

Bạn dùng `Atomic` hoặc `Channel` để chuyển tiền. Từng lệnh đơn lẻ thì an toàn (không Data Race), nhưng thứ tự thực hiện sai logic.

> _Ví dụ:_ Thread A chuyển tiền -> Thread B in sao kê.
> 
> Nếu B chạy trước A: Sao kê chưa có giao dịch.
> 
> Nếu A chạy trước B: Sao kê có giao dịch.
> 
> -> Kết quả không đồng nhất (Race Condition) dù code không crash.

---

## 5. Tổng kết cho phỏng vấn

|**Câu hỏi**|**Trả lời**|
|---|---|
|**Race Condition là gì?**|Lỗi khi nhiều luồng tranh nhau sửa dữ liệu chung, kết quả phụ thuộc may rủi vào thứ tự chạy.|
|**Tại sao nó nguy hiểm?**|Gây mất tiền, sai dữ liệu, khó debug vì nó không xảy ra liên tục (Heisenbug).|
|**Làm sao tránh?**|Dùng cơ chế đồng bộ: `Mutex`, `RWMutex`, `Channel`, hoặc `Atomic`.|
|**Cách tìm lỗi?**|Dùng `go run -race` hoặc review code kỹ các biến global/shared.|

---

_Ghi chú: Copy vào Obsidian để lưu trữ._