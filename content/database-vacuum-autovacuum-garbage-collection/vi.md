---
title: "Database - Vacuum & Autovacuum"
tags:
  - "database"
  - "postgresql"
  - "vacuum"
  - "performance"
  - "maintenance"
  - "interview"
  - "mvcc"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Như đã đề cập trong phần MVCC, khi bạn hoặc , PostgreSQL không thực sự xóa dữ liệu cũ khỏi ổ cứng ngay lập tức."
---

## 1. Bản chất vấn đề: Bloat Data (Dữ liệu phình to)

Như đã đề cập trong phần **MVCC**, khi bạn `UPDATE` hoặc `DELETE`, PostgreSQL **không thực sự xóa** dữ liệu cũ khỏi ổ cứng ngay lập tức.

- `DELETE` = Đánh dấu dòng đó là "đã chết" (Dead Tuple).
    
- `UPDATE` = Đánh dấu dòng cũ chết + Chèn dòng mới.
    

> [!WARNING] Hệ quả
> 
> Nếu không dọn dẹp, file dữ liệu sẽ chứa đầy xác chết (Dead Tuples).
> 
> -> File phình to (Bloat).
> 
> -> `SELECT` phải quét qua cả rác để tìm dữ liệu sống -> **Hiệu năng tụt dốc không phanh.**

---

## 2. VACUUM là gì?

VACUUM là quy trình "dọn rác" để tái chế không gian lưu trữ. Có 2 loại chính:

### A. Standard VACUUM (Thường)

- **Hành động:** Đi quét các Dead Tuples và đánh dấu vùng nhớ đó vào **Free Space Map (FSM)**.
    
- **Kết quả:** File trên đĩa **KHÔNG NHỎ ĐI**. Nhưng Postgres sẽ tái sử dụng các chỗ trống đó cho các lệnh `INSERT` / `UPDATE` tiếp theo.
    
- **Ưu điểm:** Chạy song song với production (Non-blocking). Không khóa bảng.
    

### B. VACUUM FULL (Mạnh tay)

- **Hành động:** Viết lại (Rewrite) toàn bộ bảng sang một file mới tinh, nén chặt lại, không còn lỗ hổng.
    
- **Kết quả:** Trả lại dung lượng đĩa cho hệ điều hành. File nhỏ đi.
    
- **Nhược điểm chết người:** Khóa cứng bảng (**Access Exclusive Lock**).
    
    - Trong lúc chạy, không ai được đọc/ghi gì hết.
        
    - **TUYỆT ĐỐI HẠN CHẾ** chạy trên hệ thống Bank đang online (Downtime).
        

---

## 3. Autovacuum (Người lao công cần mẫn)

Thay vì để DBA phải chạy lệnh tay, Postgres có tiến trình ngầm **Autovacuum Daemon**.

- Nó liên tục theo dõi (track) số lượng dead tuples của các bảng.
    
- Khi số lượng rác vượt ngưỡng quy định -> Nó tự động kích hoạt Standard Vacuum.
    

> [!DANGER] Sai lầm kinh điển
> 
> Nhiều người thấy Autovacuum chiếm I/O nên tắt nó đi (`autovacuum = off`).
> 
> -> **Đừng bao giờ làm thế!** Hệ thống sẽ chạy mượt lúc đầu, nhưng sau vài tuần sẽ chậm dần đều và cuối cùng là sập hẳn do Bloat hoặc Wraparound.

---

## 4. Transaction ID Wraparound (Cơn ác mộng tỷ đô)

Đây là lý do quan trọng nhất buộc Vacuum phải chạy, ngay cả khi bạn không xóa dữ liệu nào.

- **Vấn đề:** Postgres dùng số nguyên 32-bit để đánh dấu Transaction ID (XID). Giới hạn khoảng **4 tỷ** transaction.
    
- **Wraparound:** Khi xài hết 4 tỷ số, bộ đếm quay về 0.
    
    - Lúc này, các dữ liệu cũ (XID = 100) sẽ bị Postgres hiểu nhầm là "được tạo ra ở tương lai" (so với XID hiện tại là 0).
        
    - -> **Dữ liệu cũ bỗng dưng TÀNG HÌNH (Mất dữ liệu).**
        
- **Giải pháp (Freezing):** Vacuum có nhiệm vụ đi quét các dòng cũ và đánh dấu bit đặc biệt "Frozen" (Vĩnh cửu). Để Postgres biết dòng này thuộc về quá khứ xa xưa, không cần so sánh XID nữa.
    

---

## 5. Tuning Autovacuum cho High Load

Cấu hình mặc định của Postgres rất bảo thủ, phù hợp bảng nhỏ, nhưng tệ hại với bảng lớn (vài trăm GB).

**Công thức kích hoạt:**

`Ngưỡng = autovacuum_vacuum_threshold + (autovacuum_vacuum_scale_factor * Số dòng của bảng)`

- _Mặc định:_ `scale_factor = 0.2` (20%).
    
- _Ví dụ:_ Bảng `transactions` có 100 triệu dòng.
    
    - Phải đợi có **20 triệu dòng rác** (Dead Tuples) thì Autovacuum mới chạy.
        
    - -> Lúc đó dọn rất lâu, gây lag hệ thống.
        

**Tuning (Best Practice):**

Chỉnh riêng cho bảng lớn để Vacuum chạy thường xuyên hơn nhưng mỗi lần chạy nhanh hơn (Chia nhỏ để trị).

SQL

```sql
-- Giảm scale factor xuống 1% (hoặc 0.5%) cho bảng to
ALTER TABLE transactions SET (
    autovacuum_vacuum_scale_factor = 0.01,  -- 1% thay đổi là dọn ngay
    autovacuum_vacuum_cost_limit = 1000     -- Tăng budget I/O cho nó chạy nhanh hơn
);
```

---

## 6. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Làm sao biết bảng nào đang bị Bloat?
> 
> **A:** Sử dụng extension `pgstattuple` hoặc query các view hệ thống (`pg_stat_user_tables`).
> 
> SQL
>
> ```sql
> SELECT n_dead_tup, n_live_tup,
>        (n_dead_tup / n_live_tup::float) as bloat_ratio
> FROM pg_stat_user_tables
> WHERE n_live_tup > 0;
> ```

> [!QUESTION] Q: `DELETE FROM table` vs `TRUNCATE table`?
> 
> **A:**
> 
> - `DELETE`: Sinh ra Dead Tuples (cần Vacuum), có thể Rollback, kích hoạt Trigger.
>     
> - `TRUNCATE`: Xóa vật lý file dữ liệu ngay lập tức (Rất nhanh), không sinh Dead Tuples, không kích hoạt Trigger `ON DELETE`, không thể Rollback (trong một số DB khác, nhưng trong Postgres `TRUNCATE` **có thể** Rollback nếu nằm trong Transaction block).
>     

> [!QUESTION] Q: Tại sao đôi khi Autovacuum chạy mãi không xong?
> 
> **A:** Do có một **Long-running Transaction** đang treo.
> 
> Nếu có một transaction mở từ sáng đến chiều mà không Commit/Rollback, Vacuum không thể dọn dẹp các dead tuples được tạo ra sau thời điểm transaction đó bắt đầu (do cơ chế MVCC phải giữ lại để cho transaction kia đọc).
> 
> -> **Monitor:** Phải kill các transaction treo quá lâu (`idle in transaction`).