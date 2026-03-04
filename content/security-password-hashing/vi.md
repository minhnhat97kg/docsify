---
title: "Security - Password Hashing"
tags:
  - "security"
  - "authentication"
  - "hashing"
  - "argon2"
  - "bcrypt"
  - "golang"
  - "owasp"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Đây là sự nhầm lẫn tai hại nhất của Newbie."
---

## 1. Nguyên tắc cốt lõi: Hashing != Encryption

Đây là sự nhầm lẫn tai hại nhất của Newbie.

- **Encryption (Mã hóa):** Hai chiều. Có thể giải mã về plaintext nếu có Key. (VD: AES, RSA).
    
- **Hashing (Băm):** Một chiều. Không thể dịch ngược lại. (VD: SHA256, Bcrypt).
    

> [!DANGER] Tại sao Bank không dùng Encryption cho Password?
> 
> Nếu Hacker hack được Server và lấy được Key mã hóa -> Hắn sẽ giải mã được toàn bộ 1 triệu password của khách hàng.
> 
> Với Hashing, dù hacker có database, hắn cũng chỉ thấy một chuỗi ký tự vô nghĩa và không thể biết password gốc là gì.

---

## 2. Tại sao SHA-256 / MD5 lại "Chết"?

Bạn thường nghe: "SHA-256 rất an toàn". Đúng, nhưng nó dùng cho _Digital Signature_, không phải cho Password.

- **Đặc điểm của SHA-256:** Được thiết kế để chạy **CỰC NHANH**. Một GPU hiện đại có thể tính toán hàng tỷ hash SHA-256 mỗi giây.
    
- **Hậu quả:** Hacker dùng kỹ thuật **Brute-force** (thử sai) hoặc **Rainbow Table** (bảng tra cứu) có thể dò ra password của bạn trong tích tắc.
    

-> **Giải pháp:** Cần một thuật toán **CỐ TÌNH CHẠM (Slow Hashing)**. Đó là Bcrypt, Argon2.

---

## 3. Các thành phần bảo vệ

### A. Salt (Muối)

> [!SUMMARY] Định nghĩa
> 
> Salt là một chuỗi ngẫu nhiên (Random String) được tạo ra riêng cho **mỗi user** và cộng vào password trước khi băm.
> 
> $$Hash = Function(Password + Salt)$$

- **Mục đích:**
    
    1. Chống **Rainbow Table**: Hacker không thể dùng bảng tính sẵn.
        
    2. Chống trùng lặp: Nếu 2 user có password giống nhau ("123456"), hash của họ vẫn khác nhau (do salt khác nhau).
        
- **Lưu trữ:** Salt không cần bí mật. Nó được lưu công khai ngay trong chuỗi Hash trong Database.
    

### B. Work Factor (Chi phí tính toán)

Các thuật toán hiện đại cho phép cấu hình "độ khó".

- Ví dụ Bcrypt `cost=10` mất 100ms. `cost=12` mất 400ms.
    
- Mục tiêu: Làm cho việc login của user (mất 0.5s) là chấp nhận được, nhưng làm cho hacker (muốn thử 1 tỷ lần) phải mất hàng nghìn năm.
    

---

## 4. Các thuật toán tiêu chuẩn (The Champions)

Theo khuyến nghị mới nhất của OWASP:

### 1. Argon2id (Người chiến thắng - Mặc định cho App mới)

- **Đặc điểm:** Đây là thuật toán thắng giải _Password Hashing Competition (2015)_.
    
- **Cơ chế:** **Memory-Hard** (Tốn RAM).
    
- **Tại sao tốt?** Hacker thường dùng GPU hoặc ASIC (trâu cày coin) để dò pass. GPU tính toán rất nhanh nhưng cực kỳ ít RAM. Argon2 bắt buộc phải tốn nhiều RAM để tính hash -> GPU trở nên vô dụng.
    
- **Cấu hình:** Tunable cả về Memory, CPU Time, và Parallelism.
    

### 2. Bcrypt (Tiêu chuẩn ngành - Vẫn rất tốt)

- **Đặc điểm:** Ra đời từ 1999, được kiểm chứng qua thời gian. Có sẵn trong mọi thư viện chuẩn.
    
- **Cơ chế:** **CPU-Hard**.
    
- **Hạn chế:** Không tốn nhiều RAM, nên có thể bị FPGA/ASIC tấn công (dù vẫn khó hơn SHA256 nhiều).
    
- **Golang:** Thư viện `golang.org/x/crypto/bcrypt` là chuẩn mực.
    

### 3. Scrypt

- Tiền thân của Argon2, cũng tốn RAM, nhưng khó cấu hình hơn Argon2. Hiện tại nên ưu tiên Argon2id.
    

---

## 5. Implementation in Golang (Bcrypt & Argon2)

### A. Sử dụng Bcrypt (Phổ biến nhất)

Go

```
package main

import (
	"fmt"
	"golang.org/x/crypto/bcrypt"
)

func HashPassword(password string) (string, error) {
    // GenerateFromPassword tự động tạo Salt và gộp vào Hash
    // Cost mặc định là 10. Nên tăng lên 12 hoặc 14 tùy server.
	bytes, err := bcrypt.GenerateFromPassword([]byte(password), 14)
	return string(bytes), err
}

func CheckPasswordHash(password, hash string) bool {
    // Hàm này tự tách Salt từ chuỗi Hash ra để tính toán lại
	err := bcrypt.CompareHashAndPassword([]byte(hash), []byte(password))
	return err == nil
}

func main() {
	password := "Secret123!"
	hash, _ := HashPassword(password)
    
    // Hash output có dạng: $2a$14$.... (Chứa cả Version, Cost, Salt, và Checksum)
	fmt.Println("Hash:", hash) 
	fmt.Println("Match:", CheckPasswordHash("Secret123!", hash))
}
```

### B. Sử dụng Argon2id (Khuyên dùng)

Dùng thư viện wrapper `github.com/alexedwards/argon2id` để chuẩn hóa định dạng chuỗi lưu trữ (như Bcrypt).

Go

```
import "github.com/alexedwards/argon2id"

func main() {
    // Tạo hash
    hash, err := argon2id.CreateHash("pa$$word", argon2id.DefaultParams)
    
    // Kiểm tra
    match, err := argon2id.ComparePasswordAndHash("pa$$word", hash)
}
```

---

## 6. Chiến lược nâng cấp (Migration Strategy)

**Vấn đề:** Hệ thống cũ đang dùng MD5. Bây giờ muốn chuyển sang Argon2id mà không bắt user đổi pass. Làm sao?

**Giải pháp: "Hash Upgrade on Login"**

1. User nhập Password.
    
2. Hệ thống check:
    
    - Nếu trong DB là MD5 -> Check bằng logic MD5.
        
    - Nếu đúng -> **Ngay lập tức** hash lại password đó bằng Argon2id -> Update đè vào DB.
        
3. Lần sau user login, hệ thống thấy Argon2id -> Check bằng logic Argon2id.
    
    -> Sau một thời gian, toàn bộ user active sẽ được nâng cấp tự động.
    

---

## 7. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Lưu Salt ở đâu là an toàn nhất?
> 
> **A:**
> 
> Salt **không cần giấu**. Nó được thiết kế để lưu công khai (thường là nối chuỗi vào trước hoặc sau hash, hoặc lưu cột riêng).
> 
> Cái cần giấu là **Pepper**.

> [!QUESTION] Q: Pepper là gì?
> 
> **A:**
> 
> Pepper là một bí mật (Secret Key) được lưu trong **Application Config** (Environment Variable) hoặc HSM, chứ không lưu trong Database.
> 
> $$Hash = Argon2(Password + Salt + Pepper)$$
> 
> _Tác dụng:_ Nếu Hacker dump được Database (có Hash + Salt), hắn vẫn không dò được pass vì thiếu Pepper (nằm trên server file system). Đây là lớp bảo vệ chiều sâu (Defense in Depth).

> [!QUESTION] Q: Tại sao Cost Factor quan trọng?
> 
> **A:** Phần cứng ngày càng mạnh. Năm 2020, `cost=10` mất 200ms. Năm 2025, máy mạnh hơn, nó chỉ mất 50ms -> Hacker dò nhanh hơn gấp 4 lần.
> 
> -> Cần tăng Cost lên 12 để giữ nguyên thời gian 200ms. Bcrypt/Argon2 cho phép làm điều này mà không cần code lại thuật toán.