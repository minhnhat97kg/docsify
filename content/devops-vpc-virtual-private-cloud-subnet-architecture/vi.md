---
title: "DevOps - VPC & Subnet Architecture"
tags:
  - "aws"
  - "vpc"
  - "networking"
  - "security"
  - "architecture"
  - "terraform"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Nếu AWS là một thành phố khổng lồ, thì VPC chính là mảnh đất riêng của bạn được rào lại."
---

## 1. Bản chất: Ngôi nhà của bạn trên Mây

Nếu AWS là một thành phố khổng lồ, thì **VPC** chính là **mảnh đất riêng** của bạn được rào lại.

Trong mảnh đất đó, bạn chia thành các phòng (Subnets).

- **Public Subnet (Phòng khách):** Có cửa mở ra đường cái. Ai cũng có thể gõ cửa (nếu bạn cho phép).
    
- **Private Subnet (Phòng ngủ):** Kín cổng cao tường. Người lạ không thể nhìn thấy, không thể vào trực tiếp.
    

> [!DANGER] Nguyên tắc vàng (Security)
> 
> **Database (Tài sản quý nhất) phải LUÔN nằm trong Private Subnet.**
> 
> Hacker không thể tấn công thứ mà hắn không thể nhìn thấy (không có Public IP).

---

## 2. Kiến trúc 3 Lớp (3-Tier Architecture)

Đây là mô hình chuẩn mực nhất cho mọi hệ thống Banking/Enterprise.

### A. Public Subnet

- **Đặc điểm:** Có đường đi trực tiếp ra Internet (Route Table trỏ về **Internet Gateway - IGW**).
    
- **Chứa gì:**
    
    - **Load Balancer (ALB):** Để đón khách.
        
    - **Bastion Host (Jump Server):** Máy chủ trung gian để Admin SSH vào trong.
        
    - **NAT Gateway:** "Cửa sau" giúp các server bên trong đi chợ (tải update).
        

### B. Private Subnet (App Layer)

- **Đặc điểm:** KHÔNG có đường ra Internet trực tiếp. KHÔNG có Public IP.
    
- **Chứa gì:** **Backend Servers (EC2 / EKS Nodes)**.
    
- **Giao tiếp:** Chỉ nhận traffic từ Load Balancer (ở Public Subnet).
    

### C. Private Subnet (Data Layer)

- **Đặc điểm:** Kín nhất.
    
- **Chứa gì:** **Database (RDS), Cache (Redis)**.
    
- **Giao tiếp:** Chỉ nhận traffic từ App Servers.
    

---

## 3. Kết nối: Làm sao "người trong nhà" đi ra ngoài?

Database nằm ở Private Subnet (không có Internet). Vậy làm sao nó tải bản vá lỗi (Update OS) hoặc backup lên S3?

**Giải pháp: NAT Gateway**

- NAT Gateway nằm ở **Public Subnet**.
    
- Database gửi request đến NAT Gateway.
    
- NAT Gateway thay mặt Database đi ra Internet tải dữ liệu về, rồi chuyển lại cho Database.
    
- **Quan trọng:** Internet chỉ nhìn thấy IP của NAT Gateway. Internet không thể chủ động kết nối ngược lại vào Database. (Chỉ chiều ra, không có chiều vào).
    

---

## 4. Infrastructure as Code (Terraform)

Cấu hình Routing là phần hay sai nhất.

Terraform

```
# 1. Tạo VPC
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

# 2. Public Subnet & Internet Gateway
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id # Trỏ ra Internet
  }
}

# 3. Private Subnet & NAT Gateway
# (NAT Gateway cần 1 Elastic IP)
resource "aws_eip" "nat" {}

resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public.id # NAT phải nằm ở Public
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat.id # Trỏ ra NAT, KHÔNG trỏ IGW
  }
}
```

---

## 5. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Làm sao tôi SSH vào được EC2 nằm trong Private Subnet để debug?
> 
> **A:**
> 
> - **Cách cổ điển:** Dùng **Bastion Host**. SSH vào Bastion (Public), từ Bastion nhảy tiếp vào Private EC2. (Rủi ro: Phải bảo mật key của Bastion thật kỹ).
>     
> - **Cách hiện đại (AWS Recommended):** Dùng **SSM Session Manager**. Không cần mở port 22, không cần Bastion. Truy cập trực tiếp qua Console/CLI cực kỳ an toàn và có log đầy đủ.
>     

> [!QUESTION] Q: Security Group vs. NACL (Network ACL) khác gì nhau?
> 
> **A:**
> 
> - **Security Group (Tường lửa mềm):** Gắn vào **Instance**. Là **Stateful** (Cho phép chiều đi thì tự động cho phép chiều về). Đây là lớp bảo vệ chính.
>     
> - **NACL (Tường lửa cứng):** Gắn vào **Subnet**. Là **Stateless** (Phải mở cả chiều đi và chiều về thủ công). Thường dùng để chặn (Block) các IP xấu cụ thể ở cấp độ mạng.
>     

> [!QUESTION] Q: Nếu NAT Gateway bị sập, chuyện gì xảy ra?
> 
> **A:**
> 
> Các server trong Private Subnet sẽ **mất kết nối Internet**.
> 
> - App không thể gọi API bên thứ 3 (Stripe, Twilio...).
>     
> - Database không thể update.
>     
> - **Nhưng:** Traffic nội bộ từ Load Balancer -> App -> DB vẫn hoạt động bình thường. Khách hàng vẫn truy cập web được (trừ các tính năng cần 3rd party).
>     
> - _Fix:_ Dùng NAT Gateway Multi-AZ để dự phòng.
>     

---

**Next Step:**

Bạn đã nắm vững "Móng nhà" (VPC) và "Tường rào" (Security Group).

Bây giờ, hãy đến với thành phần "Điều hòa không khí" giúp phân phối tải cho ngôi nhà: **Load Balancing (ELB/ALB)** - Cách chia traffic thông minh để không server nào bị quá tải.
