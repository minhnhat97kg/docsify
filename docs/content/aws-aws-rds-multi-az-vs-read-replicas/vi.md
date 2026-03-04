---
title: "AWS - RDS Multi-AZ vs Read Replicas"
tags:
  - "aws"
  - "cloud"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Rất nhiều người nhầm lẫn giữa Backup dự phòng (High Availability) và Mở rộng hiệu năng (Scalability). - Multi-AZ: Dành cho Disaster Recovery (Cứu hộ khi có cháy nổ). Không giúp chạy nhanh hơn. -..."
---

## 1. Sự nhầm lẫn kinh điển

Rất nhiều người nhầm lẫn giữa **Backup dự phòng (High Availability)** và **Mở rộng hiệu năng (Scalability)**.
- **Multi-AZ:** Dành cho **Disaster Recovery** (Cứu hộ khi có cháy nổ). Không giúp chạy nhanh hơn.
- **Read Replicas:** Dành cho **Performance** (Chạy nhanh hơn). Không đảm bảo tự động cứu hộ (với RDS thường).

---

## 2. Multi-AZ (High Availability - HA)

**Mục tiêu:** "Thà chết chứ không mất dữ liệu". Đảm bảo DB luôn sống dù Data Center bị sập.

- **Cơ chế:** **Synchronous Replication (Đồng bộ tức thì)**.
    1. App viết dữ liệu vào **Primary DB** (ở AZ A).
    2. Dữ liệu được copy sang **Standby DB** (ở AZ B).
    3. Chỉ khi cả 2 nơi đều ghi thành công, RDS mới báo "Success" về cho App.
        
- **Hiệu năng:** Ghi chậm hơn một chút (do chờ sync mạng), nhưng an toàn tuyệt đối (Strong Consistency).
- **Failover:** Nếu Primary chết -> AWS tự động trỏ DNS sang Standby -> Standby lên làm Primary. App không cần sửa code kết nối.
- **Lưu ý:** Bạn **KHÔNG THỂ** đọc dữ liệu từ Standby DB. Nó chỉ nằm im chờ chết thay thôi.
    

---

## 3. Read Replicas (Scaling)

**Mục tiêu:** "Chia lửa" cho DB chính. Giảm tải các câu lệnh `SELECT`.

- **Cơ chế:** **Asynchronous Replication (Đồng bộ bất đồng bộ)**.
    
    1. Primary DB ghi xong là báo Success ngay.
        
    2. Sau đó âm thầm bắn log sang Replica.
        
- **Hiệu năng:** Ghi nhanh. Nhưng Replica có thể bị **trễ (Lag)** vài giây so với Primary (Eventual Consistency).
    
- **Usage:** App phải sửa code để trỏ các lệnh `SELECT` (Report, Analytics) vào địa chỉ của Replica. Lệnh `INSERT/UPDATE` vẫn vào Primary.
    
- **Lưu ý:** Nếu Primary chết, Replica **KHÔNG** tự động thay thế (trừ khi bạn promote thủ công hoặc dùng Aurora).
    

---

## 4. Amazon Aurora (Next Level)

Aurora xóa nhòa ranh giới giữa 2 khái niệm trên.

- **Storage:** Dữ liệu được chia nhỏ và nhân bản ra **6 bản copy** trên 3 AZ.
- **Reader = Failover Target:** Các Read Replica trong Aurora cũng chính là các Standby.
- **Failover cực nhanh:** Nếu Primary chết, Aurora tự động thăng cấp 1 Read Replica lên làm Primary trong < 30s.
- **Global Database:** Có thể tạo Replica ở region khác (Singapore -> US) với độ trễ < 1s.
---

## 5. So sánh nhanh

|**Đặc điểm**|**Multi-AZ (RDS thường)**|**Read Replicas (RDS thường)**|**Aurora Replicas**|
|---|---|---|---|
|**Mục đích**|Dự phòng (HA)|Tăng tốc đọc (Performance)|Cả hai|
|**Replication**|Synchronous (Chậm, an toàn)|Asynchronous (Nhanh, rủi ro lag)|Async (Shared Storage)|
|**Có đọc được không?**|**KHÔNG** (Standby chỉ chờ)|**CÓ**|**CÓ**|
|**Failover**|Tự động|Thủ công (phải Promote)|Tự động|
|**Endpoint**|Dùng chung 1 DNS|Mỗi Replica 1 DNS riêng|Có Reader Endpoint (Load Balance tự động)|

---

## 6. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Tại sao hệ thống bị chậm khi bật Multi-AZ?
> 
> **A:** Do cơ chế **Synchronous Replication**. Mỗi lệnh `COMMIT` phải chờ dữ liệu đi qua đường truyền mạng sang AZ bên kia và ghi xuống đĩa xong mới trả về. Độ trễ (Latency) tăng lên vài mili-giây. Đây là cái giá phải trả cho sự an toàn (Consistency).

> [!QUESTION] Q: Làm sao scale việc GHI (Write Scaling) cho RDS?
> 
> **A:** Read Replicas chỉ scale ĐỌC.
> RDS (Relational DB) rất khó scale GHI theo chiều ngang (Horizontal).
> - **Cách 1:** Scale Up (Vertical) - Tăng CPU/RAM cho máy Primary.
> - **Cách 2:** Sharding (Chia nhỏ DB) ở tầng Application.
> - **Cách 3:** Chuyển sang **Aurora Serverless** hoặc **DynamoDB** (NoSQL) nếu cần write throughput cực lớn.
>     

> [!QUESTION] Q: Replica Lag là gì? Xử lý sao?
> 
> **A:** Là hiện tượng Primary đã có dữ liệu mới, nhưng Replica chưa kịp cập nhật.
> User vừa update Profile xong (Primary), F5 lại trang (đọc từ Replica) thấy vẫn là Profile cũ.
> _Fix:_ Với các luồng quan trọng (sau khi ghi cần đọc ngay), hãy bắt buộc đọc từ **Primary**, đừng đọc từ Replica.

