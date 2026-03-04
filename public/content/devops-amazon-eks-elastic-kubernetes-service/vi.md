---
title: "DevOps - Amazon EKS"
tags:
  - "aws"
  - "eks"
  - "kubernetes"
  - "k8s"
  - "architecture"
  - "devops"
  - "banking"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Trong môi trường Ngân hàng (Banking), độ tin cậy (Reliability) và bảo mật (Security) là tối thượng."
---

## 1. Tại sao Bank chọn EKS thay vì tự cài K8s?

Trong môi trường Ngân hàng (Banking), **độ tin cậy (Reliability)** và **bảo mật (Security)** là tối thượng.

- **Tự cài (Self-managed on EC2):** Bạn phải tự lo việc backup `etcd`, tự vá lỗi bảo mật cho API Server, tự cấu hình High Availability (HA) cho Master Node. Nếu Master chết -> Cả Cluster mất lái.
    
- **Dùng EKS (Managed Service):** AWS chịu trách nhiệm quản lý **Control Plane**.
    - AWS cam kết SLA 99.95%.
    - Control Plane tự động trải dài trên 3 Availability Zones (AZ). Nếu 1 AZ sập, K8s vẫn sống.
    - Bank chỉ cần lo quản lý Worker Nodes (nơi chạy App).

---

## 2. Kiến trúc EKS: Control Plane vs. Data Plane

Kiến trúc EKS được chia làm 2 phần tách biệt hoàn toàn.

### A. Control Plane (Vùng cấm địa - AWS quản lý)

Đây là "bộ não" của K8s, bao gồm:

- **API Server:** Cửa ngõ nhận lệnh `kubectl`.
    
- **etcd:** Database lưu trữ trạng thái cluster.
    
- **Scheduler & Controllers:** Điều phối Pod.
    

> [!NOTE] Lưu ý
> 
> Bạn **KHÔNG** nhìn thấy các server này trong EC2 Console. Nó là hộp đen. Bạn chỉ giao tiếp với nó qua HTTPS Endpoint.

### B. Data Plane (Sân chơi - Bạn quản lý)

Đây là nơi các container ứng dụng (Core Banking, Payment App) thực sự chạy. Có 3 chế độ:

1. **Self-managed Node Groups:** Bạn tự bật EC2, tự cài Kubelet, tự join vào cluster. (Bank hay dùng để custom OS/Kernel Security).
    
2. **Managed Node Groups:** AWS bật EC2 giúp bạn, tự động update OS khi có bản vá. Bạn vẫn SSH vào được nếu cần.
    
3. **AWS Fargate (Serverless):** Không có EC2 nào cả. Bạn chỉ định nghĩa Pod, AWS tự tìm chỗ chạy. (Ít dùng cho Core Banking vì khó can thiệp sâu, nhưng tốt cho batch jobs).
    

---

## 3. Networking: VPC CNI Plugin

Khác với K8s chuẩn (dùng mạng Overlay ảo), EKS sử dụng **Amazon VPC CNI**.

- **Đặc điểm:** Mỗi Pod sinh ra sẽ nhận được một **IP thật** từ VPC Subnet (giống như một cái máy tính trong mạng LAN).
    
- **Lợi ích:**
    - Hiệu năng mạng cực cao (không qua lớp NAT trung gian).
    - Dễ dàng debug network.
    - Tích hợp tốt với VPC Flow Logs để audit an ninh.
        

> [!DANGER] Vấn đề cạn kiệt IP (IP Exhaustion)
> Vì mỗi Pod chiếm 1 IP, nếu bạn chạy 10.000 Pods trên các Subnet nhỏ (/24) -> **Hết IP**.
> _Giải pháp:_ Thiết kế VPC cẩn thận, dùng Secondary CIDR block cho Pods.

---

## 4. Security: Kết nối "Kín cổng cao tường"

Bank không bao giờ để API Server lộ ra public internet.

### Private Cluster Endpoint

Trong EKS, bạn có thể cấu hình **API Server Endpoint Access**:

- **Public:** Truy cập qua Internet (Dễ nhưng rủi ro).
- **Private:** Chỉ truy cập được từ trong VPC (qua VPN hoặc Direct Connect). -> **Chuẩn Banking.**
- **Public + Private:** Cho phép Public nhưng giới hạn CIDR (IP văn phòng).
    

### IRSA (IAM Roles for Service Accounts)

Đây là cách áp dụng **Least Privilege** cho Pod.

- Thay vì gắn quyền `S3FullAccess` cho cả cái Node (EC2), ta chỉ gắn quyền đó cho đúng cái Pod `Report-Service`.
- Pod `Payment-Service` nằm cùng Node đó sẽ **không** đọc được S3.
- Cơ chế: EKS tích hợp với OIDC Provider để map IAM Role vào K8s Service Account.
    

---

## 5. Quy trình Upgrade (Nỗi đau lớn nhất)

K8s ra version mới 3 tháng/lần. EKS chỉ hỗ trợ 3-4 version gần nhất. Việc nâng cấp EKS cho Bank là một dự án lớn.

**Quy trình chuẩn:**

1. **Upgrade Control Plane:** Bấm nút trên AWS Console (Mất ~30p, không downtime App, chỉ downtime API Server).
    
2. **Upgrade Data Plane (Worker Nodes):**
    - Tạo Node Group mới (Version mới).
    - **Cordon & Drain** Node cũ (Cấm nhận pod mới, đuổi pod cũ sang node mới).
    - Xóa Node Group cũ.
        
3. **Upgrade Add-ons:** Cập nhật CNI Plugin, CoreDNS, kube-proxy để tương thích.

---

## 6. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Làm sao để Pod A trong EKS truy cập an toàn vào RDS Database trong cùng VPC?
> 
> **A:**
> 
> Sử dụng **Security Groups for Pods** (Tính năng mới của EKS).
> 1. Tạo SG `db-access-sg` cho phép outbound đến port 5432.
> 2. Gắn SG này vào Pod A (thông qua Manifest).
> 3. Trên RDS SG, cho phép inbound từ `db-access-sg`.
>     -> Không cần quản lý IP (vì IP Pod đổi liên tục), quản lý bằng Security Group ID.
>     

> [!QUESTION] Q: EKS có tự động scale không?
> 
> **A:**
> 
> Có, ở 2 cấp độ:
> 
> 4. **Pod Level (HPA - Horizontal Pod Autoscaler):** CPU Pod tăng -> Tăng số lượng Pod.
>     
> 5. **Node Level (Cluster Autoscaler / Karpenter):** Khi Pod sinh ra nhiều mà hết chỗ trên Node -> AWS tự động mua thêm EC2 (Node) mới để chạy.
>     
>     _Lưu ý:_ **Karpenter** là công nghệ mới, nhanh hơn và tối ưu chi phí tốt hơn Cluster Autoscaler truyền thống.
>     

> [!QUESTION] Q: Bạn xử lý thế nào khi `kubectl` bị chậm hoặc timeout?
> 
> **A:**
> 
> Thường do Control Plane bị quá tải hoặc mạng có vấn đề.
> 
> 6. Check AWS Health Dashboard xem EKS Region có sập không.
>     
> 7. Kiểm tra xem mình có đang spam API Server không (Ví dụ: CI/CD pull status liên tục).
>     
> 8. Nếu dùng Private Endpoint, kiểm tra kết nối VPN/Direct Connect.
>     

---

