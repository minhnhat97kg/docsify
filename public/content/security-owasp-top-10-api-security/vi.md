---
title: "Security - OWASP Top 10 API Security"
tags:
  - "security"
  - "owasp"
  - "api"
  - "backend"
  - "interview"
  - "banking"
  - "golang"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Trước đây, ta hay nghe đến OWASP Top 10 Web (SQL Injection, XSS...)."
---

## 1. Tổng quan: Web vs. API Security

Trước đây, ta hay nghe đến **OWASP Top 10 Web** (SQL Injection, XSS...).

Tuy nhiên, API hiện đại (REST/GraphQL) có đặc thù riêng. SQL Injection giờ ít gặp (nhờ ORM), thay vào đó là các lỗi về **Logic và Phân quyền**.

Vì vậy, OWASP ra mắt bộ tiêu chuẩn riêng: **OWASP API Security Top 10 (Phiên bản mới nhất 2023)**.

> [!WARNING] Banking Context
> 
> Với Ngân hàng, 3 lỗi nguy hiểm nhất là **BOLA (API1)**, **Broken Authentication (API2)** và **BOPLA (API3)**. Đây là những lỗi khiến tiền "bay" khỏi tài khoản nhanh nhất.

---

## 2. API1:2023 - Broken Object Level Authorization (BOLA)

Tên cũ là **IDOR (Insecure Direct Object Reference)**. Đây là "Vua của các lỗ hổng API".

> [!SUMMARY] Kịch bản tấn công
> 
> - **Hợp lệ:** User A (ID: 100) gọi API xem số dư: `GET /api/accounts/100/balance`.
>     
> - **Tấn công:** User A sửa URL thành ID của User B: `GET /api/accounts/101/balance`.
>     
> - **Lỗi:** Server trả về số dư của User B mà không kiểm tra xem A có quyền sở hữu tài khoản 101 hay không.
>     

### Cách phòng chống (Golang Middleware)

**Sai (Chỉ check đăng nhập):**

Go

```
func GetBalance(c *gin.Context) {
    accID := c.Param("id")
    // Sai: Cứ thế query DB mà không so sánh với User đang login
    balance := db.FindAccount(accID) 
    c.JSON(200, balance)
}
```

**Đúng (Check quyền sở hữu):**

Go

```
func GetBalance(c *gin.Context) {
    // 1. Lấy UserID từ Token (đã verify ở middleware trước)
    currentUserID := c.MustGet("userID").(string)
    
    accID := c.Param("id")
    
    // 2. Query DB: Phải có điều kiện user_id
    var account Account
    if err := db.Where("id = ? AND owner_id = ?", accID, currentUserID).First(&account).Error; err != nil {
        c.AbortWithStatus(403) // Forbidden
        return
    }
    
    c.JSON(200, account)
}
```

---

## 3. API2:2023 - Broken Authentication (Xác thực gãy)

Không phải là chưa login, mà là cơ chế login/token quá yếu.

- **Vấn đề:**
    
    - Cho phép mật khẩu yếu ("123456").
        
    - Token JWT không hết hạn (No Expiry) hoặc Signing Key quá dễ đoán.
        
    - Không có Rate Limit trên API Login (Brute Force).
        
    - Gửi Token qua URL (`/api?token=abc`) thay vì Header (lộ trong log server).
        

---

## 4. API3:2023 - Broken Object Property Level Authorization (BOPLA)

Đây là sự kết hợp của 2 lỗi cũ (2019): **Excessive Data Exposure** (Lộ data thừa) và **Mass Assignment** (Gán data bừa bãi).

### A. Lộ Data thừa (Excessive Data Exposure)

- **Kịch bản:** App chỉ cần hiển thị "Tên User".
    
- **Lỗi:** API backend lười biếng, trả về `SELECT * FROM users`. JSON trả về chứa cả `password_hash`, `cccd_number`, `balance`.
    
- **Hacker:** Sniff traffic và thấy hết thông tin nhạy cảm.
    

### B. Gán Data bừa bãi (Mass Assignment)

- **Kịch bản:** API Update Profile nhận JSON body và map thẳng vào Object User.
    
- **Tấn công:** Hacker gửi thêm field: `{"role": "ADMIN", "balance": 999999999}`.
    
- **Lỗi:** Backend (đặc biệt là Node.js/Go GORM) tự động update luôn cột `role` và `balance` vào DB.
    

**Giải pháp (DTO Pattern):**

Luôn định nghĩa struct riêng cho Request/Response. Không dùng struct DB (Model) để nhận/trả dữ liệu.

Go

```
// Struct dùng cho DB (Có chứa field nhạy cảm)
type User struct {
    ID       uint
    Username string
    Password string // Nhạy cảm
    Role     string // Nhạy cảm
}

// Struct dùng cho API Request (Chỉ cho sửa những cái này)
type UpdateUserRequest struct {
    Username string `json:"username"`
    // Không có field Role ở đây -> Hacker gửi lên cũng bị bỏ qua
}
```

---

## 5. API4:2023 - Unrestricted Resource Consumption (Rate Limit)

Nếu không giới hạn tài nguyên, API sẽ bị DoS (Denial of Service) hoặc tốn tiền Cloud vô ích.

- Không Rate Limit số request.
    
- Không giới hạn kích thước file upload.
    
- Không phân trang (Pagination) chặt chẽ (User request `page_size=1,000,000` -> Sập DB).
    

-> **Giải pháp:** Xem lại bài [[Rate Limiting]].

---

## 6. API6:2023 - Unrestricted Access to Sensitive Business Flows

Lỗi này liên quan đến **nghiệp vụ** hơn là kỹ thuật.

Hacker không hack server, mà lạm dụng tính năng.

- **Ví dụ:** API "Mua vé máy bay".
    
- **Tấn công:** Hacker viết script tự động giữ chỗ (Booking) nhưng không thanh toán. Làm hãng bay hết vé ảo, không bán được cho khách thật.
    
- **Ví dụ:** API "Đăng bài". Hacker spam bài rác quảng cáo.
    

**Giải pháp:** Captcha, Fingerprinting thiết bị, Phân tích hành vi (Behavior Analysis).

---

## 7. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Làm sao ngăn chặn Mass Assignment trong GORM?
> 
> **A:**
> 
> 1. Sử dụng `Select` hoặc `Omit` khi update:
>     
>     `db.Model(&user).Select("Name", "Age").Updates(input)` (Chỉ cho phép sửa Name, Age).
>     
> 2. Tốt nhất: Sử dụng struct DTO riêng biệt, copy dữ liệu từ DTO sang Model thủ công, không bao giờ `BindJSON` thẳng vào Model.
>     

> [!QUESTION] Q: Sự khác biệt giữa BOLA (API1) và BOPLA (API3)?
> 
> **A:**
> 
> - **BOLA (Level Object):** Hacker truy cập vào **Object ID** mà nó không được phép (Xem tài khoản của người khác). -> _Sai chủ sở hữu._
>     
> - **BOPLA (Level Property):** Hacker truy cập vào **Thuộc tính** mà nó không được phép (trong chính object của nó hoặc người khác). Ví dụ: User thường nhưng xem được thuộc tính `is_admin` hoặc sửa được `balance`. -> _Sai quyền hạn trên trường dữ liệu._
>     

> [!QUESTION] Q: JWT token bị lộ thì làm sao thu hồi (Revoke)?
> 
> **A:** JWT là Stateless, cấp rồi không thu lại được.
> 
> Giải pháp:
> 
> 1. **Blacklist:** Lưu token bị lộ vào Redis (Blacklist) với TTL bằng thời gian hết hạn của nó. Middleware check Redis trước khi cho qua.
>     
> 2. **Short-lived Access Token:** Để Access Token chỉ sống 5-15 phút. Dùng Refresh Token (có lưu trong DB) để cấp mới. Khi cần revoke, xóa Refresh Token trong DB -> Hacker chỉ dùng được Access Token thêm vài phút là hết.
>