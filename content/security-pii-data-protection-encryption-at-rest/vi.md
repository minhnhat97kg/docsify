---
title: "Security - PII Data Protection"
tags:
  - "security"
  - "encryption"
  - "pii"
  - "gdpr"
  - "aes"
  - "kms"
  - "banking"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Security - PII Data Protection (Encryption at Rest)"
---

Security - PII Data Protection (Encryption at Rest)

## 1. PII là gì và Tại sao phải mã hóa?

**PII (Personally Identifiable Information)** là dữ liệu định danh cá nhân:

- Số CCCD/CMND, Passport.
    
- Số điện thoại, Email.
    
- Địa chỉ nhà.
    
- Số tài khoản ngân hàng (PAN).
    

> [!DANGER] Toxic Data
> 
> Trong Banking, PII được coi là **Dữ liệu độc hại**.
> 
> Nếu Hacker dump được Database chứa password -> User đổi password là xong.
> 
> Nếu Hacker dump được Database chứa số CCCD + Địa chỉ -> User không thể đổi CCCD. Ngân hàng sẽ đối mặt án phạt khổng lồ (GDPR, Nghị định 13) và mất uy tín vĩnh viễn.

**Mục tiêu:** Dù Hacker (hoặc Sysadmin tò mò) có cầm được file Database (`dump.sql`), họ cũng chỉ thấy một mớ ký tự vô nghĩa.

---

## 2. Các tầng mã hóa (Encryption Layers)

Không phải cứ "mã hóa" là an toàn. Có 3 tầng bảo vệ:

### A. Disk Level (Thấp nhất)

- **Công nghệ:** AWS EBS Encryption, BitLocker, LUKS.
    
- **Bảo vệ:** Chống trộm ổ cứng vật lý tại Data Center.
    
- **Điểm yếu:** Khi Server bật lên và Mount ổ cứng, dữ liệu lại trở thành Plaintext. Hacker hack vào OS vẫn đọc được file.
    

### B. Database Level (TDE - Transparent Data Encryption)

- **Công nghệ:** Postgres TDE, Oracle TDE, MS SQL TDE.
    
- **Bảo vệ:** File vật lý của DB được mã hóa.
    
- **Điểm yếu:** DB Engine tự động giải mã khi Query. Admin DB (`root`) SELECT vẫn thấy plaintext.
    

### C. Application Level (Cao nhất - Chuẩn Banking)

- **Cơ chế:** Backend (Golang/Java) mã hóa dữ liệu **trước khi** gửi câu `INSERT` xuống DB.
    
- **Bảo vệ:** Database chỉ chứa rác (`0x8a91b...`). Admin DB, Cloud Provider đều không đọc được. Chỉ có Backend có Key mới giải mã được.
    

---

## 3. Thuật toán chuẩn: AES-256-GCM

Đừng sáng tạo thuật toán. Hãy dùng tiêu chuẩn công nghiệp.

- **AES (Advanced Encryption Standard):** Chuẩn đối xứng (Symmetric).
    
- **256-bit Key:** Độ dài khóa an toàn nhất hiện nay.
    
- **Mode GCM (Galois/Counter Mode):** Quan trọng!
    
    - Nó cung cấp **Authenticated Encryption**.
        
    - Đảm bảo cả tính Bí mật (Confidentiality) và tính Toàn vẹn (Integrity).
        
    - Nếu Hacker lén sửa 1 bit trong chuỗi mã hóa, khi giải mã sẽ báo lỗi ngay lập tức (không ra dữ liệu rác).
        

---

## 4. Key Management: Envelope Encryption (Mã hóa phong bì)

Đây là phần khó nhất và hay bị hỏi nhất trong System Design.

**Câu hỏi:** "Mã hóa dữ liệu bằng Key A. Vậy Key A giấu ở đâu?"

Nếu lưu Key A trong file `config.yaml` -> Hacker đọc file config -> Mất hết.

Giải pháp là **Envelope Encryption**:

1. **DEK (Data Encryption Key):**
    
    - Sinh ngẫu nhiên một Key cho **mỗi dòng** (hoặc mỗi bảng).
        
    - Dùng DEK để mã hóa dữ liệu PII.
        
2. **KEK (Key Encryption Key) / Master Key:**
    
    - Nằm trong **HSM (Hardware Security Module)** hoặc **Cloud KMS** (AWS KMS, Google KMS). Tuyệt đối không bao giờ rời khỏi phần cứng đó.
        
    - Dùng KEK để mã hóa cái DEK ở trên.
        
3. **Lưu trữ:**
    
    - Trong DB lưu: `Encrypted_Data` + `Encrypted_DEK`.
        
4. **Quy trình Đọc:**
    
    - App đọc `Encrypted_DEK` từ DB.
        
    - Gửi `Encrypted_DEK` lên KMS nhờ giải mã.
        
    - KMS trả về `Plain_DEK` (chỉ tồn tại trong RAM App chốc lát).
        
    - App dùng `Plain_DEK` giải mã `Encrypted_Data`.
        

---

## 5. Vấn đề truy vấn (Searching on Encrypted Data)

Nếu cột `email` đã bị mã hóa thành `aq#$15...`.

Làm sao chạy câu lệnh: `SELECT * FROM users WHERE email = 'hacker@gmail.com'`?

DB không thể so sánh plaintext với ciphertext.

### Giải pháp: Blind Indexing (Chỉ mục mù)

Tạo thêm một cột `email_hash`.

|**id**|**email_encrypted (AES)**|**email_hash (HMAC-SHA256)**|
|---|---|---|
|1|`0x9a8...` (Decrypt ra a@b.com)|`a1b2...` (Hash của a@b.com)|

- **Lưu ý:** Hash phải dùng **HMAC** với một **Blind Index Key** bí mật (khác với Encryption Key). Nếu chỉ dùng SHA256 thường, hacker có thể đoán được (Rainbow table).
    
- **Query:**
    
    1. App tính hash: `h = HMAC('hacker@gmail.com', key)`.
        
    2. SQL: `SELECT * FROM users WHERE email_hash = h`.
        
    3. Lấy `email_encrypted` ra giải mã để hiển thị.
        

---

## 6. Code Implementation (Golang AES-GCM)

Go

```
package main

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"encoding/base64"
	"fmt"
	"io"
)

// Encrypt encrypts plain text string into cipher text string
func Encrypt(plainText string, key []byte) (string, error) {
	block, err := aes.NewCipher(key)
	if err != nil {
		return "", err
	}

	// GCM Mode
	aesGCM, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}

	// Tạo Nonce (Number used once) ngẫu nhiên
	nonce := make([]byte, aesGCM.NonceSize())
	if _, err = io.ReadFull(rand.Reader, nonce); err != nil {
		return "", err
	}

	// Mã hóa: Seal(dst, nonce, plaintext, additionalData)
	// Nonce được đính kèm vào đầu ciphertext (công khai)
	ciphertext := aesGCM.Seal(nonce, nonce, []byte(plainText), nil)

	return base64.StdEncoding.EncodeToString(ciphertext), nil
}

// Decrypt decrypts cipher text string into plain text string
func Decrypt(encryptedString string, key []byte) (string, error) {
	enc, _ := base64.StdEncoding.DecodeString(encryptedString)
	block, err := aes.NewCipher(key)
	if err != nil {
		return "", err
	}

	aesGCM, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}

	nonceSize := aesGCM.NonceSize()
	if len(enc) < nonceSize {
		return "", fmt.Errorf("ciphertext too short")
	}

	// Tách Nonce và Ciphertext thực sự
	nonce, ciphertext := enc[:nonceSize], enc[nonceSize:]

	// Giải mã
	plaintext, err := aesGCM.Open(nil, nonce, ciphertext, nil)
	if err != nil {
		return "", err
	}

	return string(plaintext), nil
}
```

---

## 7. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Key Rotation (Xoay vòng khóa) hoạt động thế nào?
> 
> **A:**
> 
> Theo chuẩn PCI-DSS, Master Key phải đổi định kỳ (VD: 1 năm).
> 
> Với Envelope Encryption, ta **không cần** giải mã lại toàn bộ dữ liệu TB trong DB.
> 
> Ta chỉ cần:
> 
> 1. Giải mã các `Encrypted_DEK` bằng KEK cũ.
>     
> 2. Mã hóa lại các DEK đó bằng KEK mới.
>     
> 3. Update lại cột `Encrypted_DEK` trong DB.
>     
>     -> Nhanh hơn gấp tỷ lần so với việc decrypt/encrypt lại dữ liệu gốc.
>     

> [!QUESTION] Q: Tại sao không dùng AES-ECB?
> 
> **A:**
> 
> **ECB (Electronic Codebook)** là mode yếu nhất. Các khối dữ liệu giống nhau sẽ cho ra ciphertext giống nhau.
> 
> _Ví dụ:_ Nếu mã hóa ảnh logo bằng ECB, bạn vẫn nhìn thấy mờ mờ hình dáng của logo đó.
> 
> _Banking:_ Bắt buộc dùng **GCM** hoặc **CBC** (với IV ngẫu nhiên).

> [!QUESTION] Q: Masking vs. Encryption khác gì nhau?
> 
> **A:**
> 
> - **Encryption (DB Layer):** Lưu `0x9a8b...` để bảo vệ khỏi hacker dump DB.
>     
> - **Masking (Presentation Layer):** Hiển thị `******1234` lên màn hình để bảo vệ khỏi người đứng sau lưng (Shoulder Surfing) hoặc nhân viên CSKH không cần biết số đầy đủ.
>     
> - Cả hai thường được dùng kết hợp.
>