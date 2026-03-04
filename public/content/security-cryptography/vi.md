---
title: "Security - Cryptography"
tags:
  - "security"
  - "cryptography"
  - "hashing"
  - "encryption"
  - "aes"
  - "argon2"
  - "key-management"
  - "vault"
date: "2026-03-04"
author: "nathan.huynh"
summary: "---"
---

---

---

## 1. Bản chất: Smoothie vs. Lockbox

Về mặt chuyên môn:

- **Hashing:** Là hàm một chiều (One-way function). Nó biến một dữ liệu đầu vào bất kỳ thành một chuỗi ký tự có độ dài cố định. Không có cách nào (về mặt toán học thực tế) để dịch ngược từ Hash về dữ liệu gốc.
    
- **Encryption:** Là quá trình biến đổi dữ liệu (Plaintext) thành dạng không đọc được (Ciphertext) bằng một thuật toán và một chìa khóa (Key). Quá trình này có thể đảo ngược nếu có chìa khóa đúng.
    

> [!SUMMARY] Mental Model
> 
> **Hashing - "Ly sinh tố trái cây":** Bạn cho cam, táo, chuối vào máy xay. Bạn nhận được một ly sinh tố. Nhìn ly sinh tố, bạn biết nó có cam và táo, nhưng bạn **không bao giờ** biến ly sinh tố đó trở lại thành những quả cam, quả táo nguyên vẹn được. Đây là cách ta lưu mật khẩu: Ta không cần biết mật khẩu là gì, ta chỉ cần biết "ly sinh tố" có khớp không.
> 
> **Encryption - "Chiếc két sắt":** Bạn bỏ tài liệu vào két và khóa lại. Chỉ có người cầm chìa khóa mới mở được để đọc tài liệu gốc. Đây là cách ta bảo vệ dữ liệu nhạy cảm cần dùng lại (Số thẻ tín dụng, địa chỉ nhà).
> 
> **Khác biệt lớn nhất:** Hashing là **mãi mãi** (không quay đầu), Encryption là **tạm thời** (có thể mở khóa).

---

## 2. Giải phẫu (Anatomy): Chọn thuật toán đúng

### A. Hashing mật khẩu (Password Hashing)

Đừng bao giờ dùng SHA-256 hay MD5 để hash mật khẩu. Chúng quá nhanh, khiến hacker có thể brute-force hàng tỷ lần mỗi giây. Hãy dùng các thuật toán "chậm có chủ đích" như **Argon2** hoặc **bcrypt**.

Go

```
// Ngôn ngữ: Go
// Sử dụng Argon2 - "Nhà vô địch" hiện tại về Password Hashing
import "golang.org/x/crypto/argon2"

func HashPassword(password string) {
    salt := []byte("random_salt_here")
    // Argon2id giúp chống lại các cuộc tấn công side-channel và GPU cracking
    hash := argon2.IDKey([]byte(password), salt, 1, 64*1024, 4, 32)
    fmt.Printf("Hash: %x\n", hash)
}
```

### B. Encryption (AES-GCM)

AES là tiêu chuẩn vàng cho mã hóa đối xứng. **GCM (Galois/Counter Mode)** là "vị vua" vì nó cung cấp cả **Confidentiality** (mật mã) và **Authenticity** (đảm bảo dữ liệu không bị sửa đổi - Tampering).

Python

```
# Ngôn ngữ: Python (using Cryptography library)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

data = b"Sensitive Info: Account Balance $1,000,000"
key = AESGCM.generate_key(bit_length=256)
aesgcm = AESGCM(key)
nonce = os.urandom(12) # Nonce cực kỳ quan trọng, không bao giờ được lặp lại

ciphertext = aesgcm.encrypt(nonce, data, None)
# ciphertext bây giờ chứa cả dữ liệu mã hóa và tag xác thực
```

---

## 3. So sánh đánh đổi: Khi nào dùng cái gì?

|**Đặc điểm**|**Hashing (Argon2/bcrypt)**|**Symmetric Encryption (AES-GCM)**|**Asymmetric Encryption (RSA/ECC)**|
|---|---|---|---|
|**Tính thuận nghịch**|Một chiều (Không thể giải mã)|Hai chiều (Cần 1 key)|Hai chiều (Cần cặp Public/Private key)|
|**Tốc độ**|Chậm (Chống brute-force)|Rất nhanh|Chậm (Tốn CPU)|
|**Use Case chính**|Lưu mật khẩu, kiểm tra file Integrity|Mã hóa Database, Disk, File lớn|Trao đổi Key, Chữ ký số, HTTPS|
|**Quản lý Key**|Không cần key (Cần Salt)|Khó (Làm sao giấu 1 key duy nhất)|Dễ hơn (Public key có thể công khai)|

---

## 4. Vấn đề nhức nhối: Key Management (Quản lý chìa khóa)

Bạn có thuật toán mạnh nhất thế giới nhưng lại để chìa khóa dưới thảm (file `.env`) hoặc dán lên cửa (Git), thì coi như vô nghĩa.

### Thách thức: Secret Sprawl

Khi hệ thống lớn lên, các "secret" (DB password, API Key, Encryption Key) nằm rải rác khắp nơi. Nếu một server bị chiếm quyền, hacker có tất cả.

### Giải pháp: Centralized Secret Management

Sử dụng các công cụ như **HashiCorp Vault**, **AWS Secrets Manager**, hoặc **Google Secret Manager**.

> [!NOTE] Cơ chế hoạt động của Vault
> 
> 1. **Auth:** Ứng dụng xác thực với Vault (dùng IAM Role, Kubernetes Service Account).
>     
> 2. **Access:** Vault kiểm tra Policy xem ứng dụng được lấy secret nào.
>     
> 3. **Lease:** Vault cấp secret cho ứng dụng với một thời hạn nhất định (TTL).
>     
> 4. **Audit:** Mọi hành động lấy secret đều được ghi log chi tiết.
>     

---

## 5. Security/Performance Checklist

1. **Salt your Hashes:** Luôn dùng Salt ngẫu nhiên cho mỗi user để chống lại Rainbow Table.
    
2. **Never roll your own crypto:** Đừng tự viết thuật toán mã hóa. Hãy dùng các thư viện chuẩn (Libsodium, Tink, OpenSSL).
    
3. **Nonce/IV must be unique:** Trong AES-GCM, nếu bạn dùng lại cùng một Nonce với cùng một Key, bảo mật sẽ sụp đổ hoàn toàn.
    
4. **Key Rotation:** Định kỳ thay đổi chìa khóa mã hóa (ví dụ: 90 ngày một lần).
    
5. **No secrets in code:** Sử dụng các công cụ quét (GitGuardian, Trufflehog) để đảm bảo không ai vô tình push secret lên GitHub.
    

---

## 6. Góc phỏng vấn thực chiến

> [!QUESTION] Q1: Tại sao ta lại cần "Salt" khi hashing mật khẩu?
> 
> **A:** Nếu hai user dùng chung mật khẩu "123456", hash của họ sẽ giống hệt nhau. Hacker chỉ cần hash một lần là biết tất cả những người dùng mật khẩu đó. Salt (một chuỗi ngẫu nhiên đính kèm) đảm bảo rằng cùng một mật khẩu sẽ cho ra các hash khác nhau cho mỗi user.

> [!QUESTION] Q2: AES-256 an toàn hơn AES-128, vậy tại sao không luôn dùng 256?
> 
> **A:** AES-256 tốn CPU hơn một chút và cần quy trình quản lý key phức tạp hơn để thực sự phát huy sức mạnh. Trong phần lớn các bài toán thương mại, AES-128 đã là "không thể phá vỡ" với công nghệ hiện nay. Tuy nhiên, với kỷ nguyên Quantum Computing sắp tới, AES-256 được khuyến nghị hơn.

> [!QUESTION] Q3: Làm sao để mã hóa dữ liệu trong Database mà vẫn có thể tìm kiếm (Search) được?
> 
> **A:** Đây là bài toán cực khó. Một giải pháp phổ biến là dùng **Deterministic Encryption** (cùng một input ra cùng một ciphertext) cho cột cần search (nhưng kém an toàn hơn). Giải pháp hiện đại hơn là dùng **Searchable Symmetric Encryption (SSE)** hoặc lưu một cột "Blind Index" (hash của dữ liệu gốc) để tìm kiếm chính xác.

> [!QUESTION] Q4: Sự khác biệt giữa `Secret` và `Configuration` là gì?
> 
> **A:** Configuration (như `MAX_CONNECTIONS`) có thể để ở `.env` hay `ConfigMap` vì nó không nhạy cảm. Secret (như `DB_PASSWORD`) phải được mã hóa ở trạng thái nghỉ (at rest) và chỉ được giải mã trong bộ nhớ ứng dụng thông qua Secret Manager.

**Bạn có muốn mình hướng dẫn cách thiết lập một "Secret Engine" trên HashiCorp Vault để tự động cấp quyền truy cập Database tạm thời (Dynamic Credentials) không?**