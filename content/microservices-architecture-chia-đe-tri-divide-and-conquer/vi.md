---
title: "Microservices Architecture - Chia để trị"
tags:
  - "system-design"
  - "architecture"
  - "microservices"
  - "distributed-systems"
  - "golang"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "> > - Monolith (Nguyên khối): Giống như một Tòa lâu đài khổng lồ bằng đá. > > - _Ưu điểm:_ Dễ xây dựng lúc đầu, mọi thứ ở chung một chỗ, gọi nhau rất nhanh. > > - _Nhược điểm:_ Muốn sửa cái cửa sổ..."
---

## 1. Mental Model: Lâu đài vs. Hạm đội

> [!SUMMARY] So sánh hình tượng
> 
> - **Monolith (Nguyên khối):** Giống như một **Tòa lâu đài** khổng lồ bằng đá.
>     
>     - _Ưu điểm:_ Dễ xây dựng lúc đầu, mọi thứ ở chung một chỗ, gọi nhau rất nhanh.
>         
>     - _Nhược điểm:_ Muốn sửa cái cửa sổ phải rào cả lâu đài. Nếu móng nứt, cả tòa nhà sập. Khó mở rộng (Scale) từng phần.
>         
> - **Microservices (Vi dịch vụ):** Giống như một **Hạm đội tàu chiến**.
>     
>     - _Ưu điểm:_ Linh hoạt. Tàu A chìm, tàu B vẫn bắn nhau tốt. Tàu A cần nhanh thì nâng cấp động cơ tàu A, không ảnh hưởng tàu B.
>         
>     - _Nhược điểm:_ Phức tạp trong điều phối. Làm sao để các tàu không đâm nhau? Làm sao thuyền trưởng (Gateway) ra lệnh cho cả hạm đội cùng lúc?
>         
> 
> ![Image of monolith vs microservices architecture diagram](https://encrypted-tbn3.gstatic.com/licensed-image?q=tbn:ANd9GcTA_le_IzIjwdKWk36wK1HL8iunsCp9sDGqPiosLuyNBmbghonTDVz4v4vieCLxWujaRvyd17_6TTMd2XjSXMGBuGk-cF3gqZPzPOyVmGC9j_zFUmc)
> 
> Shutterstock

---

## 2. Ba nguyên tắc vàng (The Holy Trinity)

Để một hệ thống được gọi là Microservices, nó phải thỏa mãn:

1. **Single Responsibility (Trách nhiệm đơn nhất):**
    
    - Mỗi Service chỉ làm **MỘT** việc và làm thật tốt (Ví dụ: Order Service chỉ quản lý đơn hàng, không quản lý User).
        
2. **Database per Service (CSDL riêng biệt):**
    
    - Đây là quy tắc khó tuân thủ nhất.
        
    - **Service A không được phép SELECT bảng của Service B.**
        
    - Muốn lấy dữ liệu? Phải gọi API của B.
        
    - _Tại sao?_ Để Service B có thể đổi tên cột, đổi từ MySQL sang MongoDB mà không làm Service A bị lỗi (Decoupling).
        
3. **Independently Deployable (Deploy độc lập):**
    
    - Nếu deploy Service A mà bắt buộc phải deploy lại cả Service B và C -> Đó là **Distributed Monolith** (Thảm họa), không phải Microservices.
        

---

## 3. Các thành phần trong hệ sinh thái

Khi xé nhỏ hệ thống, bạn cần thêm rất nhiều "phụ tùng" để chúng hoạt động trơn tru.

### A. API Gateway (Cánh cổng)

- **Vai trò:** Lễ tân. Nhận request từ Mobile/Web, định tuyến đến đúng Service bên trong.
    
- **Chức năng:** Authentication, SSL Termination, Rate Limiting.
    
- **Công nghệ:** Kong, NGINX, Amazon API Gateway.
    

### B. Service Discovery (Danh bạ)

- **Vấn đề:** Service A cần gọi Service B. Nhưng B có 100 containers, IP đổi liên tục. Gọi IP nào?
    
- **Giải pháp:** Service Discovery (như **Consul, Etcd**, hoặc **K8s DNS**) cập nhật danh sách IP sống. A chỉ cần hỏi: "Cho tôi gặp B", hệ thống tự trả về IP.
    

### C. Inter-service Communication (Giao tiếp)

Làm sao các Service nói chuyện với nhau?

|**Loại**|**Công nghệ**|**Đặc điểm**|**Use Case**|
|---|---|---|---|
|**Synchronous** (Đồng bộ)|**REST / gRPC**|A gọi B, A ngồi chờ B trả lời.|Khi cần dữ liệu ngay để hiển thị cho User.|
|**Asynchronous** (Bất đồng bộ)|**Kafka / RabbitMQ**|A bắn tin nhắn, A đi làm việc khác. B rảnh thì đọc tin nhắn xử lý.|Gửi email, xử lý đơn hàng phức tạp, Analytics.|

---

## 4. Ưu và Nhược điểm (Trade-offs)

Senior Engineer không cuồng tín Microservices. Họ cân nhắc sự đánh đổi.

### Ưu điểm (Lợi ích)

1. **Scalability:** Sale 11/11, chỉ có Service "Order" và "Payment" quá tải. Ta chỉ cần bật thêm 100 container Order/Payment. Service "User Profile" giữ nguyên. Tiết kiệm tiền hạ tầng.
    
2. **Resilience (Khả năng hồi phục):** Service "Gợi ý sản phẩm" bị lỗi (Memory Leak) chết. App bán hàng vẫn chạy bình thường, chỉ là user không thấy gợi ý thôi.
    
3. **Tech Freedom:** Team A thích Go làm Payment. Team B thích Python làm AI. Không ai ép ai.
    

### Nhược điểm (Cái giá phải trả)

1. **Complexity:** Debug cực khó. Request đi qua 10 service, lỗi ở đâu? (Cần Tracing).
    
2. **Data Consistency:** Không còn ACID Transaction. Phải dùng **Saga Pattern** và chấp nhận **Eventual Consistency**.
    
3. **Latency:** Gọi hàm nội bộ mất 0.1ms. Gọi qua mạng (gRPC) mất 5-10ms. Mạng chậm -> Hệ thống chậm.
    

---

## 5. Conway's Law (Định luật Conway)

> **"Các tổ chức thiết kế hệ thống ... bị giới hạn bởi việc tạo ra các thiết kế là bản sao của cấu trúc giao tiếp trong tổ chức đó."**

- Nghĩa là: **Cấu trúc Team quyết định cấu trúc Code.**
    
- Nếu bạn có 1 Team Backend 20 người ngồi chung -> Bạn sẽ code ra Monolith.
    
- Muốn làm Microservices thành công? Phải xé nhỏ Team.
    
    - Team Payment (3 Dev, 1 QA).
        
    - Team Order (4 Dev, 1 QA).
        
    - Mỗi Team sở hữu trọn vẹn service của mình (You build it, you run it).
        

---

## 6. Lộ trình chuyển đổi: Strangler Fig Pattern

Đừng bao giờ đập bỏ Monolith xây lại Microservices từ đầu (Big Bang). Hãy dùng chiến thuật **Cây Đa Bóp Cổ (Strangler Fig)** mà ta đã bàn:

1. Đặt API Gateway trước Monolith.
    
2. Tách một module nhỏ (dễ nhất) ra thành Microservice.
    
3. Trỏ Gateway sang Service mới.
    
4. Lặp lại.
    

---

## 7. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Khi nào **KHÔNG NÊN** dùng Microservices?
> 
> **A:**
> 
> 1. **Startups / MVP:** Khi chưa biết rõ Business Model, Domain chưa rõ ràng. Code Monolith sửa nhanh hơn.
>     
> 2. **Team nhỏ:** Dưới 10 kỹ sư. Chi phí vận hành DevOps (K8s, Logging, Monitoring) sẽ nuốt chửng thời gian code tính năng.
>     
> 3. **Hệ thống độ trễ thấp (Low Latency Trading):** Việc nhảy qua lại giữa các network hops làm chậm hệ thống.
>     

> [!QUESTION] Q: Làm sao xử lý Distributed Transaction?
> 
> **A:**
> 
> Không dùng 2-Phase Commit (2PC) vì chậm. Dùng **Saga Pattern** (Choreography hoặc Orchestration) kết hợp với **Compensating Transactions** (Giao dịch bù/hoàn tác) để đảm bảo tính nhất quán cuối cùng.

> [!QUESTION] Q: Làm sao debug khi hệ thống bị lỗi?
> 
> **A:**
> 
> Bắt buộc phải có **Distributed Tracing** (Jaeger/Zipkin).
> 
> Mỗi request vào Gateway được gắn 1 `TraceID`. ID này được truyền qua header của tất cả các service.
> 
> Khi tra log, chỉ cần search `TraceID` là ra toàn bộ hành trình của request đó.

---

**Tổng kết:** Microservices là "sân chơi" của Senior/Architect vì nó yêu cầu kiến thức tổng hợp: Code giỏi (Go/Java), Database sâu (Partitioning/Sharding), DevOps vững (K8s/Docker) và tư duy Hệ thống (Design Patterns).