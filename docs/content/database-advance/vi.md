---
title: "Database - SQL Query Optimization"
tags:
  - "sql"
  - "database"
  - "query-optimization"
  - "postgresql"
  - "mysql"
  - "performance"
  - "indexing"
date: "2026-03-04"
author: "nathan.huynh"
summary: "---"
---

---

---

## 1. Bản chất: "What, not How"

Về mặt chuyên môn, **SQL (Structured Query Language)** là một ngôn ngữ khai báo dựa trên đại số tập hợp (Relational Algebra). Khi bạn viết một câu SQL, bạn đang mô tả **kết quả** bạn muốn (The What), chứ không phải **quy trình** để lấy nó (The How). Hệ quản trị cơ sở dữ liệu (RDBMS) sẽ sử dụng một bộ tối ưu hóa (Optimizer) để tìm ra con đường ngắn nhất lấy dữ liệu đó.

> [!SUMMARY] Mental Model: Gọi món tại nhà hàng
> 
> **Lập trình Imperative (Java/Go/Python):** Giống như bạn vào bếp và hướng dẫn đầu bếp: "Đầu tiên lấy chảo, bật lửa, cho dầu, đập trứng, đảo 3 vòng...". Nếu bạn sai một bước, món ăn hỏng.
> 
> **SQL (Declarative):** Giống như bạn cầm thực đơn và nói với bồi bàn: "Cho tôi một phần trứng ốp la chín kỹ, không hành". Bạn không quan tâm họ dùng chảo gì hay đảo mấy lần. Việc của bạn là mô tả đúng "đặc điểm" của món ăn.
> 
> **Khác biệt lớn nhất:** Bạn phải tin tưởng và hỗ trợ "đầu bếp" (Optimizer) bằng cách cung cấp các chỉ mục (Index) và viết câu lệnh rõ ràng để họ không phải "lật tung cả bếp" (Full Table Scan) để tìm một quả trứng.

---

## 2. Giải phẫu (Anatomy): 3 Kỹ thuật SQL "Thượng thừa"

### A. Window Functions (Hàm cửa sổ)

Thay vì `GROUP BY` làm gộp các dòng lại, Window Functions cho phép bạn tính toán trên một tập hợp các dòng mà vẫn giữ nguyên chi tiết từng dòng.

SQL

``` sql
-- Tính tổng doanh thu của từng user và phần trăm đóng góp của mỗi đơn hàng
SELECT 
    user_id,
    order_id,
    amount,
    SUM(amount) OVER(PARTITION BY user_id) as total_user_spent,
    amount * 100.0 / SUM(amount) OVER(PARTITION BY user_id) as percent_contribution
FROM orders;
```

### B. Common Table Expressions (CTE)

CTE giúp câu lệnh SQL của bạn trông giống như code logic, dễ đọc, dễ debug hơn là các Subquery lồng nhau "hại não".

SQL

```
-- Sử dụng CTE để phân tách logic tìm top users và lấy chi tiết
WITH top_users AS (
    SELECT user_id 
    FROM orders 
    GROUP BY user_id 
    HAVING SUM(amount) > 1000
)
SELECT u.name, u.email, o.order_date
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE u.id IN (SELECT user_id FROM top_users);
```

### C. Indexing (Chỉ mục)

Hiểu về B-Tree Index là bắt buộc. Index không phải là "phép thuật", nó là một cấu trúc dữ liệu bổ trợ để tìm kiếm nhanh hơn.

SQL

```
-- Tạo Composite Index (Index tổ hợp)
-- Thứ tự cột rất quan trọng: (Last_Name, First_Name) khác (First_Name, Last_Name)
CREATE INDEX idx_user_fullname ON users (last_name, first_name);
```

---

## 3. So sánh đánh đổi: JOIN vs. Subquery

Nhiều người phân vân không biết dùng cái nào sẽ nhanh hơn.

|**Đặc điểm**|**JOIN**|**Subquery (IN/EXISTS)**|
|---|---|---|
|**Bản chất**|Kết hợp các bảng theo hàng ngang.|Lọc tập dữ liệu dựa trên một tập khác.|
|**Hiệu năng**|Thường tốt hơn cho tập dữ liệu lớn vì Optimizer dễ tối ưu.|Có thể chậm nếu Subquery bị thực thi lại nhiều lần (Correlated).|
|**Độ đọc hiểu**|Dễ theo dõi luồng quan hệ dữ liệu.|Dễ hiểu cho các bài toán logic "có/không".|
|**Sử dụng khi**|Cần lấy dữ liệu từ cả hai bảng.|Chỉ cần kiểm tra sự tồn tại hoặc lọc đơn giản.|

---

## 4. Vấn đề nhức nhối & Giải pháp

### Vấn đề 1: Lỗi N+1 (The Silent Killer)

Đây là lỗi kinh điển khi dùng ORM (như Hibernate, GORM). Bạn lấy 100 bản ghi, sau đó với mỗi bản ghi bạn lại gọi DB thêm 1 lần nữa để lấy dữ liệu liên quan.

- **Giải pháp:** Sử dụng **Eager Loading** hoặc viết một câu `JOIN` duy nhất để lấy tất cả dữ liệu cần thiết trong 1 lần truy vấn (Round-trip).
    

### Vấn đề 2: SARGability (Search Argument-able)

Viết SQL khiến Index trở nên vô dụng.

- **Ví dụ tệ:** `SELECT * FROM users WHERE YEAR(created_at) = 2024;` (DB phải tính toán hàm YEAR cho từng dòng, không dùng được Index).
    
- **Giải pháp:** `SELECT * FROM users WHERE created_at >= '2024-01-01' AND created_at < '2025-01-01';` (Index hoạt động hoàn hảo).
    

---

## 5. SQL Performance Checklist

1. **No `SELECT *`:** Chỉ lấy những cột cần thiết. Tiết kiệm băng thông và tận dụng được Covering Index.
    
2. **Explain Plan:** Luôn chạy `EXPLAIN ANALYZE` (PostgreSQL) hoặc `EXPLAIN` (MySQL) để xem DB đang thực sự làm gì.
    
3. **Limit & Pagination:** Luôn có `LIMIT` cho các API lấy danh sách. Đừng bao giờ trả về 1 triệu dòng cho Frontend.
    
4. **Avoid Wildcards at the beginning:** `LIKE '%abc'` sẽ gây Full Table Scan. Hãy dùng `LIKE 'abc%'` nếu có thể.
    
5. **Data Types:** Chọn kiểu dữ liệu nhỏ nhất có thể (ví dụ: `INT` vs `BIGINT`). Data nhỏ hơn = Index nhỏ hơn = Cache được nhiều hơn.
    

---

## 6. Góc phỏng vấn thực chiến

> [!QUESTION] Q1: Sự khác biệt giữa `WHERE` và `HAVING` là gì?
> 
> **A:** `WHERE` dùng để lọc các dòng **trước** khi gộp nhóm (Aggregation). `HAVING` dùng để lọc các nhóm **sau** khi đã gộp nhóm. Bạn không thể dùng hàm tổng hợp (như `SUM`, `COUNT`) trong `WHERE`.

> [!QUESTION] Q2: Tại sao một câu Query chạy nhanh ở Local nhưng lại rất chậm trên Production?
> 
> **A:** 1. Do lượng dữ liệu khác biệt (Index Scan chuyển thành Full Table Scan). 2. Do "Data Distribution" (dữ liệu trên Pro bị lệch - Skewed). 3. Do tài nguyên phần cứng (IOPS, Memory) bị tranh chấp bởi các process khác.

> [!QUESTION] Q3: Làm thế nào để xóa 10 triệu dòng trong một bảng lớn mà không làm treo hệ thống?
> 
> **A:** Đừng dùng một câu `DELETE` duy nhất. Hãy chia nhỏ ra (Batching), xóa mỗi lần 5000-10000 dòng trong một vòng lặp, kèm theo lệnh `SLEEP` ngắn để DB có thời gian "thở" và không làm đầy Transaction Log.

> [!QUESTION] Q4: "Covering Index" là gì?
> 
> **A:** Là một Index chứa tất cả các cột mà câu truy vấn cần. Khi đó, DB chỉ cần đọc dữ liệu từ Index (nằm trên RAM) và không cần phải truy cập vào ổ đĩa để đọc bảng dữ liệu gốc (Heap), giúp tăng tốc độ cực lớn.

**Bạn có muốn mình phân tích sâu hơn về cách đọc một Execution Plan để tìm ra "nút thắt cổ chai" (Bottleneck) trong một câu Query chậm không?**