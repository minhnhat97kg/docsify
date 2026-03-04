---
title: "System Design - Eventual Consistency"
tags:
  - "system-design"
  - "distributed-systems"
  - "cap-theorem"
  - "consistency"
  - "banking"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Trong thế giới Database truyền thống (SQL), chúng ta quen với Strong Consistency (Tính nhất quán mạnh): Ghi xong là Đọc thấy ngay."
---

## 1. Định nghĩa cốt lõi

Trong thế giới Database truyền thống (SQL), chúng ta quen với **Strong Consistency** (Tính nhất quán mạnh): Ghi xong là Đọc thấy ngay.

Tuy nhiên, định lý **CAP Theorem** phát biểu rằng: Trong một hệ thống phân tán (Distributed System) có khả năng chịu lỗi đường truyền (Partition Tolerance - P), bạn buộc phải chọn giữa:

- **Consistency (C):** Đọc luôn đúng mới nhất, nhưng có thể bị lỗi (chết) nếu mạng chậm.
    
- **Availability (A):** Luôn trả lời (sống dai), nhưng dữ liệu có thể cũ.
    

> [!SUMMARY] Eventual Consistency (Nhất quán cuối cùng)
> 
> Là mô hình chọn **Availability (A)** và **Partition Tolerance (P)**.
> 
> _Cam kết:_ Nếu không có update mới nào vào đối tượng A, thì **cuối cùng (eventually)** tất cả các truy cập vào A đều sẽ trả về giá trị mới nhất.
> 
> _Thực tế:_ Sẽ có một khoảng thời gian ngắn (Inconsistency Window) người dùng nhìn thấy dữ liệu cũ.

---

## 2. Tại sao Bank lại dùng Eventual Consistency?

Nhiều người nghĩ Bank phải luôn là Strong Consistency (ACID). Điều này đúng với **Core Banking (Ledger - Sổ cái)**.

Nhưng với các hệ thống vệ tinh, **Eventual Consistency** là bắt buộc để scale.

### Ví dụ 1: Sao kê lịch sử giao dịch (Transaction History)

- Khi bạn quẹt thẻ, Core Banking trừ tiền ngay (Strong Consistency).
    
- Nhưng để hiện lên App Mobile cho bạn xem "Lịch sử giao dịch", hệ thống thường dùng mô hình **CQRS**.
    
- Data từ Core sẽ được bắn Async sang hệ thống Query (Elasticsearch/Mongo).
    
- -> Bạn quẹt thẻ xong, tiền đã trừ, nhưng F5 app chưa thấy giao dịch đâu. 2 giây sau mới thấy. -> **Chấp nhận được.**
    

### Ví dụ 2: Tích điểm đổi quà (Loyalty System)

- Bạn thanh toán xong, điểm thưởng không cần cộng ngay lập tức.
    
- Có thể cộng sau 5-10 phút cũng không sao.
    
- Ưu tiên việc thanh toán nhanh (Availability) hơn là tính điểm đúng ngay lúc đó.
    

---

## 3. Các mô hình cập nhật (Update Patterns)

Làm sao để các node "Cuối cùng cũng giống nhau"?

### A. Read Repair (Sửa khi đọc)

- Dùng trong Cassandra/DynamoDB.
    
- Client đọc dữ liệu từ nhiều node (A, B, C).
    
- Thấy A, B trả về version 2 (mới), C trả về version 1 (cũ).
    
- Client trả về v2 cho user, đồng thời gửi lệnh update ngầm xuống C để C lên v2.
    

### B. Anti-Entropy (Gossip Protocol)

- Các node trong cluster liên tục "tám chuyện" (Gossip) với nhau ngẫu nhiên.
    
- "Ê tao có data X v2, mày có gì?". "Tao mới có v1". -> OK để tao bắn v2 qua cho.
    
- Quá trình này chạy nền (background), giúp đồng bộ dữ liệu dần dần mà không ảnh hưởng traffic chính.
    

---

## 4. BASE - Đối trọng của ACID

Nếu SQL có ACID, thì NoSQL/Distributed Systems có **BASE**:

- **Basically Available:** Hệ thống cơ bản là luôn sống (dù có thể một số phần bị hỏng).
    
- **Soft state:** Trạng thái hệ thống có thể thay đổi ngay cả khi không có input mới (do quá trình đồng bộ đang chạy ngầm).
    
- **Eventual consistency:** Cuối cùng thì đâu sẽ vào đó.
    

---

## 5. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Làm sao biết "Cuối cùng" là bao lâu (How long is eventually)?
> 
> **A:** Phụ thuộc vào tải hệ thống và độ trễ mạng.
> 
> - Amazon DynamoDB: Thường là vài mili-giây (ms).
>     
> - DNS (Domain Name System): Có thể lên tới 24h.
>     
> - Bank Reporting: Có thể là T+1 (Qua ngày hôm sau).
>     
> 
> Trong thiết kế, cần có SLA rõ ràng (ví dụ: 99.9% dữ liệu đồng bộ dưới 2 giây).

> [!QUESTION] Q: Xử lý xung đột (Conflict) như thế nào trong Eventual Consistency?
> 
> **A:** Khi 2 người cùng sửa một bản ghi ở 2 node khác nhau, khi đồng bộ sẽ bị Conflict.
> 
> Các giải pháp:
> 
> 1. **Last Write Wins (LWW):** Lấy cái nào có Timestamp mới nhất. (Dễ mất dữ liệu).
>     
> 2. **Vector Clocks:** Lưu lịch sử version logic ([A:1, B:1]) để phát hiện xung đột và bắt App phải merge thủ công. (Phức tạp nhưng an toàn).
>     

> [!QUESTION] Q: Facebook Like là Strong hay Eventual?
> 
> **A:** **Eventual.**
> 
> Bạn bấm Like, số counter tăng lên ngay trên máy bạn (Optimistic UI). Nhưng bạn bè bạn có thể chưa thấy số tăng ngay. Vài giây sau mới thấy. Facebook ưu tiên trải nghiệm mượt mà hơn là số đếm chính xác tuyệt đối từng mili-giây.