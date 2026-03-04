---
title: "Security - JWT (JSON Web Tokens)"
tags:
  - "security"
  - "jwt"
  - "authentication"
  - "backend"
  - "golang"
  - "interview"
  - "banking"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Khác với Session-based truyền thống (Server phải lưu session trong RAM/Redis), JWT là Stateless. - Server tạo ra Token, ký tên vào đó, rồi ném cho Client. - Server KHÔNG LƯU gì cả. - Lần sau..."
---

## 1. Bản chất: Stateless Authentication

Khác với Session-based truyền thống (Server phải lưu session trong RAM/Redis), **JWT là Stateless**.
- Server tạo ra Token, ký tên vào đó, rồi ném cho Client.
- Server **KHÔNG LƯU** gì cả.
- Lần sau Client gửi Token lên, Server chỉ cần kiểm tra chữ ký (Signature). Nếu chữ ký đúng -> Tin tưởng dữ liệu bên trong.
    

> [!SUMMARY] Mental Model
> 
> JWT giống như tờ tiền Polymer.
> 
> Ngân hàng Nhà nước (Server) in tiền và ký bảo mật.
> 
> Người dân (Client) cầm tiền đi tiêu.
> 
> Cửa hàng (API) soi tiền giả bằng cách kiểm tra các chi tiết bảo mật, chứ không cần gọi điện về Ngân hàng Nhà nước để hỏi tờ tiền này có hợp lệ không.

---

## 2. Cấu trúc giải phẫu (Anatomy)
Một chuỗi JWT gồm 3 phần, ngăn cách bởi dấu chấm (`.`): `Header.Payload.Signature`
### A. Header (Metadata)
Cho biết loại token và thuật toán ký

``` json
{
  "alg": "HS256", // Thuật toán ký (HMAC SHA-256)
  "typ": "JWT"
}
```

### B. Payload (Claims - Dữ liệu)

Chứa thông tin về user và các quyền hạn.

> [!DANGER] Lưu ý quan trọng
> 
> Payload chỉ được **Base64Url Encoded**, **KHÔNG PHẢI MÃ HÓA (Encrypted)**.
> 
> Bất kỳ ai nhặt được token đều có thể decode ra để đọc nội dung (dùng `jwt.io`).
> 
> -> **Tuyệt đối không để Password, số dư tài khoản, hay thông tin nhạy cảm ở đây.**

Các Claims chuẩn (Standard Claims):

- `sub` (Subject): ID của user (user_id).
- `iss` (Issuer): Ai phát hành (Auth Server).
- `aud` (Audience): Dành cho ai dùng (Billing Service, App Mobile...).
- `exp` (Expiration): Thời điểm hết hạn (Unix Timestamp).
- `iat` (Issued At): Thời điểm phát hành.
- `jti` (JWT ID): ID duy nhất của token (Dùng để chống Replay Attack hoặc làm Blacklist).

### C. Signature (Chữ ký)

Đây là phần đảm bảo tính toàn vẹn.
Công thức tính:
$$Signature = HMACSHA256(base64(Header) + "." + base64(Payload), SecretKey)$$

Nếu Hacker sửa Payload (ví dụ: sửa `role: "user"` thành `role: "admin"`), khi Server tính lại Signature sẽ thấy kết quả khác với Signature đang có -> **Token không hợp lệ.**

---

## 3. Signing Algorithms: HS256 vs. RS256

Trong Banking, việc chọn thuật toán ký cực kỳ quan trọng.

|**Đặc điểm**|**HS256 (HMAC with SHA-256)**|**RS256 (RSA Signature with SHA-256)**|
|---|---|---|
|**Loại**|Symmetric (Đối xứng).|Asymmetric (Bất đối xứng).|
|**Key**|Dùng **1 Secret Key** duy nhất để vừa Ký vừa Verify.|Dùng **Private Key** để Ký, **Public Key** để Verify.|
|**Chia sẻ**|Phải share Secret Key cho tất cả Service muốn verify token.|Chỉ Auth Server giữ Private Key. Các API Service giữ Public Key (công khai).|
|**Rủi ro**|Nếu 1 Service bị hack lộ key -> Toàn hệ thống chết.|Nếu API Service bị hack -> Hacker chỉ có Public Key (vô dụng để tạo token giả).|
|**Use Case**|Monolith, Internal Microservices (tin tưởng nhau tuyệt đối).|**Public APIs, Banking, OIDC (Auth0, Google).**|

---

## 4. Vấn đề nhức nhối: Revocation (Thu hồi)

Vì JWT là stateless (Server không lưu), làm sao Server "xé bỏ" tờ tiền polymer (Token) khi nó vẫn chưa hết hạn?

(Ví dụ: User báo mất điện thoại, Admin muốn logout user đó ngay lập tức).

### Giải pháp 1: Short Lived Token (Hạn ngắn)
- Để Access Token chỉ sống **5 phút**.
- Nếu muốn revoke, ta chỉ cần chặn Refresh Token.
- Hacker chỉ dùng được Access Token trong tối đa 5 phút còn lại. (Chấp nhận rủi ro nhỏ).

### Giải pháp 2: Blacklist (Deny List)
- Khi user logout, lưu `jti` (Token ID) hoặc `exp` của token đó vào **Redis**.
- Mỗi khi có request, Middleware check Redis xem token này có nằm trong sổ đen không.
- _Nhược điểm:_ Biến JWT thành Stateful (lại phụ thuộc Redis), nhưng nhanh hơn session DB.

### Giải pháp 3: Versioning (Allow List)

- Trong User DB lưu thêm cột `token_version = 1`.
- Trong JWT Payload cũng có `v: 1`.
- Khi muốn Revoke (Logout all devices): Tăng `token_version` trong DB lên 2.
- Các Token cũ (`v: 1`) gửi lên sẽ thấy không khớp với DB (`v: 2`) -> Từ chối.

---

## 5. Security Checklist cho JWT

1. **Luôn kiểm tra `alg` header:** Chặn tấn công `alg: "none"` (một số thư viện cũ dính lỗi cho phép token không cần ký vẫn pass).
2. **Validate đủ claims:** Phải check `exp` (hết hạn chưa), `iss` (đúng người phát hành không), `aud` (có phải token dành cho mình không).
3. **Weak Secret:** Với HS256, Secret Key phải dài và ngẫu nhiên (ít nhất 32 ký tự). Nếu dùng "secret123", hacker brute-force 1 giây là ra.
4. **Storage:**
    - **LocalStorage:** Dễ dính XSS (JS độc lấy trộm token).
    - **HttpOnly Cookie:** An toàn với XSS, nhưng cần chống CSRF. _Khuyên dùng cho Web App._

---

## 6. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: JWS vs. JWE là gì?
> 
> **A:**
> 
> - **JWS (Signed):** Token được ký để đảm bảo không bị sửa đổi, nhưng nội dung **công khai** (Ai cũng đọc được). Đây là chuẩn phổ biến nhất.
>     
> - **JWE (Encrypted):** Token được **mã hóa** toàn bộ nội dung. Chỉ người có Key mới đọc được Payload. Dùng khi cần truyền dữ liệu nhạy cảm (Số CCCD, Lương) qua Token.
>     

> [!QUESTION] Q: Nếu tôi đổi Secret Key thì sao?
> 
> **A:**
> 
> Toàn bộ Token đã phát hành trước đó sẽ **chết ngay lập tức** (Invalid Signature). Đây là cách "Kill Switch" khẩn cấp khi hệ thống bị lộ key, nhưng sẽ làm hàng triệu user bị logout cùng lúc.

> [!QUESTION] Q: JWT kích thước lớn ảnh hưởng gì?
> 
> **A:** JWT được gửi trong Header `Authorization: Bearer <token>` của **mỗi request**.
> 
> Nếu bạn nhét quá nhiều claims vào payload -> Header to -> Tốn băng thông mạng (đặc biệt với Mobile mạng yếu).
> 
> _Best Practice:_ Giữ JWT nhỏ gọn, chỉ chứa ID. Các thông tin chi tiết nên query từ DB hoặc Cache.
