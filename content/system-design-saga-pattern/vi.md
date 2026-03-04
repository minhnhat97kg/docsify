---
title: "System Design - Saga Pattern"
tags:
  - "system-design"
  - "microservices"
  - "saga-pattern"
  - "distributed-transaction"
  - "banking"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Trong kiến trúc Monolith, ta có ACID Transaction của Database để đảm bảo an toàn."
---

## 1. Vấn đề: 2PC vs. Microservices

Trong kiến trúc Monolith, ta có **ACID Transaction** của Database để đảm bảo an toàn.

Nhưng khi chuyển sang Microservices (mỗi service có DB riêng):

- Service `Order` tạo đơn hàng.
    
- Service `Payment` trừ tiền.
    
- Service `Inventory` trừ kho.
    

Làm sao để đảm bảo cả 3 cái này cùng thành công hoặc cùng thất bại?

**Giải pháp cũ: Two-Phase Commit (2PC / XA)**

- Khóa (Lock) tất cả Database cùng lúc.
    
- **Vấn đề:** Quá chậm, giữ lock lâu, điểm chết (Single Point of Failure), không scale được.
    

**Giải pháp hiện đại: Saga Pattern**

- Chia transaction lớn thành chuỗi các **Local Transactions** nhỏ.
    
- Mỗi service tự commit DB của mình và bắn sự kiện để kích hoạt service tiếp theo.
    

---

## 2. Cơ chế: Compensating Transactions (Giao dịch bù)

Điểm cốt lõi của Saga là **không có Rollback tự động** (như `ROLLBACK` trong SQL). Vì Service A đã commit xong rồi, không thể undo DB được nữa.

Ta phải viết code để thực hiện hành động ngược lại -> Gọi là **Compensating Transaction**.

|**Hành động (Action)**|**Giao dịch bù (Compensation)**|
|---|---|
|`CreateOrder()`|`RejectOrder()`|
|`DeductMoney($100)`|`RefundMoney($100)`|
|`ReserveStock(Item A)`|`ReleaseStock(Item A)`|

**Quy trình lỗi:**

1. `Order` thành công.
    
2. `Payment` thành công.
    
3. `Inventory` **thất bại** (Hết hàng).
    
4. -> Hệ thống phải tự động gọi: `RefundMoney()` -> `RejectOrder()` để đưa dữ liệu về trạng thái nhất quán.
    

---

## 3. Hai cách triển khai Saga

### A. Choreography (Vũ điệu - Phi tập trung)

Các service tự nói chuyện với nhau qua Message Broker (Kafka/RabbitMQ). Không ai làm nhạc trưởng.

- **Luồng:** `Order` xong -> bắn event `OrderCreated`. `Payment` nghe thấy -> trừ tiền -> bắn `PaymentProcessed`.
    
- **Ưu điểm:** Đơn giản, ít điểm nghẽn.
    
- **Nhược điểm:**
    
    - **Cyclic Dependencies:** Service A chờ B, B chờ A -> Rối như tơ vò.
        
    - Khó theo dõi trạng thái hiện tại của transaction đang nằm ở đâu.
        

### B. Orchestration (Nhạc trưởng - Tập trung) - _Khuyên dùng cho Bank_

Có một Service riêng (gọi là **Orchestrator** hoặc **Saga Coordinator**) đứng ra điều phối. Nó ra lệnh cho từng thằng làm việc.

- **Luồng:** `OrderService` (Saga) bảo `PaymentService`: "Trừ tiền đi".
    
- Nếu `Payment` trả về OK -> Saga bảo `Inventory`: "Trừ kho đi".
    
- Nếu `Inventory` trả về Lỗi -> Saga bảo `Payment`: "Hoàn tiền lại đi".
    
- **Ưu điểm:** Dễ quản lý, logic tập trung, tránh phụ thuộc chéo.
    
- **Nhược điểm:** Thêm một service phải bảo trì.
    

---

## 4. Code Demo: Orchestration Saga (Golang)

Mô hình này thường dùng **State Machine**.

Go

``` go
package main

// Định nghĩa các bước trong Saga
const (
    StepCreateOrder = "CREATE_ORDER"
    StepPayment     = "PAYMENT"
    StepStock       = "STOCK"
)

type SagaOrchestrator struct {
    paymentSvc PaymentClient
    stockSvc   StockClient
    orderSvc   OrderClient
}

func (s *SagaOrchestrator) ProcessOrder(ctx context.Context, orderID string) error {
    // BƯỚC 1: Order đã tạo (Local Transaction)
    
    // BƯỚC 2: Gọi Payment (Remote)
    err := s.paymentSvc.Deduct(ctx, orderID)
    if err != nil {
        // Lỗi Payment -> Hủy Order ngay
        s.orderSvc.Reject(ctx, orderID) // Compensation
        return err
    }

    // BƯỚC 3: Gọi Inventory (Remote)
    err = s.stockSvc.Reserve(ctx, orderID)
    if err != nil {
        // Lỗi Stock -> Phải Undo cả bước 2 và bước 1
        
        // 3.1. Compensation cho bước 2 (Hoàn tiền)
        s.paymentSvc.Refund(ctx, orderID) 
        
        // 3.2. Compensation cho bước 1 (Hủy đơn)
        s.orderSvc.Reject(ctx, orderID)
        
        return err
    }

    // Thành công toàn bộ
    s.orderSvc.Approve(ctx, orderID)
    return nil
}
```

> [!TIP] State Persistence
> 
> Trong thực tế, Orchestrator phải lưu trạng thái vào DB sau mỗi bước (ví dụ: `saga_state` table).
> 
> Để nếu Orchestrator bị sập nguồn giữa chừng, khi khởi động lại nó biết đang làm dở bước nào để tiếp tục hoặc rollback.

---

## 5. Saga & ACID: Sự thiếu vắng của "I" (Isolation)

Đây là câu hỏi "sát thủ" trong phỏng vấn.

Saga đảm bảo ACD (Atomicity, Consistency, Durability) nhưng **thiếu Isolation (Tính cô lập)**.

**Vấn đề:**

- User A chuyển tiền. (Saga: Trừ tiền A -> Chờ -> Cộng tiền B).
    
- Giữa lúc "Chờ", tiền của A đã bị trừ, nhưng B chưa nhận được.
    
- Nếu User A truy vấn số dư lúc này -> Thấy mất tiền nhưng giao dịch chưa xong.
    
- Hoặc tệ hơn: User A nạp tiền rồi rút ngay. Saga nạp tiền đang chạy (chưa xong hẳn) nhưng Saga rút tiền đã nhảy vào can thiệp.
    

**Giải pháp:**

1. **Semantic Lock:** Đánh dấu bản ghi là `PENDING_APPROVAL`. Các transaction khác không được đụng vào bản ghi đang Pending.
    
2. **Commutative Updates:** Thiết kế sao cho thứ tự thực hiện không quan trọng (Cộng trước trừ sau hay trừ trước cộng sau đều ra kết quả đúng).
    

---

## 6. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Nếu bước Compensation (Hoàn tiền) cũng bị lỗi thì sao? (Ví dụ: DB Payment sập hẳn).
> 
> **A:** Đây là kịch bản ác mộng.
> 
> - **Retry:** Hệ thống phải liên tục Retry lệnh Compensation (Exponential Backoff) cho đến khi thành công.
>     
> - **Human Intervention:** Nếu Retry 24h vẫn lỗi, phải đẩy vào "Dead Letter Queue" và bắn alert cho đội vận hành (Admin) vào xử lý thủ công (Reconcile). _Không được phép bỏ qua._
>     

> [!QUESTION] Q: Khi nào nên dùng Choreography thay vì Orchestration?
> 
> **A:**
> 
> - **Choreography:** Khi luồng đơn giản (2-3 services), team nhỏ, muốn phát triển nhanh.
>     
> - **Orchestration:** Khi luồng phức tạp (Banking Flow), cần tuân thủ quy trình nghiêm ngặt, cần Audit log rõ ràng ai gọi ai, và transaction trải dài qua > 4 services.
>     

> [!QUESTION] Q: Saga Pattern đảm bảo Strong Consistency hay Eventual Consistency?
> 
> **A:** **Eventual Consistency** (Nhất quán cuối cùng).
> 
> Sẽ có một khoảng thời gian ngắn hệ thống không nhất quán (tiền đã trừ bên A nhưng chưa cộng bên B). Nhưng cuối cùng, Saga đảm bảo tiền sẽ về đúng chỗ (hoặc cộng B, hoặc hoàn lại A).