---
title: "Security - OAuth 2.0 & OIDC"
tags:
  - "security"
  - "oauth2"
  - "oidc"
  - "authentication"
  - "authorization"
  - "jwt"
  - "interview"
  - "banking"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Rất nhiều người nhầm lẫn hai khái niệm này."
---

## 1. Phân biệt AuthN vs. AuthZ (Mental Model)

Rất nhiều người nhầm lẫn hai khái niệm này.

- **OAuth 2.0 (Open Authorization):** Giao thức **Ủy quyền** (Authorization).
    - _Ví dụ:_ Bạn đưa chìa khóa xe cho nhân viên Valet parking. Anh ta có quyền _lái xe_ của bạn, nhưng không có quyền _mở cốp xe_ hay _bán xe_. Anh ta giữ cái "Token" (chìa khóa Valet) chứ không phải chìa khóa gốc.
        
- **OIDC (OpenID Connect):** Giao thức **Định danh** (Authentication) xây dựng trên nền tảng OAuth 2.0.
    - _Ví dụ:_ Nhân viên an ninh kiểm tra thẻ ID của bạn để biết _bạn là ai_ (Tên, tuổi, ảnh đại diện).
        

> [!SUMMARY] Tóm lại
> 
> - **OAuth 2.0:** Để API biết "Thằng này được phép làm gì?" (Access Token).
>     
> - **OIDC:** Để App biết "Thằng đang login là ai?" (ID Token).
>     

---

## 2. Các vai diễn (Roles)
1. **Resource Owner:** Chính là **User** (Khách hàng).
2. **Client:** Ứng dụng (**App Mobile/Web**) muốn truy cập dữ liệu.
3. **Authorization Server (IdP):** Hệ thống quản lý User (Ví dụ: **Auth0, Keycloak, Google, IdentityServer**). Nơi user nhập password.
4. **Resource Server:** **Backend API** (Nơi chứa dữ liệu tài khoản, tiền nong).

---
## 3. Authorization Code Flow with PKCE (Chuẩn Vàng)

Ngày xưa dùng _Implicit Flow_ (trả token trực tiếp trên URL) -> **Đã bị khai tử** vì kém bảo mật.

Ngày nay, chuẩn bắt buộc cho Mobile App và SPA (React/Vue) là **Authorization Code Flow with PKCE** (Proof Key for Code Exchange).

**Luồng đi chi tiết:**

1. **User bấm Login:**
    - App tạo ra một chuỗi ngẫu nhiên gọi là `code_verifier`.
    - App băm chuỗi đó tạo ra `code_challenge`.
    - App chuyển hướng User sang trang Login của IdP kèm theo `code_challenge`.    
2. **User đăng nhập:** Tại trang của IdP (App không hề biết password).
3. **IdP trả về Authorization Code:**
    - Nếu đăng nhập đúng, IdP redirect user về App kèm theo một mã `code` (dùng 1 lần).    
4. **Trao đổi Token (Exchange):**
    - App gửi `code` + `code_verifier` (chuỗi gốc ban đầu) lên IdP.    
5. **Verify & Issue Token:**
    - IdP kiểm tra: Băm `code_verifier` xem có khớp với `code_challenge` lúc đầu không? (Để đảm bảo thằng gửi code chính là thằng đã request login, chống tấn công chặn giữa).
    - Nếu khớp -> Trả về **Access Token** + **ID Token** + **Refresh Token**.

---
## 4. Client Credentials Flow (Machine-to-Machine)

Dùng cho các Service nội bộ nói chuyện với nhau (VD: Service "Tính lãi" gọi Service "Tài khoản"). Không có User tương tác.

1. Service A gửi `Client ID` + `Client Secret` lên IdP.
2. IdP trả về `Access Token`.
3. Service A dùng Token đó gọi Service B.

---
## 5. Token Anatomy: Access vs. ID Token

Cả hai thường là **JWT (JSON Web Token)**, nhưng mục đích khác nhau hoàn toàn.
### A. ID Token (OIDC - Cho Frontend dùng)
Chứa thông tin User để hiển thị lên màn hình. **KHÔNG** dùng để gọi API.

``` json
{
  "iss": "https://my-bank.auth0.com/",
  "sub": "user_123", // User ID
  "name": "Nguyen Van A",
  "email": "a@bank.com",
  "picture": "https://avatar..."
}
```

### B. Access Token (OAuth 2.0 - Cho Backend dùng)
Chứa quyền hạn (Scopes). Backend chỉ tin tưởng cái này.

``` json
{
  "iss": "https://my-bank.auth0.com/",
  "sub": "user_123",
  "aud": "https://api.mybank.com", // Dành cho API nào?
  "scope": "read:accounts write:transfer", // Được làm gì?
  "exp": 1735689600 // Hết hạn lúc nào?
}
```

---
## 6. Refresh Token Rotation (Bảo mật nâng cao)
`Access Token` thường chỉ sống ngắn (5-15 phút) để nếu bị hack thì hacker cũng chỉ dùng được một lúc.
Khi hết hạn, App dùng `Refresh Token` (sống dài: 30 ngày) để xin Access Token mới mà không bắt User login lại.

> [!DANGER] Rủi ro
> 
> Nếu Hacker lấy được Refresh Token -> Hắn có thể xin Access Token mãi mãi.

**Giải pháp: Rotation (Xoay vòng)**

- Mỗi khi dùng Refresh Token cũ để xin mới -> IdP sẽ **HỦY** Refresh Token cũ và cấp cho một cái Refresh Token hoàn toàn mới.
- Nếu Hacker lấy trộm Refresh Token cũ và mang đi xài -> IdP phát hiện Token này đã bị dùng rồi -> **HỦY TOÀN BỘ** session của User đó ngay lập tức (Hệ thống phát hiện xâm nhập).

---

## 7. FAPI - Financial-grade API (Chuẩn Ngân hàng)

Trong Banking, OAuth 2.0 thường là chưa đủ. Các ngân hàng áp dụng chuẩn **FAPI** (Profile bảo mật cao cấp của OAuth).

- **mTLS (Mutual TLS):** Không chỉ Server có chứng chỉ, mà Client (App) cũng phải có chứng chỉ Client Certificate để xác thực 2 chiều.
- **Sender Constrained Tokens (DPoP):** Access Token được gắn chặt với Private Key của thiết bị. Nếu Hacker trộm được Token mang sang máy khác dùng -> Vô hiệu (Vì không có Private Key khớp).
    

---

## 8. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Tại sao không lưu Token trong LocalStorage?
> 
> **A:**
> 
> LocalStorage dễ bị tấn công bởi **XSS**. Nếu trang web dính mã độc JS, hacker đọc được LocalStorage -> Mất Token.
> 
> _Best Practice:_ Lưu Token trong **Cookie HttpOnly** (JS không đọc được) với flag `Secure` và `SameSite=Strict`.

> [!QUESTION] Q: Có Access Token rồi thì Backend xác thực kiểu gì?
> 
> **A:** Backend không gọi lên IdP mỗi lần (chậm). Backend lưu Public Key của IdP.
> 
> Khi nhận JWT, Backend dùng Public Key để verify chữ ký (Signature) của JWT. Nếu chữ ký đúng và hạn dùng (exp) còn hiệu lực -> Tin tưởng thông tin trong đó. Đây là xác thực **Stateless**.

> [!QUESTION] Q: Scopes là gì?
> 
> **A:** Là phạm vi quyền hạn. Ví dụ: `read:balance` (chỉ xem số dư), `write:transfer` (được chuyển tiền).
> 
> Nếu Access Token chỉ có scope `read`, mà user cố tình gọi API chuyển tiền -> Backend chặn lại (403 Forbidden).

Chúng ta đã đi qua lớp bảo mật mạng (mTLS) và kiến trúc tổng thể (Zero Trust). Bây giờ, hãy bước lên tầng ứng dụng để giải quyết bài toán: **Làm sao để một ứng dụng tin tưởng một ứng dụng khác thay mặt người dùng?** Chào mừng bạn đến với thế giới của **"Chìa khóa vạn năng"**.

---

---

## 1. Bản chất: Valet Key vs. Passport

Về mặt chuyên môn:

- **OAuth 2.0:** Là một **Authorization Framework** (khung ủy quyền). Nó cho phép một ứng dụng bên thứ ba truy cập vào tài nguyên của người dùng mà không cần biết mật khẩu.
    
- **OIDC:** Là một lớp **Authentication** (xác thực) xây dựng trên nền OAuth 2.0 để định danh người dùng.
    
- **SAML 2.0:** Là một tiêu chuẩn dựa trên **XML** để trao đổi dữ liệu xác thực và ủy quyền giữa các bên (thường dùng trong doanh nghiệp).
    

> [!SUMMARY] Mental Model
> 
> **OAuth 2.0 - "Chìa khóa phụ cho thợ sửa xe" (Valet Key):** Bạn đưa chìa khóa phụ cho thợ. Chìa này mở được cửa để họ đánh xe vào xưởng nhưng **không** mở được cốp xe hay ngăn chứa đồ riêng tư. Thợ xe không cần biết mật khẩu nhà bạn.
> 
> **OIDC - "Thẻ căn cước đính kèm chìa khóa":** Ngoài việc cho phép thợ sửa xe lái xe (OAuth2), bạn đưa thêm một tấm thẻ ghi rõ: "Tôi là chủ xe, tên là A". Thợ xe biết chắc chắn họ đang phục vụ ai.
> 
> **SAML - "Hộ chiếu ngoại giao":** Một cuốn sổ dày cộp, trang trọng, bằng giấy (XML). Nó chứa mọi thông tin về bạn và được đóng dấu bởi các đại sứ quán (Identity Provider). Nó hơi cồng kềnh nhưng các tổ chức lớn (Chính phủ, Bank) cực kỳ tin tưởng nó.
> 
> **Khác biệt lớn nhất:** OAuth2 để **Làm (Authorize)**, OIDC để **Biết (Authenticate)**, và SAML làm **Cả hai** nhưng theo cách truyền thống của Enterprise.

---

## 2. Giải phẫu & Flow Diagrams

### A. OAuth 2.0 (Authorization Code Flow)

Đây là luồng an toàn nhất hiện nay, thường dùng cho Web/Mobile app.

Plaintext

```
1. User -> Click "Login with Google"
2. App -> Redirect tới Google (Client ID, Scopes)
3. User -> Login & Duyệt quyền tại Google
4. Google -> Redirect về App kèm "Authorization Code"
5. App -> Gửi Code + Client Secret tới Google
6. Google -> Trả về Access Token
7. App -> Dùng Access Token để lấy dữ liệu (Ảnh, Email...)
```

### B. OpenID Connect (OIDC)

OIDC = OAuth 2.0 + **ID Token** (Dạng JWT).

Go

```
// Cấu trúc của ID Token (JWT Payload) nhận được từ OIDC
{
  "iss": "https://accounts.google.com",
  "sub": "1234567890", // Định danh duy nhất của User
  "aud": "my-client-app-id",
  "exp": 1672531200,
  "email": "dev.nathan@gmail.com",
  "name": "Nathan Thợ Gõ"
}
```

### C. SAML 2.0 (SSO Flow)

Dùng XML Assertions. Rất phổ biến trong môi trường tích hợp như AD FS, Okta cho các ứng dụng nội bộ doanh nghiệp.

XML

```
<saml:Assertion>
  <saml:Issuer>https://idp.example.com</saml:Issuer>
  <saml:Subject>
    <saml:NameID>nathan@company.com</saml:NameID>
  </saml:Subject>
  <saml:AttributeStatement>
    <saml:Attribute Name="Role"><saml:AttributeValue>Manager</saml:AttributeValue></saml:Attribute>
  </saml:AttributeStatement>
</saml:Assertion>
```

---

## 3. So sánh đánh đổi

|**Đặc điểm**|**OAuth 2.0**|**OIDC**|**SAML 2.0**|
|---|---|---|---|
|**Mục đích chính**|Ủy quyền (Authorization)|Xác thực (Authentication)|Cả hai (SSO Enterprise)|
|**Định dạng dữ liệu**|JSON / Key-Value|JWT (JSON)|XML|
|**Độ thân thiện**|Rất cao (Web/Mobile)|Rất cao (Modern Apps)|Thấp (Phức tạp, cồng kềnh)|
|**Bảo mật**|Tốt (Cần PKCE)|Rất tốt|Rất tốt (Ký số XML mạnh)|
|**Use Case**|Gọi API bên thứ 3|Login cho Web/App hiện đại|SSO cho công ty lớn, App cũ|

---

## 4. Vấn đề nhức nhối & Giải pháp

### Vấn đề 1: Authorization Code Interception

Hacker có thể đánh cắp "Code" ở bước 4 để đổi lấy Token.

- **Giải pháp: PKCE (Proof Key for Code Exchange).** Client tạo một bí mật tạm thời (Code Verifier) và gửi bản hash của nó (Code Challenge) đi. Chỉ Client thực sự mới có "chìa khóa" để giải mã bước cuối. **Bắt buộc cho Mobile/SPA.**
    

### Vấn đề 2: XML Signature Wrapping (SAML)

Hacker sửa nội dung XML nhưng giữ nguyên phần chữ ký số, đánh lừa logic kiểm tra của ứng dụng.

- **Giải pháp:** Sử dụng các thư viện SAML chuẩn, được update thường xuyên và luôn validate cấu trúc XML (Schema) trước khi verify chữ ký.
    

---

## 5. Security Checklist

1. **Sử dụng HTTPS:** Tuyệt đối không chạy OAuth2/SAML qua HTTP. Token sẽ bị lộ ngay lập tức.
    
2. **Strict Redirect URI:** Chỉ cho phép redirect về các domain đã được khai báo chính xác (Whitelisting). Tránh tấn công Redirect.
    
3. **Short-lived Access Tokens:** Access token chỉ nên sống vài phút. Dùng Refresh Token để lấy token mới.
    
4. **Scoping:** Chỉ xin những quyền tối thiểu (ví dụ: `read:profile`, đừng xin `write:all`).
    
5. **State Parameter:** Luôn dùng tham số `state` để chống tấn công CSRF trong luồng OAuth2.
    

---

## 6. Góc phỏng vấn thực chiến

> [!QUESTION] Q1: Tại sao không dùng Access Token để xác thực người dùng?
> 
> **A:** Vì Access Token là "Valet Key". Nó chứng minh bạn có quyền truy cập tài nguyên, nhưng nó không cho biết bạn là ai. Nếu dùng nó để login, bạn sẽ dính lỗi "Confused Deputy". OIDC ra đời với ID Token để giải quyết đúng việc này.

> [!QUESTION] Q2: Khi nào thì dùng SAML thay vì OIDC?
> 
> **A:** Khi bạn làm việc với các hệ thống Enterprise cũ (Legacy) hoặc các tổ chức chính phủ/ngân hàng đã chuẩn hóa hạ tầng dựa trên XML và Active Directory. Nếu xây dựng App mới hoàn toàn, OIDC luôn là lựa chọn hàng đầu.

> [!QUESTION] Q3: PKCE hoạt động như thế nào và tại sao nó quan trọng cho Single Page Apps (SPA)?
> 
> **A:** Trong SPA, Client Secret không thể được giữ bí mật (vì code JS nằm ở browser). PKCE thay thế Client Secret bằng một cơ chế "bí mật động" được tạo ra cho mỗi request, giúp ngăn chặn việc đánh cắp Authorization Code.

**Bạn có muốn mình hướng dẫn cách tích hợp thực tế Social Login (Google/GitHub) vào một dự án Go hoặc Node.js bằng thư viện chuẩn không?**