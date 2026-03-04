---
title: "System Design - CDN & Edge Computing"
tags:
  - "system-design"
  - "cdn"
  - "edge-computing"
  - "networking"
  - "performance"
  - "architecture"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Dù server Backend của bạn có tối ưu đến mức phản hồi trong 1ms, nhưng nếu Server đặt ở Virginia (Mỹ) mà User đang ở Hà Nội, tín hiệu vẫn phải đi qua cáp quang biển vòng nửa trái đất."
---

## 1. Vấn đề: Giới hạn của Tốc độ Ánh sáng

Dù server Backend của bạn có tối ưu đến mức phản hồi trong 1ms, nhưng nếu Server đặt ở **Virginia (Mỹ)** mà User đang ở **Hà Nội**, tín hiệu vẫn phải đi qua cáp quang biển vòng nửa trái đất.

- **Vật lý:** Ping từ VN sang Mỹ tối thiểu mất **200ms**.
- **Trải nghiệm:** Web load mất 2-3 giây (vì cần nhiều round-trip TCP/TLS).
    

> [!SUMMARY] Nguyên lý
> 
> Chúng ta không thể tăng tốc độ ánh sáng.
> Cách duy nhất để nhanh hơn là **mang dữ liệu đến gần người dùng hơn**.

**CDN (Content Delivery Network)** là một mạng lưới các server vệ tinh (Edge Servers) nằm rải rác khắp thế giới (Hà Nội, Sing, Tokyo, London...).

---

## 2. Cơ chế hoạt động: Static vs. Dynamic
### A. Static Assets (Ảnh, CSS, JS, Video)

Đây là "sân nhà" của CDN.
1. **Lần đầu:** User A (VN) vào web. CDN ở VN chưa có ảnh `logo.png`. Nó sẽ gọi về Origin Server (Mỹ) để lấy và lưu lại (Cache).
2. **Lần sau:** User B (VN) vào web. CDN trả về `logo.png` ngay lập tức từ server ở Hà Nội (Ping < 5ms). Origin Server ở Mỹ không cần làm gì cả.
    

### B. Dynamic Content (API, Database)

API lấy số dư tài khoản (`GET /balance`) không thể cache được. Vậy CDN giúp gì?

- **Route Optimization:** CDN tìm đường đi ngắn nhất và ổn định nhất qua mạng lưới riêng của họ (backbone) thay vì đi qua Public Internet chập chờn.
- **TCP/TLS Handshake Offloading:** Kết nối SSL được thiết lập ngay tại Edge (Hà Nội). Quãng đường còn lại về Mỹ dùng kết nối Keep-Alive có sẵn -> Giảm thời gian bắt tay.
    

---

## 3. Edge Computing - Khi CDN trở nên "Thông minh"

Ngày xưa, CDN chỉ là cái kho chứa file (Dumb Cache).

Ngày nay, với **Edge Computing** (AWS Lambda@Edge, Cloudflare Workers), ta có thể **chạy code ngay tại CDN**.

> [!TIP] Use Cases đắt giá
> 
> 1. **Image Resizing:**
>     User dùng iPhone -> Edge tự resize ảnh thành kích thước nhỏ. User dùng Desktop -> Edge trả ảnh to. Origin chỉ cần lưu 1 ảnh gốc chất lượng cao.
>     
> 2. **Auth/Security:**
>     Chặn IP của Hacker ngay tại Edge. Origin Server không bao giờ phải tốn CPU để xử lý request rác.
>     
> 3. **A/B Testing:**
>     Edge server quyết định User nào thấy giao diện A hay B rồi trả về HTML tương ứng, không cần về Backend.
>     

---

## 4. Streaming Video (Netflix/TikTok Architecture)

Làm sao Netflix phục vụ phim 4K cho 200 triệu người cùng lúc?

1. **Transcoding:** File phim gốc được cắt nhỏ thành hàng nghìn file `.ts` (chunks), mỗi file dài 2-4 giây, với nhiều độ phân giải khác nhau (360p, 720p, 4K).
    
2. **Pre-warming:** Trước giờ cao điểm (tối thứ 6), Netflix dự đoán phim nào sẽ Hot và **đẩy trước (Push)** các file này ra các Edge Server của nhà mạng (ISP) như Viettel/FPT.
    
3. **Adaptive Bitrate Streaming (HLS/DASH):**
    
    - App trên Tivi đo tốc độ mạng.
    - Mạng khỏe -> Tải file chunk 4K.
    - Mạng yếu -> Tự động chuyển sang tải file chunk 720p.
    - Tất cả đều lấy từ server đặt ngay tại trung tâm dữ liệu của Viettel/FPT -> Tốc độ cực nhanh.
        

---

## 5. Cache Invalidation (Bài toán khó nhất)

> _"There are only two hard things in Computer Science: cache invalidation and naming things."_

Khi bạn update file `style.css`, làm sao bắt CDN trên toàn thế giới cập nhật ngay lập tức?

1. **Purge (Xóa Cache):** Gửi lệnh lên CDN: _"Xóa ngay file style.css đi"_.
    - _Nhược điểm:_ Chậm (mất vài phút đến cả tiếng để lan truyền toàn cầu). Tốn kém.
        
2. **Versioning (Khuyên dùng):** Đổi tên file.
    - Thay vì `style.css`, hãy đặt tên là `style.v1.css`.
    - Khi sửa code -> Build ra file `style.v2.css`.
    - Update file HTML để trỏ vào v2.
    - -> CDN coi đây là file mới hoàn toàn -> **Cập nhật tức thì**.
        

---

## 6. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: CDN giúp gì trong việc chống DDoS?
> 
> **A:**
> 
> CDN hoạt động như một tấm khiên khổng lồ.
> 
> Với băng thông hàng Tbps, CDN có thể hấp thụ các đợt tấn công Volumetric (làm ngập lụt traffic) thay cho Origin Server. Origin Server được ẩn giấu IP thật, Hacker không thể tấn công trực tiếp.

> [!QUESTION] Q: "Thundering Herd" (Đàn bò chạy loạn) tại CDN là gì?
> 
> **A:**
> Khi một nội dung Hot (ví dụ: Livestream bóng đá) vừa bắt đầu, Cache chưa có dữ liệu.
> 1 triệu người cùng request file `video_chunk_1.ts` cùng lúc.
> Nếu CDN không thông minh, nó sẽ gửi 1 triệu request về Origin -> Sập Origin.
> _Giải pháp:_ **Request Collapsing**. CDN chỉ gửi **1 request duy nhất** về Origin, lấy file về, rồi copy trả cho 999.999 người còn lại.

> [!QUESTION] Q: Khi cấu hình `Cache-Control` header trong Golang, nên đặt là gì?
> 
> **A:**
> 
> - Với file có version (`app.v123.js`): `Cache-Control: public, max-age=31536000, immutable`. (Cache 1 năm, không bao giờ cần check lại).
> - Với file không có version (`index.html`): `Cache-Control: no-cache`. (Luôn phải hỏi lại Server xem có bản mới không trước khi dùng bản cache).
>     

---

