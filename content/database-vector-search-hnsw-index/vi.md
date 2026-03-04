---
title: "Database - Vector Search & HNSW Index"
tags:
  - "database"
  - "postgresql"
  - "pgvector"
  - "ai"
  - "machine-learning"
  - "hnsw"
  - "banking"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "> > pgvector là một extension mã nguồn mở biến PostgreSQL thành một Vector Database. > > Nó cho phép bạn lưu trữ các Vector Embeddings (mảng số thực nhiều chiều) ngay trong bảng dữ liệu thông..."
---

## 1. pgvector là gì? (Mental Model)

> [!SUMMARY] Định nghĩa
> 
> **pgvector** là một extension mã nguồn mở biến PostgreSQL thành một **Vector Database**.
> 
> Nó cho phép bạn lưu trữ các **Vector Embeddings** (mảng số thực nhiều chiều) ngay trong bảng dữ liệu thông thường, và thực hiện các phép toán tìm kiếm tương đồng (**Similarity Search**) bằng SQL.

### Vector Embedding là gì?

Trong AI, mọi dữ liệu (văn bản, hình ảnh, giọng nói, hành vi gian lận) đều được chuyển đổi thành một mảng số (Vector). Các dữ liệu có ý nghĩa giống nhau sẽ nằm gần nhau trong không gian vector.

- **Ví dụ Banking:**
    
    - Giao dịch bình thường: `[0.1, 0.5, 0.9]`
        
    - Giao dịch mua cà phê: `[0.1, 0.55, 0.85]` (Gần vector trên -> Normal)
        
    - Giao dịch lừa đảo (Hack): `[0.9, -0.1, 0.2]` (Xa vector trên -> Anomalous)
        

---

## 2. Các loại Index trong pgvector

Để tìm kiếm trong hàng triệu vector, pgvector cung cấp 2 loại index chính. Đây là câu hỏi phỏng vấn "must-know".

### A. IVFFlat (Inverted File with Flat Compression)

- **Cơ chế:** Chia không gian vector thành các cụm (Clusters/Lists). Khi tìm kiếm, chỉ tìm trong cụm gần nhất và vài cụm lân cận.
    
- **Ưu điểm:** Build index rất nhanh, tốn ít RAM.
    
- **Nhược điểm:**
    
    - Độ chính xác (Recall) giảm nếu chọn sai tham số.
        
    - **Quan trọng:** Phải có dữ liệu trước rồi mới xây Index thì mới tối ưu (vì nó cần học cách phân cụm data).
        

### B. HNSW (Hierarchical Navigable Small World) - _Khuyên dùng cho Bank_

- **Cơ chế:** Xây dựng một đồ thị nhiều tầng (Graph-based).
    
    - Tầng trên cùng: Các điểm mốc lớn (như đi máy bay giữa các thành phố).
        
    - Tầng dưới: Chi tiết cụ thể (như đi xe máy trong ngõ hẻm).
        
- **Ưu điểm:**
    
    - Tốc độ truy vấn **cực nhanh** (High Performance).
        
    - Độ chính xác (Recall) rất cao.
        
    - Chịu được việc Insert/Update dữ liệu liên tục mà không bị suy giảm hiệu năng nhiều như IVFFlat.
        
- **Nhược điểm:** Tốn RAM nhiều hơn để lưu cấu trúc đồ thị.
    

|**Đặc điểm**|**IVFFlat**|**HNSW**|
|---|---|---|
|**Speed**|Trung bình|🚀 Rất nhanh|
|**Recall**|Tùy chỉnh (Good)|⭐ Excellent|
|**Build Time**|Nhanh|Chậm hơn|
|**Memory**|Thấp|Cao|
|**Use Case**|Data tĩnh, ít RAM|**Real-time Fraud Detection**, Chatbot AI|

---

## 3. Demo: Fraud Detection với pgvector & HNSW

Kịch bản: Hệ thống cần chặn giao dịch lừa đảo trong thời gian thực (< 100ms).

### Bước 1: Cài đặt & Tạo bảng

SQL

```sql
-- 1. Enable Extension
CREATE EXTENSION vector;

-- 2. Tạo bảng Transactions với cột vector (ví dụ 3 chiều cho đơn giản)
CREATE TABLE transaction_vectors (
    transaction_id bigint PRIMARY KEY,
    description text,
    embedding vector(3) -- Vector đặc trưng của giao dịch (được tạo bởi AI Model)
);

-- 3. Insert dữ liệu mẫu (đã được AI convert thành vector)
INSERT INTO transaction_vectors (transaction_id, description, embedding) VALUES
(1, 'Mua hàng Shopee', '[0.1, 0.2, 0.3]'),
(2, 'Chuyển tiền nước', '[0.1, 0.21, 0.31]'), -- Gần giống Shopee
(3, 'Rút tiền lạ ở Campuchia', '[0.9, 0.9, 0.9]'); -- Khác biệt hoàn toàn
```

### Bước 2: Tạo HNSW Index

SQL

```sql
-- Tạo index HNSW dùng khoảng cách L2 (Euclidean)
-- m: Số lượng kết nối tối đa mỗi node (càng cao càng chính xác nhưng tốn RAM)
-- ef_construction: Độ sâu khi xây index
CREATE INDEX idx_fraud_check ON transaction_vectors
USING hnsw (embedding vector_l2_ops)
WITH (m = 16, ef_construction = 64);
```

### Bước 3: Truy vấn (Detect Fraud)

Khi có một giao dịch mới `[0.85, 0.91, 0.88]` (nghi vấn), ta tìm xem trong quá khứ có giao dịch lừa đảo nào "gần giống" nó không.

SQL

```sql
-- Tìm 5 giao dịch gần giống nhất với giao dịch mới
SELECT transaction_id, description,
       (embedding <-> '[0.85, 0.91, 0.88]') AS distance
FROM transaction_vectors
ORDER BY embedding <-> '[0.85, 0.91, 0.88]'
LIMIT 5;

-- Kết quả sẽ trả về giao dịch số 3 (Rút tiền lạ) vì khoảng cách (distance) rất nhỏ.
-- -> HỆ THỐNG CẢNH BÁO FRAUD!
```

---

## 4. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Tại sao không dùng Pinecone/Milvus (Vector DB chuyên dụng) mà dùng pgvector?
> 
> **A:**
> 
> 1. **Single Source of Truth:** Không muốn dữ liệu bị phân mảnh (User ID ở Postgres, Vector ở Pinecone). Việc đồng bộ dữ liệu giữa 2 DB rất dễ lỗi (Consistency issue).
>     
> 2. **ACID:** Bank cần ACID. pgvector thừa hưởng ACID của Postgres. Transaction thêm vector mới nếu lỗi là Rollback ngay.
>     
> 3. **Joins:** Có thể join ngay kết quả tìm kiếm Vector với bảng `users`, `accounts` trong 1 câu SQL duy nhất. Tiện lợi vô cùng.
>     

> [!QUESTION] Q: Khi nào nên dùng khoảng cách Cosine (`<=>`) thay vì L2 (`<->`)?
> 
> **A:**
> 
> - **L2 (Euclidean):** Khi độ lớn (magnitude) của vector quan trọng.
>     
> - **Cosine:** Khi chỉ quan tâm đến **góc** (hướng) của vector, không quan tâm độ lớn. Thường dùng trong **NLP (Xử lý ngôn ngữ tự nhiên)**, so sánh độ tương đồng văn bản. Ví dụ: Văn bản dài và văn bản ngắn nhưng cùng chủ đề thì Cosine giống nhau.
>     

> [!QUESTION] Q: Giới hạn số chiều (Dimensions) của pgvector là bao nhiêu?
> 
> **A:** Mặc định là 2000 chiều (quá đủ cho OpenAI Embeddings - 1536 chiều). Có thể config lên 16000 chiều nếu cần (nhưng tốn RAM kinh khủng).