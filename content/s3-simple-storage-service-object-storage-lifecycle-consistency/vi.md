---
title: "S3 - Object Storage, Lifecycle & Consistency"
tags:
  - "aws"
  - "s3"
  - "storage"
  - "cost-optimization"
  - "system-design"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "- AWS S3 Storage Classes"
---

- [AWS S3 Storage Classes](https://aws.amazon.com/s3/storage-classes/)

## 1. Bản chất: Object Storage vs. Block Storage

Đừng nhầm lẫn **S3** với **EBS (Elastic Block Store)** gắn vào EC2.

- **EBS (Block Storage):** Giống ổ cứng (`C:`, `/dev/sda1`). Cài hệ điều hành, sửa từng byte của file được. Chỉ gắn được vào 1 EC2 tại 1 thời điểm.
    
- **S3 (Object Storage):** Giống một cái kho khổng lồ.
    
    - Lưu trữ theo dạng **Key-Value**. (Key: `images/logo.png`, Value: Dữ liệu ảnh).
        
    - **Immutable (Bất biến):** Muốn sửa file? Phải upload đè file mới lên. Không thể mở file ra sửa 1 dòng rồi lưu lại.
        
    - **Web-scale:** Truy cập qua HTTP API. Dung lượng vô hạn.
        

---

## 2. Storage Classes (Chiến thuật tối ưu chi phí)

S3 không chỉ có một mức giá. Chọn sai class có thể làm hóa đơn AWS tăng gấp đôi.

### A. S3 Standard (Mặc định)

- **Đặc điểm:** Truy cập tức thì (mili-giây).
    
- **Giá:** Đắt nhất.
    
- **Use Case:** Dữ liệu nóng (Hot Data), file ảnh profile, static assets cho web.
    

### B. S3 Intelligent-Tiering (Thông minh - Khuyên dùng)

- **Cơ chế:** AWS tự theo dõi.
    
    - File nào 30 ngày không ai sờ tới -> Tự chuyển sang lớp rẻ hơn (Infrequent Access).
        
    - File nào đang ở lớp rẻ mà có người truy cập -> Tự chuyển về lớp Standard.
        
- **Use Case:** Dữ liệu mà bạn **không đoán được** tần suất truy cập.
    

### C. S3 Standard-IA (Infrequent Access)

- **Đặc điểm:** Phí lưu trữ **rẻ hơn 50%** so với Standard. NHƯNG bị tính phí khi **đọc** file (Retrieval Fee).
    
- **Use Case:** File backup tháng, file log cũ. Cần là lấy được ngay, nhưng ít khi cần.
    

### D. S3 Glacier (Kho lạnh)

- **Đặc điểm:** Cực rẻ (bằng 1/10 Standard).
    
- **Nhược điểm:** **Không thể lấy ngay.** Muốn đọc file phải gửi lệnh "Restore" và chờ từ **1 phút đến 12 tiếng** (tùy gói).
    
- **Use Case:** Lưu trữ dài hạn để tuân thủ luật pháp (Lưu hợp đồng 10 năm), phim gốc chất lượng cao ít xem.
    

---

## 3. Lifecycle Policies (Tự động dọn rác)

Đừng bao giờ xóa file bằng tay. Hãy dùng **Lifecycle Rule**.

> [!SUMMARY] Kịch bản điển hình (Log Rotate)
> 
> 1. **Day 0:** Upload log lên `Standard`.
>     
> 2. **Day 30:** Chuyển sang `Standard-IA` (vì ít đọc dần).
>     
> 3. **Day 90:** Chuyển sang `Glacier Deep Archive` (Lưu kho cho rẻ).
>     
> 4. **Day 365:** `Expire` (Xóa vĩnh viễn).
>     

---

## 4. S3 Strong Consistency (Cập nhật quan trọng 2020)

Trước đây S3 là **Eventual Consistency** (Ghi xong đọc ngay có thể chưa thấy).

**Hiện tại S3 là Strong Consistency.**

- **Write-after-Write:** Bạn upload đè file `report.pdf`. Ngay lập tức sau đó bạn gọi API `GET report.pdf` -> AWS cam kết trả về file **mới nhất**.
    
- **List:** Bạn upload file mới, gọi lệnh `ListObjects` -> Cam kết thấy file đó ngay lập tức.
    
- -> **Lợi ích:** Giúp backend logic đơn giản hơn rất nhiều (không cần sleep/retry).
    

---

## 5. Design Pattern: Presigned URLs (Upload trực tiếp)

**Vấn đề:** Client muốn upload file video 1GB.

- **Cách Sai:** Client -> Upload lên Backend Server -> Backend đẩy lên S3.
    
    - _Hậu quả:_ Server bị nghẽn RAM/Bandwidth. Server thành điểm thắt cổ chai.
        

**Giải pháp: Presigned URLs**

1. **Client:** Gọi `GET /api/upload-ticket`.
    
2. **Backend:** Dùng AWS SDK tạo một **Presigned URL** (có hạn 5 phút) rồi trả về cho Client.
    
3. **Client:** Dùng URL đó để `PUT` file trực tiếp lên S3.
    
    - Backend không hề chạm vào file.
        
    - Bảo mật tuyệt đối (chỉ upload được đúng file đó, vào đúng bucket đó).
        

---

## 6. Infrastructure as Code (Terraform)

Terraform

```
resource "aws_s3_bucket" "logs" {
  bucket = "my-app-logs-prod"
}

# Bật Versioning (Chống xóa nhầm)
resource "aws_s3_bucket_versioning" "versioning" {
  bucket = aws_s3_bucket.logs.id
  versioning_configuration { status = "Enabled" }
}

# Cấu hình Lifecycle
resource "aws_s3_bucket_lifecycle_configuration" "lifecycle" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "log-retention"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
    expiration {
      days = 365
    }
  }
}
```

---

## 7. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Làm sao để host một trang web tĩnh (Static Web: React/Vue) rẻ nhất và chịu tải cao nhất?
> 
> **A:**
> 
> Dùng **S3 Static Website Hosting** kết hợp với **CloudFront (CDN)**.
> 
> - S3 chứa file HTML/JS/CSS.
>     
> - CloudFront cache nội dung và phân phối toàn cầu.
>     
> - Chi phí cực rẻ so với thuê EC2 chạy Nginx.
>     

> [!QUESTION] Q: Multipart Upload là gì? Khi nào dùng?
> 
> **A:**
> 
> Khi upload file lớn (**> 100MB**).
> 
> Cơ chế: Chia file thành nhiều phần nhỏ (Parts) và upload song song.
> 
> - Lợi ích: Nhanh hơn (tận dụng băng thông). Nếu rớt mạng, chỉ cần upload lại phần bị lỗi, không cần upload lại từ đầu.
>     

> [!QUESTION] Q: S3 Versioning giúp gì khi bị Hacker tấn công xóa dữ liệu (Ransomware)?
> 
> **A:**
> 
> Khi bật Versioning, lệnh `DELETE` thực chất chỉ tạo ra một **Delete Marker** (dấu xóa). File gốc vẫn còn nằm đó (dưới dạng version cũ).
> 
> Admin có thể khôi phục lại dữ liệu bằng cách xóa cái Delete Marker đi.
> 
> _Kết hợp:_ Dùng tính năng **Object Lock (WORM - Write Once Read Many)** để khóa cứng file, không ai (kể cả root) xóa được trong thời gian quy định.

---

**Next Step:**

Bạn đã có kiến thức vững chắc về S3.

Bạn có muốn tôi tổng hợp lại một **Checklist Phỏng vấn System Design** (các bước từ làm rõ yêu cầu, vẽ kiến trúc, đến chọn database) để bạn in ra và ôn tập hàng ngày không?
