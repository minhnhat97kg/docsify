---
title: "Database - Connection Pool"
tags:
  - "database"
  - "postgresql"
  - "pgbouncer"
  - "system-design"
  - "performance"
  - "devops"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "> > Khác với MySQL hay Oracle (dùng Thread), PostgreSQL sử dụng mô hình Process-based. > > - Mỗi kết nối (Client Connection) sẽ fork ra một tiến trình OS mới (). > > - Mỗi tiến trình này tốn..."
---

## 1. Vấn đề: Tại sao cần Connection Pooling?

> [!SUMMARY] PostgreSQL Process Model
> 
> Khác với MySQL hay Oracle (dùng Thread), PostgreSQL sử dụng mô hình **Process-based**.
> 
> - Mỗi kết nối (Client Connection) sẽ fork ra một tiến trình OS mới (`postgres backend process`).
>     
> - Mỗi tiến trình này tốn khoảng **5MB - 10MB RAM** (chưa kể bộ nhớ chia sẻ).
>     

**Bài toán Ngân hàng:**

- Vào ngày nhận lương, có **50.000 user** mở App Mobile cùng lúc để check số dư.
    
- Nếu App kết nối trực tiếp vào DB:
    
    - 50.000 connections x 10MB = **500 GB RAM**.
        
    - -> **Server sập ngay lập tức (OOM)**.
        
- Thực tế: Trong 50.000 user đó, chỉ có 100 người đang thực sự bấm nút "Chuyển tiền" (Active), 49.900 người còn lại đang... nhìn màn hình (Idle).
    

-> **Giải pháp:** Cần một lớp trung gian quản lý kết nối. Đó là **PgBouncer**.

---

## 2. PgBouncer là gì?

PgBouncer là một **Lightweight Connection Pooler** cho PostgreSQL.

- Nó duy trì một số lượng nhỏ kết nối thật tới Database (ví dụ: 100 kết nối).
    
- Nó chấp nhận hàng ngàn kết nối từ Client (App).
    
- Nó "lừa" App rằng App đang giữ kết nối, nhưng thực tế PgBouncer chỉ cấp kết nối thật khi App gửi câu lệnh SQL.
    

---

## 3. Các chế độ (Pooling Modes) - Câu hỏi Interview

PgBouncer có 3 chế độ, nhưng bạn chỉ cần quan tâm 2 chế độ chính:

### A. Session Pooling (Mặc định - An toàn nhất)

- **Cơ chế:** Khi Client kết nối, PgBouncer cấp một Server Connection và giữ nó cho Client đó **cho đến khi Client ngắt kết nối (Disconnect)**.
    
- **Đặc điểm:** 1 Client = 1 Server Connection (Long-lived).
    
- **Ưu điểm:** Hỗ trợ tất cả tính năng của Postgres (Temporary Tables, Prepared Statements, Session settings `SET ...`).
    
- **Nhược điểm:** Không giải quyết được bài toán 50k user idle. Nếu 50k user login, ta vẫn cần 50k kết nối xuống DB (hoặc user thứ 101 sẽ bị queue).
    
- **Use Case:** Dùng cho các ứng dụng cũ không thể sửa code, hoặc các tác vụ dài hạn (Migrate data).
    

### B. Transaction Pooling (Chuẩn cho Bank - High Concurrency)

- **Cơ chế:** PgBouncer chỉ cấp Server Connection cho Client trong thời gian thực hiện một **Transaction** (`BEGIN` ... `COMMIT`).
    
    - Vừa `COMMIT` xong, PgBouncer thu hồi connection ngay lập tức để cấp cho thằng khác.
        
    - Trong lúc Client đang tính toán (Application logic) hoặc User đang nhìn màn hình, Server Connection được giải phóng.
        
- **Hiệu quả:** 100 Server Connections có thể phục vụ 10.000 Concurrent Users (miễn là họ không bấm nút cùng một tích tắc).
    
- **Nhược điểm (Pitfalls):**
    
    - **Session State bị mất:** Bạn không thể dùng `SET TIME ZONE` ở đầu phiên và hy vọng nó tồn tại mãi.
        
    - **Prepared Statements:** Mặc định không dùng được (vì PreparedStatement gắn liền với connection cụ thể). Phải tắt feature này ở Driver hoặc config phức tạp.
        
    - **Temporary Tables:** Mất ngay sau khi commit.
        

### C. Statement Pooling (Ít dùng)

- **Cơ chế:** Thu hồi connection ngay sau mỗi câu lệnh SQL đơn lẻ.
    
- **Nhược điểm:** Phá vỡ Transaction nhiều bước (Multi-statement transaction). **Cấm dùng cho Banking.**
    

---

## 4. Cấu hình Demo (`pgbouncer.ini`)

Ini, TOML

```ini
[databases]
; Định nghĩa alias và chế độ pool
banking_db = host=127.0.0.1 port=5432 dbname=core_banking pool_mode=transaction

[pgbouncer]
listen_addr = *
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt

; Tổng số kết nối tối đa cho phép từ App (Client)
max_client_conn = 10000

; Tổng số kết nối thật tối đa tới Postgres (Server)
default_pool_size = 100
```

---

## 5. System Design: Vị trí của PgBouncer

Thông thường có 2 cách triển khai:

1. **Centralized Pooling (Phổ biến):**
    
    - App Server -> [PgBouncer Cluster] -> PostgreSQL Primary.
        
    - Giúp kiểm soát tổng lượng connection vào DB từ tất cả các microservices.
        
2. **Sidecar (K8s Pattern):**
    
    - Mỗi Pod App chạy kèm 1 container PgBouncer (localhost).
        
    - Giúp giảm latency mạng, nhưng khó kiểm soát tổng connection toàn hệ thống.
        

---

## 6. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Khi chuyển từ Session Mode sang Transaction Mode, App của tôi bị lỗi "Prepared statement does not exist". Tại sao?
> 
> **A:**
> 
> - Các thư viện ORM (Hibernate, GORM,...) thường sử dụng **Prepared Statements** (`PREPARE stmt1...; EXECUTE stmt1...`) để tăng tốc và bảo mật.
>     
> - Trong Transaction Mode, câu lệnh `PREPARE` có thể chạy trên Connection A, nhưng câu `EXECUTE` lại bị PgBouncer điều hướng sang Connection B (nơi chưa hề có stmt1). -> Lỗi.
>     
> - **Giải pháp:**
>     
>     1. Tắt Prepared Statements ở phía Client Driver (Ví dụ JDBC: `prepareThreshold=0`).
>         
>     2. Dùng chế độ `binary_parameters` thay vì `prepare`.
>         

> [!QUESTION] Q: App Go/Java đã có sẵn Connection Pool bên trong rồi (HikariCP, sql.DB), tại sao vẫn cần PgBouncer?
> 
> **A:**
> 
> - **App Pool (Client-side):** Giúp tái sử dụng kết nối trong nội bộ 1 instance của App. Nhưng nếu ta scale lên 100 instances (Pods), mỗi pod giữ 10 kết nối -> Tổng là 1000 kết nối tới DB.
>     
> - **PgBouncer (Server-side):** Là chốt chặn cuối cùng bảo vệ DB. Bất kể bạn scale App lên bao nhiêu Pod, PgBouncer vẫn đảm bảo DB chỉ nhận tối đa (ví dụ) 100 kết nối, phần còn lại sẽ được Queue tại PgBouncer.
>     

> [!TIP] Lời khuyên cho Bank System
> 
> Luôn sử dụng **Transaction Pooling** cho các OLTP Service (User-facing App). Chỉ dùng Session Pooling cho các Admin Tool hoặc Batch Job đặc thù.