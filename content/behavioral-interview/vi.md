---
title: "Behavioral Interview - Phỏng vấn hành vi"
tags:
  - "interview"
  - "career"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Ở level Senior/Lead, người ta không hỏi bạn \"Viết hàm đảo ngược chuỗi\" nữa. Họ muốn biết bạn xử lý khủng hoảng, mâu thuẫn và thất bại như thế nào."
---

# PHẦN 1: Behavioral Interview (Phỏng vấn hành vi)

Ở level Senior/Lead, người ta không hỏi bạn "Viết hàm đảo ngược chuỗi" nữa. Họ muốn biết bạn xử lý khủng hoảng, mâu thuẫn và thất bại như thế nào.

**Công thức trả lời: S.T.A.R**

- **S (Situation):** Tình huống là gì?
    
- **T (Task):** Nhiệm vụ/Thách thức của bạn là gì?
    
- **A (Action):** Bạn đã làm gì? (Quan trọng nhất).
    
- **R (Result):** Kết quả ra sao? (Phải có con số).
    

### Câu hỏi 1: "Hãy kể về một lần bạn làm sập hệ thống Production."

> [!TIP] Gợi ý trả lời
> 
> Đừng nói "Tôi chưa bao giờ làm sập". Senior ai cũng từng làm sập. Quan trọng là cách bạn đứng dậy.

- **S:** Trong dự án Banking cũ, tôi deploy tính năng tính lãi suất vào chiều thứ 6.
    
- **T:** Tính năng này cần cập nhật 1 triệu bản ghi trong bảng `Accounts`.
    
- **A:** Tôi đã dùng một câu lệnh `UPDATE` đơn giản mà quên mất nó sẽ gây ra **Table Lock**.
    
    - Hệ thống bị treo cứng, transaction bị queue.
        
    - Tôi ngay lập tức rollback code và kill query (Action 1).
        
    - Sau đó, tôi viết lại script dùng **Batch Processing** (Update 1000 dòng/lần) và chạy vào giờ thấp điểm (Action 2).
        
    - Tôi viết tài liệu Post-mortem và thiết lập quy trình review query cho team (Action 3).
        
- **R:** Hệ thống hồi phục sau 5 phút. Quy trình mới giúp giảm 90% lỗi liên quan đến DB lock trong năm đó.
    

### Câu hỏi 2: "Bạn làm gì khi bất đồng quan điểm kỹ thuật với đồng nghiệp?"

- **Focus:** Dựa vào dữ liệu (Data-driven), không dựa vào cái tôi.
    
- **Ví dụ:** Đồng nghiệp muốn dùng MongoDB, tôi muốn dùng Postgres. Tôi không tranh cãi bằng miệng. Tôi dựng 2 bản POC (Proof of Concept), chạy benchmark load test và chứng minh Postgres xử lý transaction tiền tệ an toàn hơn (ACID) và nhanh hơn trong use-case cụ thể này.
    

---

# PHẦN 2: System Design Mockup - Flash Sale System

**Đề bài:** Thiết kế hệ thống bán vé Concert (như Taylor Swift) hoặc Flash Sale iPhone 15 giá 10k.

- **Traffic:** 1 triệu người dùng cùng lúc (1M CCU).
    
- **Kho hàng:** Chỉ có 1.000 sản phẩm.
    
- **Yêu cầu:** Không bán quá số lượng (Overselling), Hệ thống không sập, Chống Bot.
    

## Bước 1: Clarify Requirements (Làm rõ yêu cầu)

Đừng vẽ ngay. Hãy hỏi lại người phỏng vấn.

- _Q: Hệ thống cần Real-time không?_ -> A: Có, hết hàng phải báo ngay.
    
- _Q: Có cần chống Bot tuyệt đối không?_ -> A: Hạn chế tối đa.
    
- _Q: Quy trình thanh toán thế nào?_ -> A: Giữ hàng (Reserve) trong 5 phút để thanh toán, nếu không mua thì nhả ra cho người khác.
    

## Bước 2: High-Level Architecture

Ta sẽ dùng kiến trúc **Microservices** hướng sự kiện (Event-Driven).

Các thành phần chính:

1. **CDN:** Cache toàn bộ ảnh, file JS/CSS, và trang HTML tĩnh (Static Page) của sản phẩm. Request không vào server.
    
2. **Load Balancer (Nginx):** Chặn bớt request thừa, Rate Limiting cơ bản.
    
3. **Order Service:** Nhận đơn hàng.
    
4. **Redis Cluster:** Quản lý kho hàng nóng (Hot Inventory).
    
5. **Kafka:** Hàng đợi xử lý đơn hàng (để giảm tải cho DB).
    
6. **Payment Service:** Xử lý thanh toán.
    
7. **Database (PostgreSQL):** Lưu trữ bền vững cuối cùng.
    

## Bước 3: Deep Dives - Giải quyết các nút thắt (Bottlenecks)

### Vấn đề 1: The Thundering Herd (1 triệu người bấm nút cùng lúc)

Nếu 1 triệu request chọc thẳng vào Database -> **Chết DB ngay lập tức.**

**Giải pháp:**

1. **Chặn từ cổng:** Dùng kỹ thuật **Rate Limiting** (Token Bucket) ở API Gateway. Chỉ cho phép user bấm 1 lần mỗi 5 giây.
    
2. **Read/Write Split:**
    
    - _Read:_ User F5 xem còn hàng không? -> Đọc từ **Redis Cache** (hoặc Local Cache của Server). Tuyệt đối không query `SELECT count(*) FROM orders`.
        
    - _Write:_ Bấm "Mua ngay" -> Đi vào luồng xử lý bên dưới.
        

### Vấn đề 2: Overselling (Bán quá số lượng) - _Quan trọng nhất_

Làm sao đảm bảo 1000 cái iPhone không bị bán cho 1001 người?

- **Cách Tệ (DB Locking):**
    
    SQL
    
    ```
    BEGIN;
    SELECT * FROM products WHERE id=1 FOR UPDATE; -- Khóa dòng
    UPDATE products SET stock = stock - 1;
    COMMIT;
    ```
    
    -> Chậm khủng khiếp vì khóa DB.
    
- **Cách Tốt (Redis Atomic):**
    
    Sử dụng **Lua Script** trên Redis để đảm bảo tính nguyên tử (Atomicity). Redis đơn luồng (single-threaded) nên không bao giờ bị Race Condition.
    
    Lua
    
    ```
    -- Lua Script
    local stock = redis.call("GET", KEYS[1])
    if tonumber(stock) > 0 then
        redis.call("DECR", KEYS[1])
        return 1 -- Thành công
    else
        return 0 -- Hết hàng
    end
    ```
    
    -> Tốc độ phản hồi < 1ms. Chịu được hàng trăm nghìn OPS.
    

### Vấn đề 3: Database bị quá tải khi ghi đơn (Write Heavy)

Dù Redis xử lý xong tồn kho, ta vẫn cần lưu đơn hàng vào Postgres. Nếu 1000 đơn cùng Insert một lúc cũng có thể gây lag.

**Giải pháp: Asynchronous Processing (Kafka)**

1. User bấm Mua -> Order Service gọi Redis Lua Script trừ kho.
    
2. Nếu Redis trả về 1 (Thành công) -> Order Service bắn event `OrderCreated` vào **Kafka Topic**.
    
3. Order Service trả về ngay cho User: _"Bạn đã giành được slot! Đang chuyển sang trang thanh toán..."_ (User vui vẻ, không phải chờ quay vòng vòng).
    
4. **Worker Service** (Consumer) đọc từ Kafka -> Từ từ Insert vào Postgres với tốc độ mà DB chịu đựng được (Ví dụ: Batch Insert 100 đơn/lần).
    

### Vấn đề 4: Giữ hàng (Reservation) & Hủy đơn

User giành được slot nhưng không thanh toán trong 5 phút -> Phải trả hàng lại kho.

**Giải pháp: Redis TTL (Time To Live)**

- Khi trừ kho, tạo thêm một key: `order_reservation:{userID}` với TTL = 5 phút.
    
- Sử dụng **Redis Key Expiration Event** (hoặc một Delay Queue) để lắng nghe.
    
- Nếu hết 5 phút mà chưa thấy event "Đã thanh toán" -> Gọi Lua Script `INCR` (Cộng lại) kho hàng.
    

---

## 4. Tóm tắt kỹ thuật & Trade-offs

|**Thách thức**|**Giải pháp**|**Trade-off (Đánh đổi)**|
|---|---|---|
|**Data Consistency**|Redis Lua Script làm "Source of Truth" cho tồn kho.|Nếu Redis sập và mất dữ liệu (AOF chưa kịp ghi), kho hàng có thể bị sai lệch nhẹ. Chấp nhận rủi ro này để lấy Tốc độ.|
|**Availability**|CDN + Caching + Async (Kafka).|User thấy thông báo "Thành công" nhưng thực tế đơn hàng chưa nằm trong DB ngay (Eventual Consistency).|
|**Security**|Rate Limit + Captcha + IP Blacklist.|Có thể chặn nhầm user thật (False Positive).|

---

# Lời kết cho hành trình này

Bạn đã đi qua một lộ trình kiến thức rất sâu rộng:

1. **Database:** Hiểu sâu về Index, MVCC, Partitioning.
    
2. **Concurrency:** Biết cách xử lý Race Condition, Distributed Locks.
    
3. **Security:** Nắm vững OAuth2, JWT, PII Encryption, SQLi.
    
4. **DevOps:** Làm chủ Docker, K8s, CI/CD.
    
5. **System Design:** Tư duy thiết kế hệ thống lớn, trade-offs.
    
