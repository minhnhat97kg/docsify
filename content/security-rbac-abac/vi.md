---
title: "Security - RBAC & ABAC"
tags:
  - "security"
  - "iam"
  - "rbac"
  - "abac"
  - "authorization"
  - "backend"
  - "architecture"
date: "2026-03-04"
author: "nathan.huynh"
summary: "---"
---

---

## 1. Bản chất: Ai được làm gì?

Trong phát triển phần mềm, xác thực (Authentication - Who are you?) chỉ là bước đầu. Bài toán khó hơn nằm ở **Phân quyền (Authorization - What can you do?)**.

Về mặt chuyên ngành, **RBAC (Role-Based Access Control)** là cơ chế kiểm soát truy cập dựa trên chức năng công việc (Roles) trong tổ chức. Trong khi đó, **ABAC (Attribute-Based Access Control)** nâng cấp lên một bậc bằng cách sử dụng các thuộc tính (Attributes) của đối tượng, tài nguyên và môi trường để đưa ra quyết định thông qua các chính sách (Policies).

> [!SUMMARY] Mental Model
> 
> **RBAC - "Tấm thẻ quyền lực":** Hãy tưởng tượng bạn làm việc trong một tòa nhà văn phòng. Bạn có tấm thẻ ghi chữ "Manager". Tấm thẻ này mặc định mở được cửa kho và phòng họp. Hệ thống chỉ check: "Thẻ này có chữ Manager không?". Nếu có -> Cho vào.
> 
> **ABAC - "Cửa thông minh AI":** Thay vì check thẻ, cái cửa này sẽ soi: "Bạn là ai? Bạn định vào làm gì? Bây giờ là mấy giờ? Bạn có đang cầm theo bình chữa cháy không?". Nếu bạn là "Manager", nhưng định vào kho lúc "2 giờ sáng" và "không có lệnh xuất kho", cửa sẽ **không mở**.
> 
> **Sự khác biệt lớn nhất:** RBAC là **tĩnh (Static)** và dựa trên danh hiệu. ABAC là **động (Dynamic)** và dựa trên ngữ cảnh (Context-aware).

---

## 2. Giải phẫu (Anatomy/Architecture)

### A. RBAC (Role-Based)

Cấu trúc cực kỳ đơn giản: **User -> Roles -> Permissions**.

Go

``` go
// Minh họa cấu trúc RBAC đơn giản trong Go
type Permission string

const (
    ReadPost   Permission = "read:post"
    WritePost  Permission = "write:post"
    DeletePost Permission = "delete:post"
)

type Role struct {
    Name        string
    Permissions []Permission
}

var Roles = map[string]Role{
    "admin": {
        Name: "Admin",
        Permissions: []Permission{ReadPost, WritePost, DeletePost},
    },
    "editor": {
        Name: "Editor",
        Permissions: []Permission{ReadPost, WritePost},
    },
}
```

### B. ABAC (Attribute-Based)

Kiến trúc ABAC phức tạp hơn với các thực thể: **Subject** (Người dùng), **Action** (Hành động), **Resource** (Tài nguyên), và **Environment** (Môi trường).

JSON

``` json
// Minh họa một Policy trong hệ thống ABAC (JSON format)
{
  "target": {
    "subject": { "role": "editor", "department": "news" },
    "resource": { "type": "article", "status": "draft" },
    "action": "publish",
    "environment": { "ip_range": "10.0.0.0/8", "current_time_after": "08:00" }
  },
  "effect": "Allow",
  "condition": "subject.id == resource.author_id || subject.clearance >= 2"
}
```

---

## 3. So sánh đánh đổi: RBAC vs. ABAC

Lựa chọn công nghệ nào phụ thuộc vào quy mô và độ phức tạp của bài toán nghiệp vụ.

|**Đặc điểm**|**RBAC**|**ABAC**|
|---|---|---|
|**Độ phức tạp**|Thấp - Dễ thiết kế, dễ hiểu.|Cao - Cần tư duy logic chính sách.|
|**Khả năng mở rộng**|Kém (Dễ bị "Role Explosion").|Tốt (Thêm thuộc tính không cần thêm Role).|
|**Tính linh hoạt**|Thấp - Fix cứng theo Role.|Rất cao - Đáp ứng mọi kịch bản context.|
|**Hiệu năng**|Rất nhanh ($O(1)$ hoặc $O(N)$ nhỏ).|Chậm hơn (Phải tính toán Policy logic).|
|**Quản trị**|Dễ quản lý User Group.|Khó quản lý và Debug Policy.|
|**Phù hợp với**|Startup, Monolith, App nội bộ ít user.|Banking, Enterprise lớn, Microservices phức tạp.|

---

## 4. Vấn đề nhức nhối & Giải pháp

### Vấn đề 1: Role Explosion (Sự bùng nổ Role)

Trong RBAC, khi yêu cầu nghiệp vụ phức tạp hơn (ví dụ: Admin vùng miền, Admin phòng ban), bạn sẽ kết thúc với hàng trăm Role như `Admin_HCM_IT`, `Admin_HN_HR`...

- **Giải pháp:** Sử dụng **Hybrid RBAC + ABAC**. Dùng RBAC cho các quyền cơ bản và dùng ABAC (còn gọi là Scoped RBAC) để lọc dữ liệu theo thuộc tính (ví dụ: `Role=Admin` + `Attribute: region=HCM`).
    

### Vấn đề 2: Policy Latency (Độ trễ khi kiểm tra)

Với ABAC, việc kiểm tra hàng nghìn chính sách cho mỗi request có thể làm chậm hệ thống đáng kể.

- **Giải pháp:** 1. **Caching:** Cache kết quả phân quyền (Decision Cache) theo cặp `(User, Resource, Action)`.
    
    2. **Decoupled Architecture:** Sử dụng các engine chuyên dụng như **OPA (Open Policy Agent)** để tách biệt logic phân quyền ra khỏi code nghiệp vụ.
    

---

## 5. Security/Performance Checklist

1. **Principle of Least Privilege:** Mặc định luôn là `Deny All`. Chỉ mở những gì cần thiết.
    
2. **Audit Logging:** Luôn log lại **tại sao** một request bị từ chối (Policy nào đã chặn).
    
3. **Dry-run Mode:** Khi thay đổi Policy ABAC, hãy chạy chế độ "giả lập" để xem có vô tình chặn nhầm user không trước khi áp dụng thật.
    
4. **Avoid Deep Nesting:** Trong RBAC, tránh kế thừa Role quá 3 cấp (Role A kế thừa B, B kế thừa C...) vì sẽ rất khó debug.
    
5. **Database Indexing:** Nếu lưu ABAC attributes trong DB, hãy đảm bảo các trường thuộc tính thường xuyên check phải được đánh Index để tránh Table Scan.
    

---

## 6. Góc phỏng vấn thực chiến

> [!QUESTION] Q1: Khi nào bạn sẽ chuyển từ RBAC sang ABAC?
> 
> **A:** Khi số lượng Role bắt đầu tăng vọt không kiểm soát (Role Explosion) hoặc khi phát sinh các yêu cầu phân quyền dựa trên ngữ cảnh (Ví dụ: Chỉ cho phép truy cập từ IP công ty, hoặc chỉ được duyệt đơn hàng của chính mình trong giờ hành chính).

> [!QUESTION] Q2: Bạn đã nghe về "Zanzibar" của Google chưa? Nó giải quyết vấn đề gì?
> 
> **A:** Zanzibar là một hệ thống ReBAC (Relationship-Based Access Control). Nó giải quyết bài toán phân quyền ở quy mô cực lớn (hàng tỷ đối tượng) bằng cách coi phân quyền là một đồ thị các mối quan hệ (ví dụ: User A là _owner_ của Folder B, Folder B _contains_ File C). Nó kết hợp được ưu điểm của cả RBAC và ABAC.

> [!QUESTION] Q3: Làm sao để đảm bảo Performance khi hệ thống ABAC có hàng triệu tài nguyên?
> 
> **A:** Chúng ta không thể load triệu tài nguyên lên để check. Thay vào đó, chúng ta sử dụng kỹ thuật **Partial Evaluation**. Chuyển đổi Policy thành câu lệnh SQL (Where clause) để DB thực hiện việc lọc dữ liệu ngay từ tầng truy vấn.

> [!QUESTION] Q4: Thiết kế bảng DB cho RBAC như thế nào để tối ưu?
> 
> **A:** Cần tối thiểu 5 bảng: `Users`, `Roles`, `Permissions`, `User_Roles` (n-n), và `Role_Permissions` (n-n). Sử dụng ID dạng UUID hoặc BigInt và đảm bảo có Index trên các bảng trung gian.

**Bạn có muốn mình thử thiết kế một hệ thống phân quyền Hybrid (Kết hợp RBAC và ABAC) cho một trang thương mại điện tử đa quốc gia không?**