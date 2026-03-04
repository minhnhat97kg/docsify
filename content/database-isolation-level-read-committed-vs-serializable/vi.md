---
title: "Database - Isolation Levels"
tags:
  - "database"
  - "backend"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Dưới đây là giải thích chi tiết về Isolation Levels, tập trung vào sự khác biệt giữa mức mặc định và mức an toàn nhất, cùng với hiện tượng \"Phantom Read\" nguy hiểm trong môi trường tài chính."
---

Dưới đây là giải thích chi tiết về **Isolation Levels**, tập trung vào sự khác biệt giữa mức mặc định và mức an toàn nhất, cùng với hiện tượng "Phantom Read" nguy hiểm trong môi trường tài chính.

## 1. Phantom Read là gì? (Bóng ma dữ liệu)

Trước khi phân biệt các cấp độ, ta cần hiểu "kẻ thù" mà ta đang đối mặt.

> [!WARNING] Định nghĩa
> 
> **Phantom Read** xảy ra trong một Transaction khi bạn thực hiện cùng một câu truy vấn 2 lần, nhưng kết quả trả về lại **khác nhau về số lượng dòng** (rows) do một Transaction khác vừa chèn thêm (Insert) hoặc xóa bớt (Delete) dữ liệu.
> 
> _Khác với Non-repeatable Read (chỉ thay đổi giá trị của dòng có sẵn), Phantom Read làm thay đổi kết quả của các phép tính tổng hợp (Count, Sum)._

### Ví dụ kịch bản Ngân hàng

- **Transaction A (Giám đốc):** Muốn xem tổng số nhân viên lương > 2000$.
    
    1. Query lần 1: Thấy 10 người.
        
- **Transaction B (HR):** Tuyển dụng nhân viên mới với lương 3000$.
    
    1. Insert nhân viên mới.
        
    2. Commit.
        
- **Transaction A (Giám đốc):**
    
    2. Query lần 2 (vẫn trong transaction đó): Tự nhiên thấy 11 người? -> **Phantom Read**.
    

---

## 2. Read Committed (Mức Mặc Định)

Đây là mức cô lập mặc định của PostgreSQL, SQL Server và Oracle.

- **Nguyên tắc:** "Tôi chỉ đọc những dữ liệu đã được Commit tại thời điểm câu lệnh query bắt đầu chạy."
    
- **Ưu điểm:** Hiệu năng cao, ít khóa (Locking), không chặn người khác ghi.
    
- **Nhược điểm:** Vẫn bị **Phantom Read** và **Non-repeatable Read**.
    

### Demo SQL: Hiện tượng Phantom Read

Giả sử ta có bảng `accounts`.

**Transaction A (Đang chạy):**

SQL

```sql
BEGIN;
-- Lần 1: Tính tổng tiền (Ví dụ ra 1000)
SELECT SUM(balance) FROM accounts;
-- ... Đang xử lý gì đó mất 5 giây ...
```

**Transaction B (Chen ngang):**

SQL

```sql
BEGIN;
INSERT INTO accounts (id, balance) VALUES (99, 500);
COMMIT; -- Transaction B đã commit xong
```

**Transaction A (Quay lại):**

SQL

```sql
-- Lần 2: Tính tổng tiền lại
-- KẾT QUẢ: 1500 (Đã bị lệch so với lần 1 -> Phantom Read)
SELECT SUM(balance) FROM accounts;
COMMIT;
```

> [!INFO] Tại sao Bank vẫn dùng Read Committed?
> 
> Vì nó nhanh. Đa số các thao tác như hiển thị lịch sử giao dịch, tra cứu thông tin khách hàng đều dùng mức này vì user chấp nhận việc dữ liệu có thể mới hơn 1 giây trước.

---

## 3. Serializable (Mức Cao Nhất)

Đây là mức cô lập "cực đoan" nhất. Database giả lập như thể các transaction được xếp hàng chạy lần lượt (Serial), dù thực tế chúng chạy song song.

- **Nguyên tắc:** Đảm bảo toàn vẹn dữ liệu tuyệt đối. Nếu phát hiện rủi ro tranh chấp -> Hủy (Kill) transaction ngay lập tức.
    
- **Cơ chế:** PostgreSQL dùng **SSI (Serializable Snapshot Isolation)**. Nó theo dõi các "mối quan hệ đọc/ghi" nguy hiểm.
    
- **Nhược điểm:** Hiệu năng thấp hơn, và Ứng dụng **BẮT BUỘC** phải có cơ chế **Retry** (thử lại) khi transaction bị lỗi.
    

### Demo SQL: Chặn Phantom Read

**Transaction A (Chế độ Serializable):**

SQL

```sql
BEGIN ISOLATION LEVEL SERIALIZABLE;

-- Lần 1: Tính tổng
SELECT SUM(balance) FROM accounts;
```

**Transaction B (Cố tình chen ngang):**

SQL

```sql
BEGIN;
INSERT INTO accounts (id, balance) VALUES (99, 500);
COMMIT; -- Vẫn Commit thành công bình thường
```

**Transaction A (Thử commit hoặc query lại):**

SQL

```sql
-- Khi Transaction A cố gắng thực hiện tiếp hoặc Commit
-- PostgreSQL phát hiện dữ liệu nền tảng đã bị thay đổi bởi B
SELECT SUM(balance) FROM accounts;

-- ❌ ERROR: could not serialize access due to read/write dependencies among transactions
-- HINT: The transaction might succeed if retried.
```

> [!TIP] Code xử lý trong Backend (Golang/Java)
> 
> Khi dùng Serializable, code của bạn phải bao bọc trong một vòng lặp `Retry`:
> 
> Go
>
> ```go
> for {
>     err := RunTransactionSerializable()
>     if isSerializationFailure(err) {
>         continue // Thử lại
>     }
>     break // Thành công hoặc lỗi khác
> }
> ```

---

## 4. Bảng So Sánh Tổng Kết

|**Đặc điểm**|**Read Committed**|**Serializable**|
|---|---|---|
|**Mức độ an toàn**|Trung bình (Chặn Dirty Read).|Tuyệt đối (Chặn All Anomalies).|
|**Phantom Read**|✅ Có thể xảy ra.|❌ Bị chặn hoàn toàn.|
|**Hiệu năng**|Cao (Tận dụng MVCC tốt).|Thấp hơn (Tốn CPU check dependency).|
|**Xử lý xung đột**|Người sau chờ người trước (Lock waiting).|**Báo lỗi ngay** (Serialization Failure).|
|**Use Case trong Bank**|Liệt kê GD, Xem số dư, App Mobile.|Tính toán lãi suất cuối ngày, Báo cáo tài chính, Kiểm toán.|

---

## 5. Câu hỏi phỏng vấn nâng cao

> [!QUESTION] Q: PostgreSQL có mức `Repeatable Read` không? Nó khác gì Serializable?
> 
> **A:** Có.
> 
> - Theo chuẩn SQL: `Repeatable Read` vẫn có thể bị Phantom Read.
>     
> - **Nhưng trong PostgreSQL:** `Repeatable Read` thực tế **ĐÃ CHẶN ĐƯỢC** Phantom Read nhờ cơ chế Snapshot Isolation.
>     
> - Vậy tại sao cần `Serializable`? -> Vì `Repeatable Read` vẫn bị lỗi **Write Skew** (Lỗi logic khi 2 transaction dựa trên dữ liệu cũ để update 2 dòng khác nhau nhưng logic ràng buộc chéo).
>     

> [!QUESTION] Q: Làm sao để tránh Phantom Read mà không dùng Serializable (vì sợ chậm)?
> 
> **A:** Sử dụng **Locking thủ công** (Pessimistic Locking).
> 
> SQL
>
> ```sql
> -- Khóa cả bảng (Table Lock) hoặc Range Lock (phức tạp)
> LOCK TABLE accounts IN SHARE MODE;
> -- Giờ thì không ai insert được nữa
> ```
> 
> Hoặc sử dụng `SELECT ... FOR UPDATE` nếu thao tác trên các dòng cụ thể.