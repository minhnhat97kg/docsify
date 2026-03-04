---
title: "AWS - KMS & Envelope Encryption"
tags:
  - "security"
  - "aws"
  - "kms"
  - "encryption"
  - "cryptography"
  - "golang"
  - "interview"
  - "cloud"
date: "2026-03-04"
author: "nathan.huynh"
summary: "AWS Key Management Service (KMS) là dịch vụ quản lý khóa bảo mật trên Cloud (HSM - Hardware Security Module)."
---

## 1. Vấn đề: Tại sao không gửi thẳng dữ liệu lên KMS?

AWS Key Management Service (KMS) là dịch vụ quản lý khóa bảo mật trên Cloud (HSM - Hardware Security Module).

Tuy nhiên, API của KMS (`kms:Encrypt`) có giới hạn: **Chỉ nhận tối đa 4KB dữ liệu**.

> [!DANGER] Câu hỏi đặt ra
> 
> Nếu bạn muốn mã hóa một file Database Backup nặng 100GB hay một video 4K, bạn không thể gửi cả file đó lên KMS được.
> 
> Ngoài ra, việc gửi dữ liệu lớn qua mạng (Network Round-trip) lên KMS sẽ làm chậm hệ thống khủng khiếp.

**Giải pháp:** **Envelope Encryption (Mã hóa phong bì)**.

---

## 2. Cơ chế Envelope Encryption

Đây là kỹ thuật dùng **2 loại khóa** khác nhau.

1. **CMK (Customer Master Key):**
    
    - Khóa chính, nằm vĩnh viễn trong phần cứng bảo mật (HSM) của AWS.
        
    - **KHÔNG BAO GIỜ** rời khỏi KMS (Ngay cả bạn hay nhân viên Amazon cũng không thấy được khóa này).
        
    - Dùng để mã hóa cái "Data Key".
        
2. **DEK (Data Key):**
    - Sinh ra ngẫu nhiên bởi KMS.
    - Dùng để mã hóa dữ liệu thật (File 100GB).
    - Khóa này được phép rời khỏi KMS (về App của bạn) dưới dạng đã mã hóa.
        

### Quy trình Mã hóa (Encryption Flow)

1. **Yêu cầu:** App gọi API `kms:GenerateDataKey` lên AWS.
    
2. **Phản hồi:** KMS trả về 2 phiên bản của cùng 1 khóa DEK:
    
    - `Plaintext Key` (Dạng rõ): Ví dụ `0x123abc...` (Chỉ tồn tại trong RAM).
        
    - `Encrypted Key` (Dạng mã hóa): Đã được CMK khóa lại.
        
3. **Mã hóa Local:** App dùng `Plaintext Key` để mã hóa dữ liệu 100GB bằng thuật toán AES-256 ngay trên server (Tốc độ cực nhanh vì không truyền data đi đâu cả).
    
4. **Lưu trữ:**
    
    - App xóa `Plaintext Key` khỏi RAM ngay lập tức.
        
    - App lưu `Encrypted Data` + `Encrypted Key` vào Database/Ổ cứng (đặt cạnh nhau).
        

### Quy trình Giải mã (Decryption Flow)

1. **Đọc:** App đọc `Encrypted Data` và `Encrypted Key` từ DB.
    
2. **Xin giải mã Key:** App gửi `Encrypted Key` lên KMS (API `kms:Decrypt`).
    
3. **Nhận Key:** KMS dùng CMK để mở khóa và trả về `Plaintext Key`.
    
4. **Giải mã Data:** App dùng `Plaintext Key` để giải mã dữ liệu gốc.
    

---

## 3. Lợi ích cốt lõi

1. **Hiệu năng (Performance):** Chỉ gửi cái khóa bé tẹo (vài byte) qua mạng. Việc mã hóa 100GB diễn ra cục bộ (Local CPU).
    
2. **Bảo mật (Security):** Master Key (CMK) không bao giờ bị lộ. Nếu Hacker trộm được DB, hắn có `Encrypted Data` và `Encrypted Key`, nhưng không có CMK để mở cái `Encrypted Key` đó.
    
3. **Tuân thủ (Compliance):** Khi cần xoá dữ liệu vĩnh viễn (Crypto-shredding), bạn chỉ cần **Disable/Delete cái CMK** trên AWS. Toàn bộ dữ liệu đã mã hóa bằng CMK đó sẽ trở thành rác không thể khôi phục, dù bản backup vẫn nằm đâu đó trên thế giới.
    

---

## 4. Code Implementation (Golang AWS SDK)

Minh họa cách gọi `GenerateDataKey` để thực hiện Envelope Encryption.

Go

```
package main

import (
	"context"
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"io"

	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/kms"
	"github.com/aws/aws-sdk-go-v2/service/kms/types"
)

func EncryptWithKMS(ctx context.Context, data []byte, keyID string) ([]byte, []byte, error) {
	// 1. Load AWS Config
	cfg, _ := config.LoadDefaultConfig(ctx)
	client := kms.NewFromConfig(cfg)

	// 2. Gọi KMS xin Data Key (DEK)
	// Trả về cả Plaintext (để dùng ngay) và CiphertextBlob (để lưu trữ)
	output, err := client.GenerateDataKey(ctx, &kms.GenerateDataKeyInput{
		KeyId:   &keyID,
		KeySpec: types.DataKeySpecAes256,
	})
	if err != nil { return nil, nil, err }

	// 3. Dùng Plaintext Key để mã hóa dữ liệu (AES-GCM Local)
	block, _ := aes.NewCipher(output.Plaintext)
	gcm, _ := cipher.NewGCM(block)
	nonce := make([]byte, gcm.NonceSize())
	io.ReadFull(rand.Reader, nonce)
	
	encryptedData := gcm.Seal(nonce, nonce, data, nil)

	// 4. Quan trọng: Xóa Plaintext Key khỏi bộ nhớ (Go GC sẽ lo, nhưng cẩn thận vẫn hơn)
	output.Plaintext = nil 

	// 5. Trả về Data đã mã hóa + Key đã mã hóa
	return encryptedData, output.CiphertextBlob, nil
}
```

---

## 5. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Key Rotation (Xoay vòng khóa) trong KMS hoạt động thế nào? Có phải mã hóa lại toàn bộ DB không?
> 
> **A:**
> 
> **Không.** Đây là tính năng "thần thánh" của KMS.
> 
> - Khi bạn bật _Automatic Key Rotation_, KMS sẽ tạo ra một phiên bản CMK mới (Backing Key) mỗi năm.
>     
> - KMS giữ lại các phiên bản cũ.
>     
> - Khi giải mã (`kms:Decrypt`), KMS tự biết cái `Encrypted Key` đó được khóa bằng phiên bản cũ nào và dùng đúng phiên bản đó để mở.
>     
> - -> **Không cần re-encrypt dữ liệu cũ.** Chỉ dữ liệu mới ghi vào mới dùng CMK mới.
>     

> [!QUESTION] Q: Multi-Region Key là gì? Tại sao cần cho Disaster Recovery (DR)?
> 
> **A:**
> 
> Mặc định, CMK là **Regional** (Tạo ở Singapore thì chỉ nằm ở Singapore).
> 
> Nếu bạn backup DB đã mã hóa từ Singapore sang Tokyo (DR Site). Khi Singapore bị sập, App ở Tokyo bật lên sẽ **không thể giải mã** được DB đó (vì CMK nằm ở Singapore).
> 
> **Giải pháp:** Sử dụng **Multi-Region Replica Key**. AWS sẽ đồng bộ CMK sang Tokyo. App ở Tokyo có thể dùng key đó để giải mã bình thường.

> [!QUESTION] Q: Phân biệt `kms:Encrypt` và `kms:GenerateDataKey`?
> 
> **A:**
> 
> - `kms:Encrypt`: Gửi dữ liệu lên KMS để mã hóa. Chỉ dùng cho dữ liệu nhỏ (<4KB) như Password, API Key, SSH Key.
>     
> - `kms:GenerateDataKey`: Xin khóa về để tự mã hóa. Dùng cho Envelope Encryption (Database, File, Big Data).
>     

---

**Next Step:**

Bạn đã hoàn thiện phần Security trên Cloud. Bạn có muốn chuyển sang chủ đề **Observability chuyên sâu** (Cách dựng Prometheus/Grafana để giám sát các metrics Go Runtime như Goroutines, GC Pause) không?