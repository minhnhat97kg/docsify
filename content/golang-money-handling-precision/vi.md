---
title: "Golang - Money Handling & Precision"
tags:
  - "golang"
  - "money"
  - "fintech"
  - "precision"
  - "database"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Trong hệ thống tài chính, việc sử dụng hay để tính toán tiền tệ là TỘI ÁC."
---

## 1. Nguyên tắc vàng: NEVER USE FLOAT

Trong hệ thống tài chính, việc sử dụng `float32` hay `float64` để tính toán tiền tệ là **TỘI ÁC**.

> [!DANGER] IEEE 754 Problem
> 
> Máy tính lưu trữ số thực dưới dạng nhị phân (Binary Floating Point). Một số con số đơn giản như `0.1` không thể biểu diễn chính xác tuyệt đối trong hệ nhị phân (giống như 1/3 trong hệ thập phân là 0.3333...).
> 
> **Hậu quả:** Sai số tích lũy.
> 
> - `0.1 + 0.2` **KHÔNG BẰNG** `0.3`.
>     
> - Nó bằng `0.30000000000000004`.
>     
> 
> Trong Bank, lệch 1 xu cũng là sai. Lệch 1 xu nhân với 10 triệu giao dịch là sai phạm lớn.

---

## 2. Giải pháp 1: Integer (Lưu đơn vị nhỏ nhất)

Cách đơn giản nhất, hiệu năng cao nhất.

Quy đổi tất cả về đơn vị nhỏ nhất (Sub-unit) để tính toán trên số nguyên (`int64`).

- **USD:** $10.50 -> Lưu là `1050` (cents).
    
- **VND:** 10,000 VND -> Lưu là `10000` (VND không có hào/xu).
    
- **Bitcoin:** 1 BTC -> Lưu là `100,000,000` (Satoshi).
    

**Ưu điểm:** Tính toán cực nhanh, tương thích mọi loại DB.

**Nhược điểm:** Phức tạp khi xử lý đa tiền tệ (Multi-currency). Bạn phải luôn nhớ mỗi loại tiền có bao nhiêu số lẻ (Exponent). Ví dụ: JPY (0), USD (2), KWD (3).

---

## 3. Giải pháp 2: Decimal Library (Khuyên dùng)

Sử dụng thư viện `github.com/shopspring/decimal` (Chuẩn mực trong cộng đồng Go).

Nó lưu trữ số dưới dạng **Fixed-point** (Số cố định) với độ chính xác tùy ý.

### Cài đặt

Bash

```
go get github.com/shopspring/decimal
```

### Code Demo: Float vs. Decimal

Go

```
package main

import (
	"fmt"
	"github.com/shopspring/decimal"
)

func main() {
	// --- CÁCH SAI (Float) ---
	var v1 float64 = 0.1
	var v2 float64 = 0.2
	fmt.Println("Float Check:", v1+v2 == 0.3) 
	// Output: false (Nó là 0.30000000000000004)

	// --- CÁCH ĐÚNG (Decimal) ---
	// Lưu ý: Luôn khởi tạo từ STRING, không dùng NewFromFloat
	d1, _ := decimal.NewFromString("0.1")
	d2, _ := decimal.NewFromString("0.2")
	d3 := d1.Add(d2)
	
	target, _ := decimal.NewFromString("0.3")
	
	fmt.Println("Value:", d3.String())        // Output: 0.3
	fmt.Println("Decimal Check:", d3.Equal(target)) // Output: true
}
```

---

## 4. Database Mapping (PostgreSQL & GORM)

Trong Database, **TUYỆT ĐỐI** không dùng `FLOAT`, `REAL`, hay `DOUBLE PRECISION`.

Phải dùng **`NUMERIC`** hoặc **`DECIMAL`**.

### SQL Definition

SQL

```
-- Cột lưu số dư: Tổng 20 chữ số, trong đó 4 số sau dấu phẩy
-- Tại sao là 4? Để tính toán tỷ giá/lãi suất chính xác hơn trước khi làm tròn.
CREATE TABLE accounts (
    id bigserial PRIMARY KEY,
    balance NUMERIC(20, 4) NOT NULL DEFAULT 0
);
```

### Golang GORM Struct

Thư viện `shopspring/decimal` tương thích hoàn hảo với `database/sql` driver.

Go

```
type Account struct {
    ID      uint            `gorm:"primaryKey"`
    // Khai báo type rõ ràng cho GORM
    Balance decimal.Decimal `gorm:"type:numeric(20,4);default:0"` 
}
```

---

## 5. Các phép toán & Làm tròn (Rounding)

Phần này phân biệt Junior và Senior.

### A. Thứ tự phép tính (Order of Operations)

Luôn tuân thủ: **Nhân trước, Chia sau**.

- Bài toán: Tính 1/3 của $100.
    
- Sai: `(100 / 3) * 1` = `33.3333` * `1` = `33.33`. (Mất độ chính xác sớm).
    
- Đúng: Giữ nguyên phân số hoặc dùng Decimal với precision cao rồi mới làm tròn ở bước cuối cùng (Display).
    

### B. Banker's Rounding (Làm tròn của Ngân hàng)

Chúng ta được dạy ở trường: >= 0.5 thì làm tròn lên (`RoundHalfUp`).

- 1.5 -> 2
    
- 2.5 -> 3
    
- 3.5 -> 4
    
    -> **Vấn đề:** Xu hướng làm tròn lên nhiều hơn -> Tổng tiền hệ thống bị dôi ra (Bias).
    

**Banker's Rounding (Round Half To Even):** Làm tròn về số chẵn gần nhất.

- 1.5 -> 2 (Chẵn)
    
- 2.5 -> 2 (Chẵn - Tròn xuống)
    
- 3.5 -> 4 (Chẵn - Tròn lên)
    
- 4.5 -> 4 (Chẵn - Tròn xuống)
    
    -> **Lợi ích:** Về mặt thống kê, sai số triệt tiêu lẫn nhau về 0. `shopspring/decimal` mặc định dùng `RoundHalfUp`, nhưng cần biết kỹ thuật này khi phỏng vấn.
    

---

## 6. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Tại sao không dùng `NewFromFloat(0.1)` mà phải dùng `NewFromString("0.1")`?
> 
> **A:**
> 
> Vì ngay bản thân hằng số `0.1` trong code Go đã là một số `float64` không chính xác rồi.
> 
> Nếu truyền nó vào `NewFromFloat`, bạn đang nạp "rác" vào Decimal.
> 
> Phải truyền String để thư viện tự parse từng ký tự số.

> [!QUESTION] Q: Khi chia tiền (ví dụ chia thưởng $100 cho 3 người), làm sao để tổng không bị lệch (33.33 + 33.33 + 33.33 = 99.99)?
> 
> **A:**
> 
> Không bao giờ dùng phép chia đều. Phải dùng thuật toán **Allocation**:
> 
> 1. Người 1: `floor(100/3)` = 33.33
>     
> 2. Người 2: `floor(100/3)` = 33.33
>     
> 3. Người 3: `100 - 33.33 - 33.33` = **33.34** (Hứng phần dư).
>     
>     Hoặc dùng hàm `decimal.Div` với phần dư trả về để phân phối lại.
>     

> [!QUESTION] Q: Nên lưu tiền trong DB là 2 số lẻ (10.50) hay 4 số lẻ (10.5000)?
> 
> **A:**
> 
> - **Số dư ví:** Thường lưu 2 hoặc theo đúng đơn vị tiền tệ.
>     
> - **Tỷ giá (Exchange Rate) / Lãi suất:** Bắt buộc lưu 4-6 số lẻ trở lên.
>     
> - **Giao dịch trung gian:** Nên lưu 4 số lẻ để tránh sai số khi cộng dồn, chỉ làm tròn hiển thị ra UI.
>