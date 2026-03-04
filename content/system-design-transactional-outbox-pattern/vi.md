---
title: "System Design - Transactional Outbox Pattern"
tags:
  - "system-design"
  - "microservices"
  - "data-consistency"
  - "kafka"
  - "database"
  - "interview"
  - "distributed-systems"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Trong Microservices, khi một nghiệp vụ xảy ra (ví dụ: Tạo đơn hàng), bạn thường phải làm 2 việc:"
---

## 1. Vấn đề: The Dual Write Problem (Ghi kép)

Trong Microservices, khi một nghiệp vụ xảy ra (ví dụ: Tạo đơn hàng), bạn thường phải làm 2 việc:

1. **Ghi Database:** `INSERT INTO orders ...` (Lưu trạng thái).
    
2. **Gửi Message:** Bắn event `OrderCreated` sang Kafka/RabbitMQ để các service khác (Payment, Inventory) biết.
    

> [!DANGER] Rủi ro
> 
> Nếu bạn thực hiện 2 việc này rời rạc, hệ thống sẽ mất nhất quán:
> 
> - **Kịch bản 1:** Ghi DB thành công, nhưng mạng lỗi không bắn được sang Kafka -> Service Payment không bao giờ biết có đơn hàng.
>     
> - **Kịch bản 2:** Bắn Kafka thành công, nhưng Ghi DB lỗi (vi phạm constraint) -> Service Payment trừ tiền cho một đơn hàng không tồn tại.
>     

Bạn không thể dùng **Distributed Transaction (2PC)** vì nó quá chậm và Kafka không hỗ trợ 2PC chuẩn.

---

## 2. Giải pháp: Transactional Outbox

Tận dụng tính chất **ACID** của RDBMS cục bộ để đảm bảo tính nguyên tử (Atomicity).

> [!SUMMARY] Cơ chế
> 
> Thay vì bắn thẳng sang Kafka, ta tạo một bảng phụ tên là `outbox` ngay trong Database của Service đó.
> 
> Việc "Lưu đơn hàng" và "Lưu tin nhắn vào Outbox" được thực hiện trong **CÙNG MỘT TRANSACTION**.

**Luồng hoạt động:**

1. `BEGIN TRANSACTION`
    
2. `INSERT INTO orders (id, user_id) VALUES (...)`
    
3. `INSERT INTO outbox (id, payload, topic) VALUES (uuid, '{json_event}', 'orders_topic')`
    
4. `COMMIT`
    

Kết quả:

- Nếu DB sập -> Cả Order và Outbox đều rollback -> An toàn.
    
- Nếu DB thành công -> Chắc chắn có tin nhắn trong Outbox chờ gửi.
    

---

## 3. The Message Relay (Người chuyển phát)

Dữ liệu đã nằm trong bảng `outbox`. Làm sao đẩy nó sang Kafka? Có 2 cách:

### A. Polling Publisher (Cách đơn giản)

Viết một con Cronjob/Worker chạy vòng lặp:

1. `SELECT * FROM outbox WHERE processed = false LIMIT 10`.
    
2. Gửi từng message sang Kafka.
    
3. Nếu gửi thành công -> `UPDATE outbox SET processed = true WHERE id = ...` (hoặc xóa dòng đó).
    

- **Ưu điểm:** Dễ code, không cần setup phức tạp.
    
- **Nhược điểm:** Tốn tài nguyên DB (liên tục query). Có độ trễ (Latency) tùy thuộc vào thời gian sleep của worker.
    

### B. Transaction Log Tailing (CDC - Change Data Capture) - _Cách Senior_

Sử dụng công cụ như **Debezium**.

- Debezium đọc trực tiếp **Write-Ahead Log (WAL)** của Database (ví dụ binlog của MySQL).
    
- Mỗi khi có dòng mới được insert vào bảng `outbox`, Debezium bắt được sự kiện và stream thẳng sang Kafka.
    
- **Ưu điểm:** Real-time, không gây áp lực query lên DB chính.
    
- **Nhược điểm:** Setup hạ tầng phức tạp.
    

---

## 4. Code Implementation (Golang + SQL)

**Schema Database:**

SQL

```
CREATE TABLE outbox (
    id UUID PRIMARY KEY,
    aggregate_id VARCHAR(255), -- ID của Order
    topic VARCHAR(255),
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Golang Code (Repository):**

Go

```
func CreateOrder(ctx context.Context, db *sql.DB, order Order) error {
    tx, err := db.BeginTx(ctx, nil)
    if err != nil { return err }
    defer tx.Rollback()

    // 1. Lưu Business Data
    _, err = tx.Exec(`INSERT INTO orders ...`, order.ID, ...)
    if err != nil { return err }

    // 2. Lưu Event vào Outbox (Cùng Transaction)
    eventPayload, _ := json.Marshal(order)
    _, err = tx.Exec(`
        INSERT INTO outbox (id, aggregate_id, topic, payload)
        VALUES ($1, $2, 'order_events', $3)
    `, uuid.New(), order.ID, eventPayload)
    if err != nil { return err }

    // 3. Commit cả hai
    return tx.Commit()
}
```

---

## 5. Vấn đề Duplicate (At-Least-Once Delivery)

Transactional Outbox đảm bảo **At-Least-Once** (Gửi ít nhất 1 lần), nhưng có thể gửi **nhiều hơn 1 lần**.

- _Kịch bản:_ Worker đọc outbox -> Gửi Kafka thành công -> Worker bị crash trước khi kịp update `processed = true`.
    
- _Hệ quả:_ Worker khởi động lại -> Đọc lại dòng cũ -> Gửi lại lần nữa.
    

**Giải pháp:** Consumer (người nhận) bắt buộc phải xử lý **Idempotency** (Tính lũy đẳng).

- Consumer check `message_id` trong Redis. Nếu đã xử lý rồi thì bỏ qua.
    

---

## 6. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Tại sao không gửi Kafka trước rồi mới Commit DB?
> 
> **A:**
> 
> Nếu gửi Kafka xong (Consumer đã nhận được và xử lý, ví dụ gửi Email), nhưng sau đó lệnh `COMMIT` DB bị lỗi (do mất điện, lỗi constraint).
> 
> -> Hậu quả: Khách nhận được Email xác nhận đơn hàng, nhưng trong hệ thống không hề có đơn hàng đó (Phantom Data).

> [!QUESTION] Q: Khi nào nên xóa dữ liệu trong bảng Outbox?
> 
> **A:**
> 
> Bảng Outbox sẽ phình to rất nhanh.
> 
> - _Polling:_ Xóa ngay sau khi gửi thành công (`DELETE` thay vì `UPDATE`).
>     
> - _CDC:_ Debezium hỗ trợ mode tự động xóa dòng sau khi đọc. Hoặc dùng partition table để drop partition cũ định kỳ.
>     

> [!QUESTION] Q: Sự khác biệt giữa Transactional Outbox và Saga Pattern?
> 
> **A:**
> 
> - **Transactional Outbox:** Là kỹ thuật _kỹ thuật_ (technical pattern) để đảm bảo việc gửi message là tin cậy. Nó là viên gạch nền tảng.
>     
> - **Saga Pattern:** Là mô hình _kiến trúc_ (architectural pattern) để quản lý quy trình nghiệp vụ dài qua nhiều service. Saga _sử dụng_ Transactional Outbox để gửi các bước (steps) đi một cách an toàn.
>