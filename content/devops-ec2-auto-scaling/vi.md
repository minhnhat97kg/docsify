---
title: "DevOps - EC2 Auto Scaling"
tags:
  - "aws"
  - "ec2"
  - "autoscaling"
  - "high-availability"
  - "devops"
  - "cost-optimization"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "DevOps - EC2 Auto Scaling"
---

DevOps - EC2 Auto Scaling

## 1. Bản chất: "Co giãn" như dây chun

Hãy tưởng tượng trang web của bạn giống như một nhà hàng.

- **Giờ trưa (Cao điểm):** Khách đông nghịt. Nếu chỉ có 2 nhân viên -> Vỡ trận (Server sập).
    
- **3h sáng (Thấp điểm):** Không có khách. Nếu vẫn thuê 10 nhân viên -> Phí tiền (Lãng phí tài nguyên).
    

**EC2 Auto Scaling** là người quản lý thông minh:

- Tự động **tuyển thêm** nhân viên (Scale Out) khi khách đông.
    
- Tự động **sa thải** bớt nhân viên (Scale In) khi vắng khách.
    
- **Mục tiêu:** Đảm bảo hiệu năng nhưng **tối ưu chi phí** (Cost Optimization).
    

---

## 2. Giải phẫu hệ thống (3 Thành phần chính)

Để Auto Scaling hoạt động, bạn cần cấu hình 3 thứ:

### A. Launch Template (Bản thiết kế)

Trả lời câu hỏi: **"Khi cần thêm máy, sẽ bật loại máy nào?"**

- AMI (Hệ điều hành): Ubuntu 20.04 hay Amazon Linux 2?
    
- Instance Type: `t3.micro` hay `c5.large`?
    
- Security Group, Key Pair, User Data (Script chạy khi khởi động).
    

### B. Auto Scaling Group - ASG (Đội hình)

Trả lời câu hỏi: **"Số lượng máy tối thiểu/tối đa là bao nhiêu?"**

- **Min Capacity:** Số lượng tối thiểu (Ví dụ: 1 - Để web không bao giờ chết hẳn).
    
- **Max Capacity:** Số lượng tối đa (Ví dụ: 10 - Để tránh bị thủng ví nếu bị DDoS).
    
- **Desired Capacity:** Số lượng mong muốn hiện tại.
    

### C. Scaling Policies (Luật lệ)

Trả lời câu hỏi: **"Khi nào thì thêm/bớt máy?"**

---

## 3. Các chiến thuật Scale (Scaling Policies)

### 1. Target Tracking Scaling (Phổ biến nhất - Khuyên dùng)

- **Cơ chế:** Giống như cái điều hòa nhiệt độ (Thermostat).
    
- **Luật:** _"Hãy giữ cho CPU trung bình của cả nhóm ở mức 50%."_
    
- **Hành động:**
    
    - Nếu CPU lên 70% -> ASG tự tính toán bật thêm 2 máy để kéo trung bình xuống.
        
    - Nếu CPU xuống 30% -> ASG tắt bớt 1 máy.
        

### 2. Step Scaling (Điều chỉnh theo nấc)

- **Luật:**
    
    - Nếu CPU > 80% -> Thêm 2 máy.
        
    - Nếu CPU > 90% -> Thêm 5 máy (Phản ứng quyết liệt hơn).
        

### 3. Scheduled Scaling (Theo lịch trình)

- **Use Case:** Bạn biết chắc chắn 9h sáng thứ 2 hàng tuần sếp sẽ vào họp và traffic tăng.
    
- **Luật:** _"Đúng 8:50 sáng thứ 2, set Min Capacity = 10"_.
    

---

## 4. Lifecycle Hooks (Móc vòng đời)

Khi một EC2 mới được sinh ra hoặc bị giết đi, bạn muốn can thiệp vào quá trình đó.

- **Launching Hook:** Máy bật lên nhưng **chưa** nhận traffic ngay.
    
    - _Dùng để:_ Cài đặt phần mềm, download model AI, khởi tạo cache. Khi nào xong mới báo "OK" để nhận khách.
        
- **Terminating Hook:** Máy sắp bị giết nhưng **chưa** chết ngay.
    
    - _Dùng để:_ **Graceful Shutdown**. Gửi log cuối cùng về S3, chờ xử lý nốt các request đang dở dang, báo cho database đóng kết nối.
        

---

## 5. Vấn đề Flapping (Dao động) & Cooldown

**Vấn đề:**

CPU vừa chạm 51% -> Bật máy mới -> CPU tụt xuống 49% -> Tắt máy vừa bật -> CPU lại lên 51% -> Bật lại.

Hệ thống cứ bật/tắt liên tục (Flapping), vừa tốn tiền (AWS tính tiền tối thiểu 1 phút/giờ đầu) vừa không ổn định.

**Giải pháp: Cooldown Period (Thời gian làm nguội)**

- Mặc định là **300 giây (5 phút)**.
    
- Sau khi vừa Scale Out, ASG sẽ "nghỉ" 5 phút không làm gì cả, để hệ thống ổn định rồi mới đo đạc tiếp.
    

---

## 6. Infrastructure as Code (Terraform)

Terraform

```
# 1. Bản thiết kế
resource "aws_launch_template" "app" {
  name_prefix   = "my-app"
  image_id      = "ami-12345678"
  instance_type = "t3.micro"
}

# 2. Nhóm Auto Scaling
resource "aws_autoscaling_group" "bar" {
  desired_capacity   = 2
  max_size           = 5
  min_size           = 1
  vpc_zone_identifier = ["subnet-1", "subnet-2"] # Multi-AZ

  launch_template {
    id      = aws_launch_template.app.id
    version = "$Latest"
  }
}

# 3. Chính sách Scale theo CPU
resource "aws_autoscaling_policy" "cpu" {
  name                   = "keep-cpu-50"
  autoscaling_group_name = aws_autoscaling_group.bar.name
  policy_type            = "TargetTrackingScaling"

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }
    target_value = 50.0
  }
}
```

---

## 7. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: EC2 Auto Scaling có giúp ứng dụng chạy nhanh hơn không?
> 
> **A:**
> 
> **Gián tiếp thì có, trực tiếp thì không.**
> 
> Auto Scaling giúp duy trì sự ổn định khi tải cao, tránh việc server bị quá tải dẫn đến phản hồi chậm hoặc timeout.
> 
> Tuy nhiên, việc bật một máy mới (Scale Out) mất thời gian (3-5 phút để boot OS và App). Trong 3-5 phút đó, user vẫn có thể thấy chậm.
> 
> _Giải pháp:_ Dùng **Predictive Scaling** (Dự đoán trước dựa trên AI) hoặc **Warm Pools** (Giữ sẵn máy đã boot nhưng ở trạng thái Stopped để bật cho nhanh).

> [!QUESTION] Q: Auto Scaling hoạt động thế nào với Stateful App (Database)?
> 
> **A:**
> 
> **Rất tệ.** Đừng dùng Auto Scaling cho Database truyền thống (MySQL/PostgreSQL trên EC2).
> 
> Vì khi Scale In, ASG sẽ xóa ngẫu nhiên 1 máy -> Mất dữ liệu trong máy đó.
> 
> Auto Scaling sinh ra cho **Stateless App** (Web, API). Với Database, hãy dùng **Amazon RDS** (có storage auto scaling) hoặc Aurora Serverless.

> [!QUESTION] Q: Một Instance đang xử lý job quan trọng (mất 1 tiếng), làm sao để ASG không "giết" nhầm nó khi Scale In?
> 
> **A:**
> 
> Sử dụng tính năng **Scale-in protection**.
> 
> Khi App bắt đầu job, gọi API AWS set `SetInstanceProtection(True)`.
> 
> Khi làm xong job, set lại `False`.
> 
> ASG sẽ bỏ qua không terminate các instance đang được bảo vệ.

---

**Next Step:**

Bạn đã nắm vững "Bộ ba quyền lực" của AWS Compute: **EC2** (Máy ảo), **Lambda** (Serverless), và **Auto Scaling** (Co giãn).

Chúng ta đã đi qua một hành trình rất dài. Để tổng kết lại, bạn có muốn tôi tạo một **Mindmap (Sơ đồ tư duy)** tổng hợp mối quan hệ giữa:

- VPC & Networking
    
- EC2 & Auto Scaling
    
- Security (IAM, WAF, KMS)
    
- Database (RDS, DynamoDB)
    
    ...để bạn có cái nhìn toàn cảnh (Big Picture) về kiến trúc Cloud không?
