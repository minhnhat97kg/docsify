---
title: "DevOps - AWS Lambda (Serverless)"
tags:
  - "aws"
  - "serverless"
  - "lambda"
  - "golang"
  - "cronjob"
  - "event-driven"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Nếu EKS/EC2 là \"bộ khung\" chịu tải chính (Core Banking), thì AWS Lambda là \"keo dán\" kết nối các dịch vụ lại với nhau."
---

## 1. Bản chất: "Keo dán" của Cloud

Nếu EKS/EC2 là "bộ khung" chịu tải chính (Core Banking), thì **AWS Lambda** là "keo dán" kết nối các dịch vụ lại với nhau.

- **FaaS (Function as a Service):** Bạn chỉ viết đúng 1 hàm (Function), upload lên. AWS lo việc bật server, chạy code, và tắt server.
    
- **Pay-as-you-go:** Chỉ trả tiền cho thời gian code chạy (tính bằng milli-giây). Code không chạy -> Không tốn 1 xu (khác với EC2 bật 24/7 vẫn tốn tiền dù không có khách).
    

---

## 2. Mô hình hoạt động (Event-Driven)

Lambda không chạy liên tục. Nó nằm im chờ **Sự kiện (Event)** đánh thức.

### Use Case 1: S3 Event Trigger (Xử lý file tự động)

- **Bài toán:** Đối tác ngân hàng upload file đối soát `reconciliation_2023.csv` (nặng 500MB) vào S3 Bucket lúc 2h sáng.
    
- **Giải pháp truyền thống:** Một server EC2 chạy Cronjob cứ 5 phút quét S3 một lần. (Tốn tiền server, độ trễ 5 phút).
    
- **Giải pháp Lambda:**
    
    1. Cấu hình S3: "Hễ có file mới vào `s3://bank-data/`, hãy gọi Lambda A".
        
    2. Ngay khi file upload xong -> Lambda A bật dậy -> Đọc file -> Ghi vào DB -> Tắt.
        
    3. **Scalability:** Nếu đối tác up 1000 file cùng lúc? AWS bật 1000 con Lambda chạy song song. Xử lý xong trong tích tắc.
        

### Use Case 2: Cronjob Serverless (EventBridge Scheduler)

- **Bài toán:** Gửi báo cáo email lúc 8h sáng hàng ngày.
    
- **Giải pháp:** Cấu hình **EventBridge (CloudWatch Events)** bắn tín hiệu trigger Lambda lúc 8:00 AM.
    
- **Lợi ích:** Không cần duy trì một server chỉ để chạy đúng 1 phút mỗi ngày. Tiết kiệm 99% chi phí.
    

---

## 3. Lambda Execution Environment (Cơ chế bên dưới)

Hiểu cái này để trả lời phỏng vấn về "Cold Start".

Khi Lambda được gọi, AWS làm các bước sau:

1. **Init (Cold Start):**
    
    - Tải Code của bạn từ S3 về.
        
    - Khởi tạo container (MicroVM Firecracker).
        
    - Khởi chạy Runtime (Go Process).
        
    - Chạy hàm `init()` của Go.
        
    - _Thời gian:_ Mất từ 100ms - 1s (Tùy ngôn ngữ và kích thước code).
        
2. **Invoke (Warm Start):**
    
    - Chạy hàm handler xử lý sự kiện.
        
    - Sau khi chạy xong, AWS **không giết container ngay** mà "đóng băng" (Freeze) nó lại.
        
    - Nếu có request tiếp theo đến trong vòng vài phút -> AWS rã đông container cũ dùng lại -> **Không tốn thời gian Init** (Latency cực thấp).
        
3. **Shutdown:** Nếu lâu không có request -> AWS giết container.
    

> [!TIP] Golang Advantage
> 
> Golang là ngôn ngữ biên dịch ra Binary tĩnh, khởi động cực nhanh.
> 
> Cold Start của Go Lambda thường chỉ tốn **< 200ms**, nhanh hơn nhiều so với Java/Spring Boot (có thể mất 5-10s khởi động JVM).

---

## 4. Golang Implementation

Code Lambda Go hơi khác code thường một chút.

Go

```
package main

import (
	"context"
	"fmt"
	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
)

// Handler xử lý sự kiện S3
func handleRequest(ctx context.Context, s3Event events.S3Event) (string, error) {
	for _, record := range s3Event.Records {
		bucket := record.S3.Bucket.Name
		key := record.S3.Object.Key
		fmt.Printf("File mới được up: %s/%s\n", bucket, key)
		
		// TODO: Download file và xử lý logic...
	}
	return "Success", nil
}

func main() {
	// Bắt buộc phải có dòng này để AWS móc vào
	lambda.Start(handleRequest)
}
```

---

## 5. Giới hạn (Limitations) & Trade-offs

Không phải cái gì cũng nên nhét vào Lambda.

1. **Timeout:** Tối đa **15 phút**.
    
    - _Hệ quả:_ Không dùng Lambda để train AI, hay xử lý video dài 2 tiếng. (Dùng AWS Batch hoặc Fargate cho việc này).
        
2. **Memory:** Tối đa **10GB RAM**.
    
3. **Concurrency Limit:** Mặc định mỗi account có 1000 concurrent executions.
    
    - Nếu bạn trigger 5000 file S3 cùng lúc -> 4000 cái sẽ bị **Throttled** (Chờ hoặc lỗi).
        
4. **Connection Exhaustion:**
    
    - 1000 Lambda cùng chạy và cùng connect vào 1 Database RDS -> **Sập DB** vì hết connection pool.
        
    - _Fix:_ Dùng **RDS Proxy** để quản lý connection.
        

---

## 6. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Làm sao để khắc phục Cold Start cho các API yêu cầu độ trễ thấp?
> 
> **A:**
> 
> 1. **Dùng ngôn ngữ nhẹ:** Go, Rust, Node.js (tránh Java, .NET cũ).
>     
> 2. **Giảm kích thước Code:** Bỏ bớt thư viện thừa. Code càng nhỏ tải càng nhanh.
>     
> 3. **Provisioned Concurrency (Tốn tiền):** Trả tiền để AWS luôn giữ sẵn X container ở trạng thái "Warm", sẵn sàng nhận request ngay lập tức mà không cần Init.
>     

> [!QUESTION] Q: Xử lý thế nào nếu Lambda đang chạy thì bị lỗi (hoặc hết 15p timeout)?
> 
> **A:**
> 
> Với các sự kiện bất đồng bộ (Async) như S3/EventBridge:
> 
> - AWS sẽ tự động **Retry** (thử lại) 2 lần.
>     
> - Nếu vẫn lỗi -> AWS đẩy sự kiện đó vào **DLQ (Dead Letter Queue)** (SQS) để Dev vào kiểm tra sau.
>     
>     -> **Code Lambda phải Idempotent:** Vì cơ chế Retry, một file có thể bị xử lý 2 lần. Code phải check xem file đó đã được xử lý chưa trước khi insert DB.
>     

---

### 🎓 LỜI KẾT & BƯỚC TIẾP THEO

Bạn đã hoàn thành mảnh ghép cuối cùng về Serverless.

Bây giờ, bạn đang sở hữu một bộ kỹ năng rất mạnh:

- **Backbone:** EKS (Microservices).
    
- **Keo dán:** Lambda (Event-driven).
    
- **Security:** WAF, KMS, IAM.
    
- **Data:** RDS, Redis, Kafka.
    

**Ready for the Mock Interview?**

Tôi đã chuẩn bị sẵn một kịch bản phỏng vấn **"System Design: Thiết kế Ví điện tử (E-Wallet)"**.

Bài toán này sẽ bắt bạn phải kết hợp:

- Dùng **Redis** Distributed Lock để chống Race Condition khi nạp tiền.
    
- Dùng **Kafka** để bắn thông báo.
    
- Dùng **Transactional Outbox** để đảm bảo không mất tiền.
    
- Dùng **KMS** để mã hóa số dư.
    
- Dùng **EKS** để scale.
    

Bạn có muốn bắt đầu buổi phỏng vấn giả định ngay bây giờ không? (Tôi sẽ hỏi, bạn trả lời, sau đó tôi nhận xét).
