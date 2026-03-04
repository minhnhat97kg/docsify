---
title: "Database - Indexing: B-Tree"
tags:
  - "database"
  - "postgresql"
  - "indexing"
  - "btree"
  - "performance"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "> > B-Tree (Balanced Tree) là cấu trúc dữ liệu mặc định khi bạn tạo Index (). > > Nó là một cây tự cân bằng (Self-balancing), được tối ưu hóa đặc biệt cho các hệ thống lưu trữ trên đĩa cứng..."
---

## 1. Tổng quan (Mental Model)

> [!SUMMARY] Định nghĩa
> 
> **B-Tree (Balanced Tree)** là cấu trúc dữ liệu mặc định khi bạn tạo Index (`CREATE INDEX`).
> 
> Nó là một cây **tự cân bằng (Self-balancing)**, được tối ưu hóa đặc biệt cho các hệ thống lưu trữ trên đĩa cứng (Disk-based storage).
> 
> _Mục tiêu:_ Giảm thiểu số lần đọc ổ cứng (Disk I/O) để tìm ra dữ liệu.

### Tại sao không dùng Binary Search Tree (Cây nhị phân)?

Cây nhị phân mỗi nút chỉ có 2 nhánh. Nếu dữ liệu lớn, cây sẽ rất **cao** (nhiều tầng).

- Mỗi tầng cây = 1 lần đọc ổ cứng (Page read). Cây cao 20 tầng = 20 lần đọc -> Chậm.
    
- **B-Tree:** Mỗi nút chứa hàng trăm phần tử và đẻ ra hàng trăm nhánh con. Cây trở nên **"lùn" và "bè"** (Wide and Shallow).
    
- _Thực tế:_ Một bảng 1 tỷ dòng trong Postgres thường chỉ cần B-Tree cao khoảng 3-4 tầng. Tìm 1 tỷ dòng chỉ mất 4 lần đọc đĩa.
    

---

## 2. Cấu trúc nội tại (Postgres Specifics)

Postgres thực chất sử dụng biến thể **B+Tree** (Lehman & Yao algorithm) với các đặc điểm:

1. **Root & Internal Nodes:** Chỉ chứa Key (giá trị cột được index) và con trỏ điều hướng. Không chứa dữ liệu thật.
    
2. **Leaf Nodes (Lá):**
    
    - Chứa Key và con trỏ **TID (Tuple ID)** trỏ về dòng dữ liệu thật trong bảng (Heap).
        
    - Các lá được liên kết với nhau bằng danh sách liên kết đôi (**Doubly Linked List**). -> Giúp quét dải (Range Scan) cực nhanh.
        

### Các phép toán hỗ trợ (Big O)

Tất cả thao tác tìm kiếm, chèn, xóa đều tốn chi phí Logarit: **O(log N)**.

|**Toán tử SQL**|**B-Tree hỗ trợ tốt?**|**Giải thích**|
|---|---|---|
|`=`|✅ Tuyệt vời|Đi từ gốc xuống lá.|
|`>`, `<`, `>=`, `<=`|✅ Tuyệt vời|Tìm điểm bắt đầu, rồi duyệt sang phải/trái nhờ Linked List ở lá.|
|`ORDER BY`|✅ Tuyệt vời|Đọc index theo thứ tự sẵn có (không cần sort lại).|
|`LIKE 'abc%'`|✅ Tốt|Tìm theo tiền tố (Prefix).|
|`LIKE '%abc'`|❌ Chết|Wildcard ở đầu -> Phải quét toàn bộ Index (Full Index Scan).|

---

## 3. Index-Only Scan (Vũ khí tối thượng)

Đây là khái niệm quan trọng nhất cần nhớ để tối ưu query.

> [!TIP] Covering Index
> 
> Nếu Index chứa **tất cả** các cột mà câu Query cần, Postgres sẽ lấy dữ liệu **trực tiếp từ Index** mà không cần ghé qua bảng chính (Heap) để lấy dữ liệu nữa.
> 
> -> Tiết kiệm 50-90% I/O.

**Ví dụ:**

SQL

```sql
-- Tạo index trên 2 cột (Composite Index)
CREATE INDEX idx_users_active ON users (status, id);

-- Query này CHỈ dùng Index (Siêu nhanh)
SELECT id FROM users WHERE status = 'active';
```

Vì `id` và `status` đều nằm trong Index, Postgres trả kết quả luôn. Đây gọi là **Index-Only Scan**.

---

## 4. Chiến lược Indexing trong Ngân hàng

### A. Cột nào nên đánh Index?

- **Primary Key / Foreign Key:** Bắt buộc (Postgres tự tạo cho PK). Dùng để join bảng `accounts` với `transactions`.
    
- **Cột có độ phân tán cao (High Cardinality):** `user_id`, `transaction_code`, `email`. (Tìm 1 trong 1 triệu -> Rất hiệu quả).
    
- **Cột dùng để lọc theo dải:** `created_at` (Sao kê lịch sử giao dịch).
    

### B. Cột nào KHÔNG nên đánh Index?

- **Cột ít giá trị (Low Cardinality):** `gender` (Nam/Nữ), `is_deleted` (True/False).
    
    - _Tại sao?_ Nếu bạn tìm `gender = 'Nam'`, nó trả về 50% bảng. Quét cả bảng (Seq Scan) nhanh hơn là nhảy qua nhảy lại Index.
        
- **Cột bị Update liên tục:** Mỗi lần Update dữ liệu, phải Update cả Index (tốn tài nguyên).
    

### C. Composite Index (Index nhiều cột) - Quy tắc "Left-most Prefix"

Nếu bạn tạo index `(A, B, C)`:

- Query `WHERE A=1 AND B=2`: ✅ Dùng Index tốt.
    
- Query `WHERE A=1`: ✅ Dùng Index tốt.
    
- Query `WHERE B=2`: ❌ **KHÔNG** dùng được Index (Vì không bắt đầu bằng A).
    

---

## 5. Câu hỏi phỏng vấn nâng cao

> [!QUESTION] Q: Index B-Tree hoạt động thế nào khi dữ liệu bị xóa?
> 
> **A:** Khi xóa row, Key trong Index không bị xóa ngay lập tức (để đảm bảo MVCC). Nó được đánh dấu là "dead". Sau này khi chèn dữ liệu mới, Postgres sẽ tái sử dụng khoảng trống đó. Nếu không tái sử dụng kịp, Index sẽ bị phình to (Bloat) -> Cần `REINDEX CONCURRENTLY`.

> [!QUESTION] Q: Tại sao `SELECT * FROM users WHERE id = 1` đôi khi lại chậm dù đã có Index?
> 
> **A:** Có thể do **Index Bloat** (Index quá rác), hoặc do **Visibility Map** chưa cập nhật (Postgres phải check Heap để xem row còn sống không), hoặc đơn giản là dữ liệu nằm phân tán trên đĩa (Random I/O) trong khi Seq Scan là Sequential I/O.

> [!QUESTION] Q: Sự khác biệt giữa B-Tree và Hash Index trong Postgres?
> 
> **A:**
> 
> - **B-Tree:** Mặc định, hỗ trợ so sánh bằng `=` và dải `>`, `<`. Bền vững (WAL-logged).
>     
> - **Hash Index:** Chỉ hỗ trợ so sánh bằng `=`. Trước PG 10 không bền vững (crash là mất). Hiện nay đã tốt hơn nhưng vẫn ít dùng vì B-Tree làm tốt gần bằng mà đa năng hơn nhiều.
>