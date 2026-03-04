---
title: "Cloud Architecture - The Big Picture"
tags:
  - "architecture"
  - "aws"
  - "system-design"
  - "vpc"
  - "security"
  - "mindmap"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Để nhớ được mối quan hệ giữa hàng tá dịch vụ AWS, hãy hình dung chúng như một thành phố được quy hoạch bài bản."
---

## 1. Mental Model: "Thành phố kiên cố"

Để nhớ được mối quan hệ giữa hàng tá dịch vụ AWS, hãy hình dung chúng như một thành phố được quy hoạch bài bản.

> [!SUMMARY] Các lớp kiến trúc
> 
> 1. **Hạ tầng mạng (VPC):** Là đất đai, đường xá, phân lô (Subnet).
>     
> 2. **Cổng thành (Entry Point):** Nơi kiểm soát ra vào (WAF, ALB).
>     
> 3. **Khu dân cư (Compute):** Nơi các công nhân (EC2/Pod) làm việc.
>     
> 4. **Kho bạc (Data):** Nơi cất giữ tài sản (RDS, S3), được bảo vệ kỹ nhất.
>     
> 5. **Luật pháp (Security):** Giấy tờ tùy thân (IAM), Chìa khóa (KMS).
>     

---

## 2. Chi tiết mối quan hệ (Connections)

Điều quan trọng không phải là từng dịch vụ, mà là **cách chúng nói chuyện với nhau**.

### A. Từ Internet vào App (The Flow)

1. **User** gõ `bank.com`.
    
2. **Route53 (DNS):** Chỉ đường đến IP của Load Balancer.
    
3. **WAF (Tường lửa):** Đứng trước Load Balancer, soi xem User có mang "dao" (SQLi/XSS) không.
    
4. **ALB (Load Balancer):** Đứng ở **Public Subnet**. Nhận khách, chia việc cho các nhân viên bên trong.
    
5. **Auto Scaling Group (EC2/EKS):** Nằm ở **Private Subnet**. Nhận request từ ALB, xử lý logic.
    

### B. Từ App xuống Data (The Vault)

1. **EC2:** Cần lấy dữ liệu User.
    
2. **Security Group:** Cổng của RDS chỉ mở cho đúng Security Group của EC2 (SG Chaining).
    
3. **RDS (Database):** Nằm ở **Private Subnet** sâu nhất.
    
4. **Secrets Manager:** EC2 không lưu password DB. Nó hỏi Secrets Manager để lấy chìa khóa vào DB.
    

### C. Từ App đi ra ngoài (The Exit)

1. **EC2:** Cần gọi API thanh toán Stripe.
    
2. **NAT Gateway:** Đứng ở Public Subnet. Nó nhận gói tin từ EC2, thay mặt đi ra Internet, rồi trả kết quả về.
    
3. **Internet Gateway (IGW):** Cổng vật lý kết nối VPC với thế giới bên ngoài.
    

---

## 3. High Availability (HA) - Không bao giờ sập

Kiến trúc này được nhân bản (Mirror) trên ít nhất **2 Availability Zones (AZ)** (Ví dụ: Data Center A và Data Center B cách nhau 100km).

- **ALB:** Tự động phân phối traffic sang cả 2 AZ.
    
- **Auto Scaling:** Tự động bật EC2 ở cả 2 AZ. Nếu AZ A bị cháy/mất điện, ASG tự động bật thêm máy ở AZ B bù vào.
    
- **RDS Multi-AZ:**
    
    - **Primary DB:** Ở AZ A (Đang ghi dữ liệu).
        
    - **Standby DB:** Ở AZ B (Chờ sẵn). Dữ liệu được đồng bộ (Sync) tức thì.
        
    - _Sự cố:_ Nếu Primary chết, AWS tự động chuyển DNS sang Standby trong 60s.
        

---

## 4. Security Overlay (Lớp bảo mật bao trùm)

Bảo mật không nằm ở một chỗ, nó len lỏi vào mọi ngóc ngách (Defense in Depth).

|**Lớp bảo vệ**|**Công nghệ**|**Bảo vệ cái gì?**|
|---|---|---|
|**Lớp 1 (Viền ngoài)**|**WAF, CloudFront**|Chống DDoS, SQL Injection, XSS.|
|**Lớp 2 (Mạng)**|**VPC, NACL, Security Group**|Chỉ cho phép các port cần thiết (443, 80). Cấm SSH từ lạ.|
|**Lớp 3 (Quyền hạn)**|**IAM Role**|Server chỉ được làm việc nó cần làm (App Server chỉ được đọc S3 bucket `logs`, không được xóa).|
|**Lớp 4 (Dữ liệu)**|**KMS, Secrets Manager**|Dữ liệu nằm yên (At-rest) trong đĩa cứng phải được mã hóa. Password không được hardcode.|

---

## 5. Câu hỏi phỏng vấn thực chiến (Hệ thống tổng hợp)

> [!QUESTION] Q: Single Point of Failure (SPOF - Điểm chết duy nhất) trong mô hình này ở đâu?
> 
> **A:**
> 
> Trong mô hình chuẩn Multi-AZ, về lý thuyết **không có SPOF phần cứng**.
> 
> - NAT Gateway? -> Cần deploy 1 cái mỗi AZ.
>     
> - RDS? -> Có Standby.
>     
> - ALB? -> AWS quản lý, bản chất nó là cụm server phân tán.
>     
> - **Rủi ro:** SPOF thường nằm ở **Region Level**. Nếu cả Region Singapore sập (động đất, cáp quang biển đứt hết), hệ thống sẽ chết.
>     
> - _Fix:_ Multi-Region Active-Active (Rất đắt và phức tạp).
>     

> [!QUESTION] Q: Security Group Chaining là gì?
> 
> **A:**
> 
> Thay vì whitelist IP (rất dễ đổi), ta whitelist **Security Group ID**.
> 
> - Rule trên DB SG: `Allow Port 5432 from Source: sg-app-server`.
>     
> - Nghĩa là: "Bất kỳ máy nào đeo thẻ `sg-app-server` đều được vào DB".
>     
> - Lợi ích: Khi Auto Scaling bật thêm máy mới, máy đó tự động đeo thẻ `sg-app-server` -> Tự động vào được DB mà không cần sửa firewall.
>     

> [!QUESTION] Q: App Server (Private) muốn tải code từ S3 (Public Service), traffic có đi qua Internet không?
> 
> **A:**
> 
> Mặc định: Có (EC2 -> NAT Gateway -> Internet -> S3 Public Endpoint). Tốn tiền băng thông và chậm.
> 
> _Tối ưu:_ Dùng **VPC Endpoint (Gateway Endpoint)** cho S3.
> 
> Traffic sẽ đi đường tắt trong mạng nội bộ của AWS thẳng tới S3. Nhanh hơn, rẻ hơn, an toàn hơn.

---

**Next Step:**

Chúc mừng bạn! Bạn đã hoàn thành việc xây dựng "Bản đồ tư duy" cho kiến trúc Cloud.

Bây giờ bạn đã sẵn sàng cho thử thách cuối cùng chưa?

**Mock Interview: Thiết kế Hệ thống Ví Điện Tử (E-Wallet).**

Tôi sẽ đưa ra đề bài, bạn sẽ vẽ ra kiến trúc (bằng lời), chọn công nghệ (SQL vs NoSQL, K8s vs Lambda) và bảo vệ quan điểm của mình. Tôi sẽ chấm điểm như một Tech Lead thực thụ.
