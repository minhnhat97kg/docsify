---
title: "Database - Advanced SQL Concepts"
tags:
  - "sql"
  - "database"
  - "query-processing"
  - "performance"
  - "backend"
  - "data-manipulation"
date: "2026-03-04"
author: "nathan.huynh"
summary: "---"
---

---

---

## 1. Bản chất: Dây chuyền lọc dữ liệu (The SQL Pipeline)

Về mặt chuyên môn, các từ khóa SQL được thiết kế dựa trên lý thuyết tập hợp. Khi một câu Query chạy, Database sẽ đi qua một quy trình logic cố định để thu hẹp phạm vi dữ liệu.

> [!SUMMARY] Mental Model: Dây chuyền sản xuất nước đóng chai
> 
> 1. **FROM & JOIN:** Lấy nguồn nước từ các hồ chứa (Bảng dữ liệu). Đây là bước tốn diện tích nhất.
>     
> 2. **WHERE:** Bộ lọc thô để loại bỏ rác và tạp chất ngay tại nguồn.
>     
> 3. **GROUP BY:** Gom các chai nước cùng loại vào từng thùng.
>     
> 4. **HAVING:** Kiểm tra xem thùng nào không đạt chuẩn (ví dụ: thùng có ít hơn 10 chai) thì loại bỏ.
>     
> 5. **SELECT:** Dán nhãn cho chai nước. (Lúc này bạn mới chọn tên cột, tính toán biểu thức).
>     
> 6. **ORDER BY & LIMIT:** Sắp xếp các thùng lên xe tải và chỉ lấy đúng số lượng xe cần thiết để đi giao hàng.
>     
> 
> **Sự khác biệt lớn nhất:** Bạn không thể dán nhãn (SELECT) trước khi lấy nước (FROM). Đó là lý do bạn không thể dùng Alias (tên thay thế) tạo ra ở SELECT trong mệnh đề WHERE.

---

## 2. Giải phẫu (Anatomy): Các từ khóa "Sống còn"

### A. Xử lý logic và NULL: `CASE WHEN` & `COALESCE`

Đây là những từ khóa giúp câu SQL của bạn có khả năng "tư duy" và xử lý dữ liệu bẩn.

SQL

```
SELECT 
    product_name,
    -- COALESCE: Lấy giá trị đầu tiên không NULL (Cực kỳ quan trọng để tránh lỗi tính toán)
    COALESCE(discount_price, original_price, 0) AS final_price,
    -- CASE WHEN: "If-else" ngay trong SQL
    CASE 
        WHEN stock_quantity = 0 THEN 'Out of Stock'
        WHEN stock_quantity < 10 THEN 'Low Stock'
        ELSE 'Available'
    END AS inventory_status
FROM products;
```

### B. Kiểm tra sự tồn tại: `EXISTS` vs `IN`

Khi cần lọc dữ liệu dựa trên một bảng khác, cách bạn chọn từ khóa sẽ quyết định tốc độ.

SQL

```
-- Dùng EXISTS cho các subquery phức tạp (Hiệu năng tốt hơn vì dừng ngay khi tìm thấy 1 dòng khớp)
SELECT name FROM users u
WHERE EXIST
    SELECT 1 FROM orders o 
    WHERE o.user_id = u.id AND o.status = 'COMPLETED'
);
```

### C. Gộp tập hợp: `UNION` vs `UNION ALL`

Sử dụng sai sẽ khiến DB của bạn phải tốn tài nguyên chạy một tác vụ ẩn: **Sort để xóa trùng**.

---

## 3. So sánh đánh đổi: UNION vs. UNION ALL

|**Đặc điểm**|**UNION**|**UNION ALL**|
|---|---|---|
|**Hành động**|Gộp các dòng và **Xóa trùng (Distinct)**.|Gộp tất cả các dòng, giữ nguyên trùng lặp.|
|**Hiệu năng**|Chậm (Vì DB phải Sort và so sánh để tìm dòng trùng).|**Rất nhanh** (Chỉ đơn giản là nối thêm dữ liệu).|
|**Dùng khi nào**|Chắc chắn muốn kết quả duy nhất, không trùng.|Khi bạn biết chắc dữ liệu 2 bên không trùng, hoặc không quan tâm việc trùng.|

---

## 4. Vấn đề nhức nhối & Giải pháp

### Vấn đề 1: Lạm dụng `DISTINCT`

Nhiều Dev có thói quen thêm `DISTINCT` vào mọi câu Query để "chắc ăn" không bị trùng.

- **Hậu quả:** `DISTINCT` là một tác vụ cực kỳ nặng. Nó ép DB phải Sort toàn bộ kết quả trên Disk/RAM.
    
- **Giải pháp:** Hãy kiểm tra lại logic `JOIN`. Nếu `JOIN` đúng và dữ liệu chuẩn, bạn thường không cần `DISTINCT`.
    

### Vấn đề 2: Lọc dữ liệu sau khi gộp nhóm (WHERE vs HAVING)

- **Lỗi:** Dùng `HAVING` để lọc các cột không liên quan đến hàm tổng hợp (như lọc theo `user_id`).
    
- **Giải pháp:** Luôn dùng `WHERE` để loại bỏ dữ liệu càng sớm càng tốt (trước khi Group By). `HAVING` chỉ dành cho các kết quả của `SUM`, `COUNT`, `AVG`.
    

---

## 5. SQL Keyword Checklist

1. **`COALESCE` mọi lúc:** Luôn dùng khi tính toán các cột có thể bị NULL để tránh kết quả trả về là NULL toàn bộ.
    
2. **Sắp xếp thứ tự JOIN:** Đưa bảng có ít dữ liệu nhất (sau khi lọc) lên trước để làm "driving table".
    
3. **Mệnh đề `ON` vs `WHERE`:** Trong `LEFT JOIN`, điều kiện ở `ON` ảnh hưởng đến việc kết nối, điều kiện ở `WHERE` sẽ lọc bỏ toàn bộ dòng sau khi đã kết nối.
    
4. **`LIKE` Pattern:** Tránh dùng `%keyword%`. Nếu bắt buộc phải tìm kiếm toàn văn, hãy dùng **Full-Text Search (FTS)** của DB thay vì dùng `LIKE`.
    
5. **`TRUNCATE` vs `DELETE`:** Nếu muốn xóa sạch bảng, dùng `TRUNCATE`. Nó không ghi log từng dòng nên nhanh hơn hàng trăm lần.
    

---

## 6. Góc phỏng vấn thực chiến

> [!QUESTION] Q1: Bạn có thể dùng Alias đặt ở SELECT trong mệnh đề WHERE không? Tại sao?
> 
> **A:** Không. Vì `WHERE` thực thi trước `SELECT`. Lúc `WHERE` đang chạy, cái tên Alias đó vẫn chưa tồn tại trong bộ nhớ của Optimizer.

> [!QUESTION] Q2: Khi nào thì `IN` nhanh hơn `EXISTS`?
> 
> **A:** Thường thì `IN` nhanh hơn khi danh sách trong Subquery rất nhỏ và đã được lưu trong bộ nhớ. `EXISTS` hiệu quả hơn khi bảng trong Subquery rất lớn vì nó hỗ trợ "Early Exit".

> [!QUESTION] Q3: `NULL` có bằng `NULL` không?
> 
> **A:** Không. Trong SQL, `NULL = NULL` trả về kết quả là `UNKNOWN` (không phải True cũng không phải False). Để kiểm tra, bắt buộc dùng `IS NULL` hoặc `IS NOT NULL`.

> [!QUESTION] Q4: Sự khác biệt giữa `CROSS JOIN` và `INNER JOIN` là gì?
> 
> **A:** `CROSS JOIN` tạo ra một tích Descartes (mọi dòng bảng A kết hợp với mọi dòng bảng B). `INNER JOIN` chỉ kết hợp các dòng thỏa mãn một điều kiện cụ thể. Một `CROSS JOIN` có kèm theo `WHERE` thực chất chính là một `INNER JOIN`.

**Bạn có muốn mình hướng dẫn cách viết SQL để xử lý dữ liệu phân cấp (Recursive CTE) - ví dụ như cấu trúc cây thư mục hoặc sơ đồ tổ chức không?**