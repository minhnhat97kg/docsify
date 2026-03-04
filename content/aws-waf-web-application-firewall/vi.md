---
title: "AWS - WAF (Web Application Firewall)"
tags:
  - "security"
  - "aws"
  - "waf"
  - "cloud"
  - "devops"
  - "owasp"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Nếu Security Group (Network Firewall) là cái hàng rào bảo vệ tòa nhà (chỉ kiểm tra xem bạn là ai, từ đâu đến - IP/Port), thì WAF chính là nhân viên an ninh đứng ngay cửa."
---

## 1. Bản chất: "Bảo vệ" lớp ứng dụng (Layer 7)

Nếu **Security Group** (Network Firewall) là cái hàng rào bảo vệ tòa nhà (chỉ kiểm tra xem bạn là ai, từ đâu đến - IP/Port), thì **WAF** chính là **nhân viên an ninh** đứng ngay cửa.

- Nhân viên an ninh sẽ lục soát ba lô của khách (Inspect HTTP Body/Header).
    
- Nếu thấy mang dao (`' OR 1=1`) hay súng (`<script>alert(1)</script>`), họ sẽ chặn ngay lập tức, dù khách đó có vé mời hợp lệ (IP sạch).
    

> [!SUMMARY] Tại sao cần WAF?
> 
> Code của bạn dù kỹ đến đâu cũng có thể có lỗ hổng (Bug).
> 
> WAF là lớp phòng thủ vòng ngoài (Virtual Patching). Nếu App bị lỗ hổng SQLi chưa kịp vá, WAF có thể chặn các request tấn công đó giúp bạn có thời gian fix code.

---

## 2. Các chức năng bảo vệ chính

WAF hoạt động dựa trên các **Rules (Luật)**.

### A. Chặn lỗ hổng phổ biến (OWASP Top 10)

- **SQL Injection (SQLi):** Chặn các chuỗi ký tự lạ như `' OR 1=1`, `UNION SELECT`.
    
- **Cross-Site Scripting (XSS):** Chặn các thẻ HTML nguy hiểm như `<script>`, `javascript:`, `onload=`.
    
- **AWS Managed Rules:** AWS cung cấp sẵn bộ luật này. Bạn chỉ cần bật lên là xong ("Core rule set", "SQLi rule set"). Không cần viết regex bằng tay.
    

### B. Rate Limiting (Chống DDoS tầng ứng dụng)

- **Luật:** "Nếu 1 IP gửi quá 100 request đến `/api/login` trong 5 phút -> Chặn IP đó trong 1 tiếng."
    
- Giúp chống Brute-force Password và HTTP Flood.
    

### C. Geo-blocking (Chặn theo địa lý)

- Ngân hàng của bạn chỉ phục vụ khách hàng Việt Nam.
    
- **Luật:** "Block toàn bộ request đến từ IP Trung Quốc, Nga, Bắc Triều Tiên..." để giảm rủi ro tấn công.
    

---

## 3. Kiến trúc triển khai (Deployment)

Trên AWS, bạn không cài WAF vào từng EC2. Bạn gắn WAF vào các "Cửa ngõ" (Entry points):

1. **AWS CloudFront (CDN):** Chặn ngay tại mép mạng (Edge). Hacker ở Mỹ tấn công -> Bị chặn ngay tại Server Mỹ, không tốn băng thông về Việt Nam. (Tốt nhất).
    
2. **Application Load Balancer (ALB):** Chặn trước khi traffic vào EC2/Container.
    
3. **API Gateway:** Chặn trước khi vào Lambda.
    

---

## 4. Infrastructure as Code (Terraform)

Đừng click tay trên Console. Hãy định nghĩa tường lửa bằng code để dễ quản lý version.

Terraform

```
resource "aws_wafv2_web_acl" "main" {
  name  = "banking-app-waf"
  scope = "REGIONAL" # Hoặc CLOUDFRONT

  default_action {
    allow {} # Mặc định cho qua, chỉ chặn cái xấu
  }

  # 1. Sử dụng bộ luật có sẵn của AWS để chặn SQLi
  rule {
    name     = "AWS-AWSManagedRulesSQLiRuleSet"
    priority = 1
    override_action { none {} }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }
    visibility_config { ... }
  }

  # 2. Luật tự chế: Rate Limit (Chặn DDoS)
  rule {
    name     = "RateLimit1000"
    priority = 2
    action { block {} }
    statement {
      rate_based_statement {
        limit              = 1000
        aggregate_key_type = "IP"
      }
    }
    visibility_config { ... }
  }
}
```

---

## 5. False Positives (Bắt nhầm người tốt)

Đây là nỗi đau lớn nhất khi dùng WAF.

- Ví dụ: User comment: _"Hôm nay tôi học lệnh SELECT trong SQL"_.
    
- WAF thấy chữ `SELECT` -> Tưởng là tấn công SQLi -> **Block User**.
    

**Chiến lược khắc phục:**

1. **Count Mode (Chế độ đếm):** Khi mới triển khai, đừng bật `Block`. Hãy bật `Count`.
    
    - WAF sẽ chỉ ghi log "Nếu là thật thì tao đã chặn thằng này".
        
2. **Analyze Logs:** Xem CloudWatch Logs. Nếu thấy WAF bắt nhầm request hợp lệ -> Tinh chỉnh lại luật (Whitelist đường dẫn cụ thể hoặc body cụ thể).
    
3. **Enforce:** Sau 1 tuần chạy Count Mode mà thấy ổn, mới chuyển sang `Block`.
    

---

## 6. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Security Group (SG), NACL và WAF khác nhau thế nào?
> 
> **A:**
> 
> - **NACL (Network ACL):** Tường lửa mức Subnet (Stateless). Chặn theo IP. Rất thô sơ.
>     
> - **Security Group:** Tường lửa mức Instance (Stateful). Chặn theo IP và Port (Layer 4). "Chỉ cho phép IP công ty vào Port 22".
>     
> - **WAF:** Tường lửa mức Ứng dụng (Layer 7). Hiểu được nội dung gói tin (HTTP Body, Cookie, User-Agent). "Chặn request có chứa SQL Injection".
>     
>     -> **Defense in Depth:** Phải dùng cả 3 lớp.
>     

> [!QUESTION] Q: WAF có chặn được Hacker nằm bên trong mạng nội bộ không?
> 
> **A:**
> 
> **Thường là không.**
> 
> WAF thường gắn ở viền ngoài (Load Balancer/Gateway). Nếu Hacker đã đột nhập vào được mạng nội bộ (hoặc nhân viên nội bộ tấn công), traffic đi ngang giữa các Microservices (East-West traffic) thường không qua WAF.
> 
> _Giải pháp:_ Cần bảo mật nội bộ (mTLS, Network Policy K8s).

> [!QUESTION] Q: Làm sao WAF đọc được HTTPS traffic (đã mã hóa)?
> 
> **A:**
> 
> WAF đứng sau bước **TLS Termination**.
> 
> Khi request đến Load Balancer/CloudFront, gói tin HTTPS được giải mã thành HTTP thường. WAF sẽ soi nội dung HTTP đó. Sau khi WAF cho qua, traffic mới được gửi xuống Backend (có thể mã hóa lại hoặc không tùy cấu hình).

---

**Next Step:**

Bạn đã kiện toàn "Thành trì" bảo mật (WAF, IAM, Secrets Manager, KMS).

Bạn có muốn thử sức với một bài toán **Troubleshooting thực tế**: "Hệ thống đang chạy thì bị chậm đột ngột, CPU tăng cao. Bạn sẽ dùng công cụ gì và quy trình nào để tìm ra nguyên nhân trong 10 phút?" (Kết hợp kiến thức Monitoring & Debugging).
