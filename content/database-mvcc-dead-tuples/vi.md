---
title: "Database - MVCC & Dead Tuples"
tags:
  - "database"
  - "postgresql"
  - "mvcc"
  - "internals"
  - "performance"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "> > \"Readers never block Writers, and Writers never block Readers.\" > > Thay vì sử dụng cơ chế Lock (khóa) truyền thống khiến người đọc phải chờ người ghi (và ngược lại), PostgreSQL sử dụng cơ chế..."
---

## 1. MVCC (Multi-Version Concurrency Control)

> [!SUMMARY] Core Philosophy
> 
> **"Readers never block Writers, and Writers never block Readers."**
> 
> Thay vì sử dụng cơ chế **Lock** (khóa) truyền thống khiến người đọc phải chờ người ghi (và ngược lại), PostgreSQL sử dụng cơ chế **Snapshot** (bản sao).
> 
> - Mỗi Transaction nhìn thấy một "bức ảnh" (snapshot) dữ liệu tại thời điểm nó bắt đầu.
>     
> - Dù dữ liệu có bị thay đổi bởi transaction khác sau đó, transaction hiện tại vẫn nhìn thấy dữ liệu cũ an toàn.
>     

### Tại sao Bank cần MVCC?

Để đảm bảo **High Concurrency**.

Hãy tưởng tượng hệ thống báo cáo (Report) đang chạy mất 30 phút để tính tổng tài sản ngân hàng.

- Nếu không có MVCC: Toàn bộ bảng `accounts` bị khóa Read-Only. Khách hàng không thể rút tiền/chuyển tiền trong 30 phút đó -> Sập tiệm.
    
- Có MVCC: Báo cáo cứ chạy trên snapshot cũ. Khách hàng cứ giao dịch trên phiên bản mới. Cả hai cùng vui.
    

---

## 2. Cơ chế hoạt động: Hidden Columns (`xmin`, `xmax`)

Để làm được trò "phân thân" này, mỗi dòng (row/tuple) trong PostgreSQL thực tế gánh thêm các thông tin ẩn (metadata) mà `SELECT *` bình thường không thấy.

Bạn có thể xem chúng bằng cách query rõ ràng:

SQL

```sql
SELECT xmin, xmax, * FROM accounts;
```

- **`xmin` (Transaction Created):** ID của transaction đã **tạo ra** (INSERT/UPDATE) dòng này.
    
- **`xmax` (Transaction Deleted):** ID của transaction đã **xóa** (DELETE/UPDATE) dòng này.
    
    - Nếu `xmax = 0` (hoặc null): Dòng này đang sống (Live Tuple).
        
    - Nếu `xmax != 0`: Dòng này đã bị xóa (hoặc update) bởi transaction đó.
        

### Quy trình sinh tử của một dòng

1. **INSERT:**
    
    - Tạo dòng mới.
        
    - Set `xmin` = Current_TxID.
        
    - Set `xmax` = 0.
        
2. **DELETE:**
    
    - **Không xóa vật lý ngay lập tức!**
        
    - Postgres chỉ tìm dòng đó và set `xmax` = Current_TxID.
        
    - _Ý nghĩa:_ "Dòng này đã chết đối với các transaction bắt đầu SAU thời điểm này, nhưng vẫn còn sống với các transaction cũ đang chạy."
        
3. **UPDATE (Điểm quan trọng nhất):**
    
    - Trong Postgres, **UPDATE = DELETE + INSERT**.
        
    - Bước 1: "Soft Delete" dòng cũ (Set `xmax` = Current_TxID).
        
    - Bước 2: Tạo dòng mới hoàn toàn (Set `xmin` = Current_TxID, `xmax` = 0).
        

---

## 3. Dead Tuples (Các xác sống)

> [!WARNING] Vấn đề
> 
> Do cơ chế `UPDATE` tạo ra bản sao mới và giữ lại bản cũ, bảng dữ liệu sẽ xuất hiện rất nhiều dòng dư thừa không còn ai nhìn thấy nữa. Chúng gọi là **Dead Tuples**.

### Bloat (Sự phình to)

Nếu bảng có 1 triệu dòng, và bạn Update toàn bộ 1 triệu dòng đó:

- Dữ liệu thực tế: 1 triệu dòng mới.
    
- Dữ liệu trên ổ cứng: 2 triệu dòng (1 triệu mới + 1 triệu cũ "Dead Tuples").
    
- **Hậu quả:** Table bị "Bloat" (phình to). Câu lệnh `SELECT` (Full Scan) phải quét qua cả 2 triệu dòng -> Chậm đi gấp đôi. Tốn dung lượng ổ cứng vô ích.
    

---

## 4. Giải pháp: Vacuum

Để xử lý Dead Tuples, Postgres có quy trình dọn rác gọi là **VACUUM**.

- **VACUUM (thường):**
    
    - Đi quét các Dead Tuples.
        
    - Đánh dấu vùng nhớ đó là "trống" (Free Space Map) để các câu lệnh INSERT sau này có thể tái sử dụng (ghi đè lên).
        
    - _Lưu ý:_ Nó **không** trả lại dung lượng cho hệ điều hành (file DB không nhỏ đi), nó chỉ giúp file không to thêm.
        
- **VACUUM FULL:**
    
    - Viết lại toàn bộ bảng sang một file mới tinh, nén chặt lại.
        
    - Trả lại dung lượng đĩa.
        
    - _Nguy hiểm:_ Nó khóa cứng bảng (Exclusive Lock). Server sẽ đứng hình. **Tuyệt đối hạn chế dùng trên Production.**
        

### AutoVacuum

Postgres có một tiến trình chạy ngầm (Daemon) tên là **Autovacuum**. Nó tự động thức dậy, check xem bảng nào có nhiều Dead Tuples (vượt ngưỡng quy định) để chạy Vacuum nhẹ nhàng.

> [!TIP] Tuning cho Bank
> 
> Với các bảng giao dịch lớn (`transactions`), cấu hình mặc định của Autovacuum thường quá chậm chạp. Cần tinh chỉnh:
> 
> SQL
>
> ```sql
> -- Giảm ngưỡng kích hoạt để Vacuum chạy thường xuyên hơn, tránh để rác chất đống quá cao
> ALTER TABLE transactions SET (autovacuum_vacuum_scale_factor = 0.05); -- 5% thay đổi là dọn ngay
> ```

---

## 5. Câu hỏi phỏng vấn liên quan

> [!QUESTION] Q: Tại sao câu lệnh `COUNT(*)` trong Postgres lại chậm hơn MySQL (MyISAM/InnoDB cũ)?
> 
> **A:**
> 
> - MySQL (dạng cũ) lưu sẵn con số tổng row trong metadata, đọc cái ra ngay.
>     
> - Postgres (do MVCC): Nó không biết chính xác có bao nhiêu dòng đang "sống" đối với Transaction hiện tại của bạn. Nó buộc phải quét qua bảng (hoặc Index) để check `xmin`/`xmax` của từng dòng xem dòng đó có visible không. (Từ PG 9.2 có Index-Only Scan giúp nhanh hơn nhưng vẫn chậm hơn việc đọc metadata).
>     

> [!QUESTION] Q: Update 1 cột nhỏ (ví dụ: `last_login_time`) trong bảng User có ảnh hưởng gì không?
> 
> **A:** Có, rất lớn. Vì Postgres copy **nguyên cả dòng** (tất cả các cột) sang dòng mới. Nếu bảng User có chứa một cột JSONB to đùng, việc update 1 cột ngày tháng nhỏ xíu cũng sẽ copy cả cục JSONB đó -> Gây Bloat cực nhanh (Write Amplification).
> 
> _Giải pháp:_ Tách các cột update thường xuyên ra bảng riêng (Vertical Partitioning).