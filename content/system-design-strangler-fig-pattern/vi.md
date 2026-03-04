---
title: "System Design - Strangler Fig Pattern"
tags:
  - "system-design"
  - "architecture"
  - "migration"
  - "refactoring"
  - "microservices"
  - "martinfowler"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Bạn có một hệ thống Core Banking cũ kỹ (Monolith) viết bằng Java 6/Cobol, code rối rắm (Spaghetti code), deploy mất cả ngày."
---

## 1. Vấn đề: "Big Bang" Rewrite (Cú nổ lớn)

Bạn có một hệ thống Core Banking cũ kỹ (Monolith) viết bằng Java 6/Cobol, code rối rắm (Spaghetti code), deploy mất cả ngày.

Sếp bảo: _"Đập đi xây lại hết bằng Golang Microservices!"_

> [!DANGER] Tại sao "Big Bang" thường thất bại?
> 
> 1. **Thời gian:** Mất 2-3 năm để viết lại tính năng cũ. Trong thời gian đó, không ra được tính năng mới (Feature Freeze).
>     
> 2. **Rủi ro:** Khi switch hệ thống mới (Cutover day), hàng tấn lỗi tiềm ẩn bùng nổ.
>     
> 3. **Kinh doanh:** Đối thủ vượt mặt vì bạn bận loay hoay với code cũ.
>     

**Giải pháp:** **Strangler Fig Pattern (Chiến lược Cây Đa bóp cổ)**.

_Thay vì đập bỏ cây cũ, hãy trồng một cây mới (Microservices) quấn quanh cây cũ (Monolith). Cây mới lớn dần, lấy hết ánh sáng (traffic), cây cũ sẽ chết dần và mục nát._

---

## 2. Cơ chế hoạt động (The Mechanics)

Thành phần quan trọng nhất: **The Facade (Lớp mặt nạ / API Gateway)**.

1. **Bước 1: Chèn Proxy (Planting).**
    
    - Đặt một API Gateway (NGINX, Kong, Cloud Gateway) đứng trước Monolith.
        
    - Ban đầu, Gateway trỏ 100% traffic về Monolith. User không thấy sự thay đổi.
        
2. **Bước 2: Xây dựng tính năng Mới (New Growth).**
    
    - Có yêu cầu làm tính năng "Thanh toán QR".
        
    - Không code vào Monolith. Code thành một Microservice riêng (Golang).
        
    - Cấu hình Gateway: Route `/api/qr` -> Microservice. Các route khác -> Monolith.
        
3. **Bước 3: Di dời tính năng Cũ (Strangling).**
    
    - Chọn một module nhỏ của Monolith (ví dụ: User Profile) để viết lại sang Microservice.
        
    - Khi xong, đổi config Gateway: Route `/api/profile` -> Microservice mới.
        
    - Tắt code Profile trong Monolith.
        
4. **Bước 4: Loại bỏ (Cleanup).**
    
    - Lặp lại cho đến khi Monolith chỉ còn là cái vỏ rỗng.
        
    - Tắt Monolith vĩnh viễn.
        

---

## 3. Cấu hình Demo (NGINX as Strangler Facade)

Đây là cách đơn giản nhất để hình dung chiến lược này qua file config.

Nginx

```
upstream legacy_monolith {
    server 10.0.0.1:8080; # Server Java cũ
}

upstream new_microservice_payment {
    server 10.0.0.2:3000; # Server Go mới
}

server {
    listen 80;

    # 1. Các tính năng đã migrate -> Trỏ sang Service mới
    location /api/v1/payments {
        proxy_pass http://new_microservice_payment;
    }

    # 2. Tất cả tính năng còn lại -> Vẫn về Monolith (Catch-all)
    location / {
        proxy_pass http://legacy_monolith;
    }
}
```

---

## 4. Thử thách khó nhất: Database (Data Synchronization)

Code thì dễ tách, nhưng Database mới là ác mộng. Monolith thường dùng chung 1 DB khổng lồ.

Khi tách Microservice "Payment" ra, nó cần dữ liệu từ bảng `users` (vẫn nằm trong Monolith DB).

**Các chiến lược xử lý Data:**

### A. Shared Database (Tạm thời)

- Microservice mới vẫn connect vào DB cũ.
    
- _Ưu điểm:_ Nhanh, không cần migrate data.
    
- _Nhược điểm:_ **Anti-pattern**. Microservice không độc lập (Tight Coupling). DB schema đổi -> Cả 2 chết.
    

### B. Sync qua Backfill & Dual Write (Chuẩn mực)

1. Tạo DB riêng cho Microservice mới.
    
2. **Backfill:** Copy dữ liệu từ DB cũ sang DB mới.
    
3. **Dual Write (Ghi kép):** Sửa code Monolith, mỗi khi có Insert/Update -> Bắn event (Kafka) hoặc gọi API sang Microservice mới để update luôn.
    
4. Khi dữ liệu đã khớp 100% -> Switch Gateway sang Microservice mới.
    

### C. Change Data Capture (CDC - Debezium)

- Không sửa code Monolith.
    
- Dùng tool (Debezium) đọc Transaction Log của DB cũ -> Bắn event sang Kafka -> Microservice mới hứng event để update DB mình.
    
- _Ưu điểm:_ Decouple hoàn toàn.
    

---

## 5. Ưu và Nhược điểm

|**Đặc điểm**|**Big Bang Rewrite**|**Strangler Fig**|
|---|---|---|
|**Rủi ro**|Cực cao (High Risk).|Thấp (Low Risk). Sai đâu sửa đó.|
|**Thời gian ra mắt**|Lâu (Vài năm).|Nhanh (Incremental).|
|**Phản hồi**|Chậm.|Tức thì. User dùng ngay tính năng mới.|
|**Độ phức tạp**|Thấp (chỉ có 1 hệ thống).|**Cao**. Phải duy trì 2 hệ thống song song trong thời gian dài.|

---

## 6. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Làm sao để rollback nếu Microservice mới bị lỗi sau khi switch?
> 
> **A:** Nhờ lớp **Gateway Facade**.
> 
> Vì việc switch chỉ là đổi dòng config trong NGINX/Gateway. Nếu Service mới lỗi, ta chỉ cần revert config NGINX để trỏ lại về Monolith (vẫn đang chạy ngầm).
> 
> _Điều kiện:_ Dữ liệu sinh ra trong lúc Service mới chạy phải được sync ngược lại Monolith (Reverse Sync) nếu muốn rollback không mất dữ liệu.

> [!QUESTION] Q: Strangler Fig có áp dụng được cho Database Schema không?
> 
> **A:** Có, khái niệm tương tự là **"Parallel Run" (Chạy song song)**.
> 
> 1. Thêm cột mới.
>     
> 2. Code ghi vào cả cột cũ và cột mới.
>     
> 3. Backfill dữ liệu cũ sang cột mới.
>     
> 4. Code đọc từ cột mới.
>     
> 5. Xóa cột cũ.
>     

> [!QUESTION] Q: Khi nào KHÔNG nên dùng Strangler Fig?
> 
> **A:**
> 
> 6. Khi Monolith quá nhỏ hoặc quá đơn giản (Over-engineering).
>     
> 7. Khi Monolith đã "chết lâm sàng" (không thể build/deploy được nữa) -> Lúc này bắt buộc phải viết lại bên cạnh.
>