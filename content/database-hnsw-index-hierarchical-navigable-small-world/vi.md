---
title: "Database - HNSW Index"
tags:
  - "database"
  - "postgresql"
  - "pgvector"
  - "hnsw"
  - "ai"
  - "performance"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Trong thế giới Vector Search, chúng ta luôn phải đánh đổi giữa 3 yếu tố: Tốc độ, Độ chính xác (Recall), và Chi phí bộ nhớ."
---

## 1. Tổng quan: Tại sao HNSW là "Game Changer"?

Trong thế giới Vector Search, chúng ta luôn phải đánh đổi giữa 3 yếu tố: **Tốc độ**, **Độ chính xác** (Recall), và **Chi phí bộ nhớ**.

> [!SUMMARY] Mental Model
> 
> **HNSW (Hierarchical Navigable Small World)** giống như hệ thống giao thông phân tầng:
> 
> - **Tầng trên cùng (Cao tốc):** Các điểm mốc lớn, cách xa nhau. Giúp bạn di chuyển thật nhanh từ Bắc vào Nam.
>     
> - **Tầng giữa (Quốc lộ):** Đi chi tiết hơn vào từng tỉnh.
>     
> - **Tầng đáy (Đường làng - Layer 0):** Kết nối tất cả các điểm dữ liệu. Đây là nơi tìm ra hàng xóm chính xác nhất.
>     
> 
> _Kết quả:_ Thay vì duyệt qua hàng triệu điểm, thuật toán chỉ cần nhảy vài bước lớn ở tầng trên rồi tinh chỉnh ở tầng dưới -> Tốc độ cực nhanh (Sub-millisecond).

---

## 2. HNSW vs. IVFFlat (So sánh kỹ thuật)

Trước khi có HNSW, `IVFFlat` là lựa chọn phổ biến. Tuy nhiên, HNSW vượt trội hơn hẳn ở các bài toán Real-time.

|**Đặc điểm**|**IVFFlat (Inverted File)**|**HNSW (Graph-based)**|
|---|---|---|
|**Cấu trúc**|Chia cụm (Clustering).|Đồ thị nhiều tầng (Multi-layer Graph).|
|**Hiệu năng Query**|Tốt.|🚀 **Tuyệt vời** (State-of-the-art).|
|**Độ chính xác (Recall)**|Giảm nếu không tinh chỉnh kỹ.|Rất cao ngay cả với setting mặc định.|
|**Khả năng Update**|❌ Tệ. Cần Re-index lại khi dữ liệu thay đổi nhiều (để tính lại tâm cụm).|✅ **Tốt**. Tự động cập nhật đồ thị khi Insert/Delete.|
|**Bộ nhớ (RAM)**|Thấp.|⚠️ **Cao**. Cần lưu các kết nối (edges) của đồ thị.|
|**Lời khuyên cho Bank**|Dùng cho dữ liệu Archival, ít truy vấn.|**Dùng cho Core App** (Fraud Detection, Face ID).|

---

## 3. Cài đặt & Tinh chỉnh (Tuning Parameters)

Khi tạo Index HNSW, có 2 tham số quan trọng quyết định sự đánh đổi giữa Tốc độ Build và RAM.

### Cú pháp SQL

SQL

```sql
-- Tạo Index HNSW cho cột embedding (Vector 1536 chiều của OpenAI)
-- m: Số lượng kết nối tối đa của mỗi điểm (node).
-- ef_construction: Độ sâu tìm kiếm khi XÂY index.
CREATE INDEX idx_support_bot ON support_tickets
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

### Giải thích tham số

1. **`m` (Max Links - Mặc định 16):**
    
    - Số lượng "hàng xóm" tối đa mà một điểm kết nối tới.
        
    - _Tăng `m`:_ Tìm kiếm chính xác hơn, nhưng tốn RAM hơn và Insert chậm hơn.
        
    - _Gợi ý:_ Khoảng 16-64 là tốt cho hầu hết dataset.
        
2. **`ef_construction` (Mặc định 64):**
    
    - Khi chèn một điểm mới, thuật toán sẽ xem xét bao nhiêu ứng viên để tìm ra chỗ đặt tốt nhất.
        
    - _Tăng `ef_construction`:_ Build Index lâu hơn, nhưng chất lượng Index tốt hơn (tìm kiếm sau này nhanh hơn).
        
    - _Gợi ý:_ Nên để cao gấp đôi `m` (ví dụ: 128).
        

---

## 4. Query Tuning (Tối ưu lúc chạy)

Một tính năng "thần thánh" của HNSW là bạn có thể điều chỉnh độ chính xác **ngay trong lúc query** mà không cần Re-index.

Tham số: **`hnsw.ef_search`**

SQL

```sql
BEGIN;
-- Set cho session hiện tại.
-- Tăng số này lên -> Tìm kỹ hơn -> Chính xác hơn -> Nhưng chậm hơn.
SET LOCAL hnsw.ef_search = 100;

SELECT content FROM documents
ORDER BY embedding <=> query_vector
LIMIT 5;
COMMIT;
```

> [!TIP] Use Case thực tế
> 
> - **User thường:** Để `ef_search = 40` (Nhanh, kết quả tương đối chuẩn).
>     
> - **VIP / Admin Audit:** Để `ef_search = 200` (Chậm hơn chút, nhưng đảm bảo không bỏ sót kết quả nào quan trọng).
>     

---

## 5. Ứng dụng trong Banking (Ngoài Fraud Detection)

1. **Biometric Authentication (Face ID / Vân tay):**
    
    - Vector khuôn mặt khách hàng được lưu trong DB.
        
    - Khi khách hàng ra quầy giao dịch, Camera quét mặt -> Convert sang vector -> Query HNSW để tìm `customer_id`.
        
    - Yêu cầu độ trễ < 200ms -> HNSW là bắt buộc.
        
2. **Semantic Search cho App Ngân hàng:**
    
    - Khách hàng gõ: _"Làm sao khóa thẻ gấp?"_
        
    - Hệ thống không tìm theo từ khóa "khóa", "thẻ".
        
    - Nó convert câu hỏi thành vector -> Tìm trong Knowledge Base các bài viết có ý nghĩa tương đương (VD: "Quy trình báo mất thẻ", "Tạm ngưng dịch vụ").
        
    - HNSW giúp trả về kết quả ngay lập tức như Google.
        

---

## 6. Câu hỏi phỏng vấn nâng cao

> [!QUESTION] Q: Nhược điểm lớn nhất của HNSW là gì?
> 
> **A:** **Tiêu tốn RAM (Memory Footprint).**
> 
> Cấu trúc đồ thị yêu cầu lưu trữ rất nhiều mối liên kết (pointers) giữa các vector. Nếu dataset quá lớn (hàng tỷ vector), RAM máy chủ có thể không chứa nổi Index.
> 
> _Giải pháp:_ Nếu hết tiền mua RAM, buộc phải quay về **IVFFlat** hoặc sử dụng kỹ thuật **Quantization** (nén vector từ float32 xuống int8/binary) để giảm dung lượng (pgvector sắp hỗ trợ).

> [!QUESTION] Q: Khi nào `ef_search` không còn tác dụng?
> 
> **A:** Khi nó lớn hơn tổng số lượng dữ liệu trong dataset (lúc này nó quét hết rồi còn đâu). Hoặc khi Index bị phân mảnh quá mức do Delete/Insert liên tục mà chưa được Vacuum (dù HNSW chịu update tốt, nhưng Vacuum vẫn cần thiết để dọn rác vật lý).