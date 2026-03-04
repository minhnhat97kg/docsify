---
title: "System Design Interview - The Ultimate Checklist"
tags:
  - "system-design"
  - "interview"
  - "checklist"
  - "architecture"
  - "senior-level"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Time Management: 45 - 60 Minutes"
---

**Time Management:** 45 - 60 Minutes

**Goal:** Chứng minh khả năng **tư duy giải quyết vấn đề** và **đánh đổi (trade-offs)**.

---

## 🕒 Phase 1: Clarify Requirements (5-10 phút)

> **"Đừng bao giờ vẽ ngay lập tức. Hãy hỏi trước."**

Người phỏng vấn cố tình đưa đề bài mơ hồ ("Thiết kế TikTok"). Nhiệm vụ của bạn là thu hẹp phạm vi.

### 1. Functional Requirements (Tính năng)

- **Core Features:** Hệ thống làm gì? (Upload video, Xem feed, Like/Comment).
    
- **Out of Scope:** Cái gì **không** làm? (Livestream, Chat, Analytics). _Hãy mạnh dạn cắt bỏ tính năng không quan trọng._
    

### 2. Non-Functional Requirements (Chất lượng)

- **Scale:** Bao nhiêu DAU (Daily Active Users)? 1 triệu hay 100 triệu?
    
- **Performance:** Latency yêu cầu là bao nhiêu? (< 200ms cho API, < 1s cho upload).
    
- **Consistency:**
    
    - _Banking/Payment:_ **Strong Consistency** (Tiền bạc). [[CAP Theorem]] -> CP.
        
    - _Social/Feed:_ **Eventual Consistency** (Like/View). [[CAP Theorem]] -> AP.
        
- **Availability:** Có cần 99.999% không?
    

---

## 🕒 Phase 2: Back-of-the-envelope Estimation (5 phút)

> **"Tính toán sơ bộ để chọn công nghệ."**

Không cần chính xác 100%, chỉ cần đúng độ lớn (Order of Magnitude).

- **Traffic (QPS):**
    
    - Công thức: `DAU * Request/User / 86400 (giây/ngày)`.
        
    - _Ví dụ:_ 10 triệu DAU * 10 request = 100 triệu req/ngày $\approx$ **1.200 [^1]QPS**. *Queries Per Second* (Đỉnh điểm x2 = 2.400 QPS).
        
    - _Kết luận:_ 2.400 QPS -> Một con DB SQL chịu tốt. Không cần Sharding phức tạp ngay đầu.
        
- **Storage (Lưu trữ):**
    
    - Công thức: `User * Data_Size * Time`.
        
    - _Ví dụ:_ 1 triệu user * 1KB * 365 ngày $\approx$ 365GB/năm.
        
    - _Kết luận:_ 1 ổ cứng chứa đủ. Sau 5 năm mới cần Sharding.
        
- **Bandwidth (Băng thông):** Quan trọng cho hệ thống Video/Ảnh.
    

---

## 🕒 Phase 3: High-Level Design (10-15 phút)

> **"Vẽ bức tranh tổng thể."**

Vẽ các khối hộp (Box) và mũi tên. Đừng đi sâu vào chi tiết vội.

1. **Client:** Mobile App / Web.
    
2. **CDN:** Chứa Static files (JS, CSS, Images). [[CDN & Edge Computing]].
    
3. **Load Balancer (ALB):** Chia tải. [[Load Balancing (ELB)]].
    
4. **API Gateway:** Authentication, Rate Limiting. [[WAF (Web Application Firewall)]].
    
5. **App Servers (Stateless):** Microservices (User Service, Feed Service...). [[EKS (Elastic Kubernetes Service)]].
    
6. **Cache:** Redis Cluster.
    
7. **Database:** Master-Slave Architecture. [[RDS / Aurora]].
    
8. **Async Worker:** Kafka + Consumers (cho tác vụ nặng).
    

---

## 🕒 Phase 4: Deep Dive (15-20 phút)

> **"Đây là lúc Senior tỏa sáng."**

Người phỏng vấn sẽ chọn 1-2 thành phần để đào sâu. Hãy chủ động đề xuất giải pháp và **nêu rõ Trade-offs**.

### 1. Database Choice (SQL vs NoSQL)

- **User/Payment:** Chọn **PostgreSQL/MySQL**. (Cần ACID, Transaction).
    
- **Feed/Logs/Metadata:** Chọn **Cassandra/DynamoDB/MongoDB**. (Cần Write cao, Schema linh hoạt).
    

### 2. Scaling Strategy

- **Read Heavy:** Thêm Read Replicas + Cache (Redis/Memcached). Chiến lược Cache-Aside.
    
- **Write Heavy:**
    
    - Dùng Message Queue ([[Transactional Outbox]] + Kafka) để buffer.
        
    - Database Sharding (chia theo `user_id`).
        

### 3. Handling Concurrency

- **Vấn đề:** Hai người cùng mua 1 vé cuối cùng.
    
- **Giải pháp:** Distributed Lock (Redis Redlock) hoặc DB Pessimistic Lock (`SELECT FOR UPDATE`).
    

### 4. Handling Failures (SPOF)

- **DB chết:** Dùng Multi-AZ Failover.
    
- **Region chết:** Dùng Global Traffic Manager (Route53) + Active-Passive Region.
    

---

## 🕒 Phase 5: Wrap Up (2-3 phút)

> **"Tự phê bình."**

Đừng đợi người phỏng vấn chỉ ra lỗi. Hãy tự nói:

- _"Hệ thống này có điểm yếu ở..."_ (Ví dụ: Latency khi sync data giữa các region).
    
- _"Để giám sát, tôi sẽ cài đặt..."_ (Prometheus, Grafana, ELK Stack).
    
- _"Trong tương lai nếu user tăng x10, tôi sẽ..."_ (Thêm Sharding, đổi sang Aurora Serverless).
    

---

## 🧩 Mental Cheat Sheet (Từ khóa ghi điểm)

|**Vấn đề**|**Giải pháp (Keywords)**|
|---|---|
|**User thấy chậm**|CDN, Redis, Caching, Async (Kafka).|
|**Dữ liệu sai lệch**|Strong Consistency, ACID, Distributed Transaction (Saga).|
|**DB quá tải**|Read Replicas, Sharding, CQRS, Database Indexing.|
|**Security**|HTTPS, WAF, Private Subnet, IAM Roles, KMS.|
|**Single Point of Failure**|Redundancy, Multi-AZ, Load Balancer, Auto Scaling.|
|**Job chạy lâu**|Batch Processing (AWS Batch), Lambda, Kafka.|

---

### 🎉 LỜI CHÚC TỪ GEMINI

Bạn đã đi qua một hành trình dài từ những dòng code Golang đầu tiên, qua các nguyên lý thiết kế, bảo mật, vận hành Cloud, cho đến kiến trúc hệ thống lớn.

Bạn hiện tại không chỉ là một **Developer** biết viết code.

Bạn là một **Engineer** biết xây dựng giải pháp.

**Next Step:**

Bây giờ, hãy tắt máy, nghỉ ngơi một chút để kiến thức lắng xuống.

Hoặc nếu bạn muốn thử lửa ngay, hãy gõ: **"Start Mock Interview"**.

Tôi sẽ đóng vai người phỏng vấn khó tính nhất mà bạn từng gặp (nhưng cũng hỗ trợ bạn nhiệt tình nhất).

Chúc bạn tự tin và thành công! 🚀

[^1]: Queries Per Second
