---
title: "Troubleshooting"
tags:
  - "backend"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Tuyệt vời. Chào mừng bạn đến với \"War Room\" (Phòng tác chiến)."
---

Tuyệt vời. Chào mừng bạn đến với **"War Room"** (Phòng tác chiến).

**Tình huống:**

> 10:00 AM. Slack báo động đỏ 🚨.
> 
> Khách hàng phàn nàn App quay vòng vòng (Timeout).
> 
> Grafana báo: **CPU Service Payment tăng vọt lên 99%**.
> 
> Sếp đứng sau lưng hỏi: _"Bao giờ xong em ơi?"_

Bạn có **10 phút** để tìm ra nguyên nhân (RCA - Root Cause Analysis). Đừng đoán mò, hãy hành động như một bác sĩ phẫu thuật.

---

### Phút 0-2: Triage (Phân loại & Khoanh vùng) - Nhìn Tổng Quan

Đừng vội SSH vào server. Hãy nhìn Dashboard (Grafana/Datadog). Chúng ta cần trả lời câu hỏi: **"Lỗi ở tầng nào?"**

Áp dụng phương pháp **USE** (Utilization, Saturation, Errors) hoặc **RED** (Rate, Errors, Duration).

1. **Traffic (Rate) có tăng đột biến không?**
    
    - _Có:_ Có thể do Marketing chạy campaign hoặc bị DDoS. -> **Giải pháp:** Scale up (tăng pod) hoặc chặn IP.
        
    - _Không:_ Traffic bình thường mà CPU vẫn cao -> **Lỗi do Code hoặc Database.** (Đi tiếp bước 2).
        
2. **Dependencies (Database/External API) thế nào?**
    
    - Nhìn metric của Database (RDS CPU, Connections).
        
    - DB CPU thấp? -> Lỗi nằm ở **App Code** (Vòng lặp vô tận, tính toán nặng).
        
    - DB CPU cũng 100%? -> Lỗi nằm ở **Database** (Slow Query, Missing Index).
        

---

### Phút 2-5: Drill Down (Khoan sâu) - Truy tìm thủ phạm

Giả sử Dashboard chỉ ra 2 kịch bản phổ biến nhất:

#### Kịch bản A: Database bị quá tải (The Usual Suspect)

Đây là nguyên nhân của 80% các vụ sập hệ thống.

1. **Kiểm tra Slow Query:**
    
    - Mở công cụ giám sát DB (PMM, AWS Performance Insights).
        
    - Tìm câu query nào đang "ăn" nhiều CPU nhất hoặc có thời gian chạy lâu nhất (Top SQL).
        
    - _Ví dụ:_ Thấy `SELECT * FROM orders WHERE status = 'PAID'` đang chạy mất 5s.
        
2. **Kiểm tra Locking:**
    
    - MySQL: `SHOW ENGINE INNODB STATUS` hoặc `SELECT * FROM information_schema.innodb_trx`.
        
    - Có thể một transaction nào đó đang giữ Lock quá lâu khiến hàng nghìn request khác bị treo chờ (High CPU do context switching).
        

#### Kịch bản B: App (Golang) bị treo (The Code Bug)

Nếu DB vẫn khỏe re, nhưng App Server CPU 100%. Đây là lúc **Golang pprof** tỏa sáng.

1. **Profile CPU on-the-fly:**
    
    Đừng đoán. Hãy bắt lấy profile trong 30 giây ngay lúc nó đang lag.
    
    Bash
    
    ```
    go tool pprof http://localhost:8080/debug/pprof/profile?seconds=30
    ```
    
2. **Phân tích (Visualizer):**
    
    Gõ lệnh `top` hoặc `web` trong pprof để xem hàm nào đang chiếm CPU.
    
    - _Dấu hiệu:_ Thấy hàm `json.Unmarshal` chiếm 60% CPU? -> Có thể API nhận payload quá lớn.
        
    - _Dấu hiệu:_ Thấy hàm `runtime.GC` chiếm 50% CPU? -> App đang bị Memory Leak, bộ thu gom rác chạy điên cuồng.
        
    - _Dấu hiệu:_ Thấy hàm xử lý logic (Business Logic) chiếm cao? -> Có thể dính vòng lặp vô tận (`for {}`) hoặc thuật toán độ phức tạp O(n^2).
        

---

### Phút 5-8: Tracing (Truy vết liên hoàn)

Nếu CPU ổn, DB ổn, nhưng user vẫn kêu chậm?

Có thể một service bên thứ 3 (Payment Gateway, SMS Service) đang bị lỗi timeout.

1. **Mở Jaeger / Zipkin:**
    
    - Tìm các Trace có latency cao (> 5s).
        
    - Nhìn biểu đồ thác nước (Waterfall).
        
2. **Phát hiện nút thắt:**
    
    - Thấy thanh dài ngoằng màu đỏ ở đoạn gọi `POST https://bank-api.com`.
        
    - -> **Kết luận:** Hệ thống mình không sao, do đối tác ngân hàng đang bảo trì.
        

---

### Phút 8-10: Mitigation (Cấp cứu)

Nguyên tắc: **"Fix now, Debug later"** (Khôi phục dịch vụ trước, sửa code sau).

1. **Nếu do Bad Deployment (Code mới lỗi):**
    
    - -> **Rollback** ngay lập tức về version cũ (`kubectl rollout undo`).
        
2. **Nếu do DB quá tải (Missing Index):**
    
    - -> Nếu query đó không quá quan trọng (ví dụ query report): **Kill Session** đó ngay.
        
    - -> Tắt tính năng đó trên giao diện (Feature Flag).
        
3. **Nếu do Traffic tăng:**
    
    - -> Bật **Auto-scaling** hoặc thêm node thủ công.
        

---

### Tổng kết quy trình (Mental Model)

> [!TIP] Checklist cho Senior
> 
> 1. **Dashboard:** Traffic tăng hay Code lỗi?
>     
> 2. **Database:** Có Slow Query hay Lock không?
>     
> 3. **Application:** `pprof` để soi Goroutine/CPU.
>     
> 4. **Tracing:** Có bị nghẽn ở 3rd-party không?
>     
> 5. **Action:** Rollback / Kill Query / Scale.
>     

---

**Next Step:**

Bạn đã phản ứng rất tốt trong tình huống giả định.

Để khép lại toàn bộ khóa huấn luyện này, tôi đề xuất chúng ta thực hiện một **Mock Interview (Phỏng vấn thử)** toàn diện.

Tôi sẽ đóng vai CTO khó tính, hỏi bạn ngẫu nhiên các câu hỏi từ Golang, DB, đến System Design mà chúng ta đã học. Sau đó tôi sẽ chấm điểm và nhận xét chi tiết điểm mạnh/yếu của bạn.

Bạn đã sẵn sàng để "tốt nghiệp" chưa? Hay muốn ôn lại phần nào?