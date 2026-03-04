---
title: "AWS - Secrets Manager & Automated Rotation"
tags:
  - "security"
  - "aws"
  - "devops"
  - "database"
  - "rotation"
  - "golang"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Trong mô hình cũ, Password Database thường được lưu trong biến môi trường () hoặc ConfigMap (K8s)."
---

## 1. Vấn đề: Cơn ác mộng "Đổi Mật Khẩu"

Trong mô hình cũ, Password Database thường được lưu trong biến môi trường (`.env`) hoặc ConfigMap (K8s).

**Rủi ro:**

1. **Rò rỉ:** Nếu Hacker đọc được biến môi trường -> Mất DB.
    
2. **Vận hành cực khổ:** Chính sách công ty bắt buộc đổi pass 90 ngày/lần.
    
    - Bước 1: DBA đổi pass trong Database.
        
    - Bước 2: DevOps update file `.env`.
        
    - Bước 3: Restart lại toàn bộ 100 Microservices. -> **Downtime** hoặc lỗi kết nối.
        

**AWS Secrets Manager** sinh ra để giải quyết việc này: App không cần biết password là gì, chỉ cần hỏi Secrets Manager. Và Password tự động đổi mỗi X ngày mà **không cần restart App**.

---

## 2. Cơ chế hoạt động

Secrets Manager hoạt động như một cái "Két sắt thông minh".

1. **Lưu trữ:** Bạn cất DB Credential (User/Pass/Host) vào Secrets Manager.
    
2. **Truy xuất:** App (Backend) khi khởi động sẽ gọi API lấy Credential về để connect DB.
    
3. **Xoay vòng (Rotation):** Đây là tính năng "ăn tiền" nhất.
    

### Quy trình Xoay vòng (Rotation Flow)

AWS sử dụng một **Lambda Function** để thực hiện việc này một cách không gây gián đoạn (Zero Downtime).

Giả sử bạn đang dùng Password A. Đến ngày xoay vòng:

1. **Create:** Lambda tạo một user mới (hoặc password mới) trong DB -> Password B.
    
2. **Set:** Lambda cập nhật Password B vào Secrets Manager (đánh dấu là `AWSPENDING`).
    
3. **Test:** Lambda thử dùng Password B login vào DB xem có được không.
    
4. **Finish:**
    
    - Nếu Test OK -> Lambda đánh dấu Password B là `AWSCURRENT` (Hiện hành).
        
    - Password A bị đẩy xuống làm `AWSARIOUS` (Cũ).
        

> [!SUMMARY] Kết quả
> 
> App đang chạy vẫn dùng kết nối cũ (Password A).
> 
> App mới khởi động hoặc App refresh lại cache sẽ lấy được Password B.
> 
> -> Quá trình chuyển đổi mượt mà.

---

## 3. Code Implementation (Golang + Caching)

Gọi API của AWS mỗi lần connect DB là rất chậm và tốn tiền.

**Best Practice:** Cache secret trong RAM của ứng dụng và refresh định kỳ.

Go

```
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/secretsmanager"
)

type DBCredentials struct {
	Username string `json:"username"`
	Password string `json:"password"`
	Engine   string `json:"engine"`
	Host     string `json:"host"`
}

func GetSecret() (*DBCredentials, error) {
	secretName := "prod/myapp/db"
	region := "ap-southeast-1"

	cfg, _ := config.LoadDefaultConfig(context.TODO(), config.WithRegion(region))
	svc := secretsmanager.NewFromConfig(cfg)

	// Gọi AWS lấy Secret
	input := &secretsmanager.GetSecretValueInput{
		SecretId: &secretName,
	}

	result, err := svc.GetSecretValue(context.TODO(), input)
	if err != nil {
		return nil, err
	}

	var creds DBCredentials
	json.Unmarshal([]byte(*result.SecretString), &creds)
	return &creds, nil
}

// Trong thực tế, bạn sẽ dùng thư viện cache để lưu creds này
// và set TTL (ví dụ 1 giờ) để nó tự gọi lại hàm này lấy pass mới.
```

---

## 4. Secrets Manager vs. Parameter Store (SSM)

Đây là câu hỏi kinh điển khi chọn giải pháp lưu config.

|**Đặc điểm**|**SSM Parameter Store**|**AWS Secrets Manager**|
|---|---|---|
|**Chi phí**|**Miễn phí** (Standard) hoặc rất rẻ.|**$0.40** / secret / tháng + phí gọi API.|
|**Rotation**|Không hỗ trợ native (phải tự viết script phức tạp).|**Hỗ trợ Native** (Tự động trigger Lambda, có sẵn template cho RDS, Redshift...).|
|**Cross-Account**|Khó cấu hình.|Dễ dàng replicate secret sang region/account khác.|
|**Password Generation**|Không.|Có thể tự sinh password ngẫu nhiên mạnh.|
|**Use Case**|Lưu config thường (URL, Feature Flag), biến môi trường không nhạy cảm.|**Lưu DB Credentials, API Key, OAuth Token cần xoay vòng.**|

---

## 5. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Nếu DB Password bị đổi (Rotation) trong khi App đang chạy, kết nối cũ có bị đứt không?
> 
> **A:**
> 
> **Không.**
> 
> Các kết nối TCP đã thiết lập (Connection Pool) vẫn giữ nguyên và hoạt động bình thường với password cũ (trừ khi DB Server bị restart hoặc kill connection).
> 
> Vấn đề chỉ xảy ra khi App cố gắng tạo _kết nối mới_. Lúc này nếu App vẫn cache password cũ -> Lỗi Login.
> 
> -> **Giải pháp:** App phải có cơ chế **Refresh Cache** (tự động lấy lại secret mới) khi gặp lỗi "Authentication Failed".

> [!QUESTION] Q: Làm sao quản lý quyền truy cập Secret?
> 
> **A:**
> 
> Sử dụng **Resource-based Policy** ngay trên Secret đó (giống S3 Bucket Policy).
> 
> Ví dụ: Chỉ cho phép IAM Role của `PaymentService` đọc secret `prod/payment/db`. Chặn `OrderService` đọc. Điều này đảm bảo nguyên lý **Least Privilege**.

> [!QUESTION] Q: Tại sao chi phí Secrets Manager lại đắt hơn SSM? Tôi có nên dùng nó cho tất cả biến môi trường không?
> 
> **A:**
> 
> Không. Chỉ dùng Secrets Manager cho những thứ **CẦN XOAY VÒNG** (Password, Key).
> 
> Với các cấu hình tĩnh như `API_TIMEOUT`, `LOG_LEVEL`, `THEME_COLOR` -> Hãy dùng **SSM Parameter Store** để tiết kiệm tiền (Free).
> 
> Một hệ thống tốt thường kết hợp cả hai.

---

**Next Step:**

Bạn đã hoàn thành phần quản lý Credential.

Để kết thúc chuỗi bài về **Hệ thống phân tán & Cloud**, chúng ta còn một mảnh ghép cuối cùng rất quan trọng trong thiết kế hệ thống hiện đại: **CDN (Content Delivery Network) & Edge Computing**. Bạn có muốn tìm hiểu cách các ông lớn như Netflix/TikTok phân phối nội dung toàn cầu không?