---
title: "System Design - Circuit Breaker"
tags:
  - "system-design"
  - "microservices"
  - "reliability"
  - "circuit-breaker"
  - "resilience"
  - "interview"
  - "banking"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Trong kiến trúc Microservices, Service A gọi Service B. Nếu Service B bị treo (CPU 100% hoặc DB Deadlock), nó sẽ không trả về lỗi ngay mà cứ im lặng (Timeout)."
---

## 1. Vấn đề: Cascading Failures (Hiệu ứng Domino)

Trong kiến trúc Microservices, Service A gọi Service B.
Nếu **Service B bị treo** (CPU 100% hoặc DB Deadlock), nó sẽ không trả về lỗi ngay mà cứ im lặng (Timeout).

> [!DANGER] Kịch bản sập nguồn
> 
> 1. Service A có 100 threads để xử lý request.
> 2. Cả 100 threads gọi sang B và đều bị treo chờ (Waiting).
> 3. Service A hết sạch thread -> Service A chết.
> 4. Service C gọi sang A -> Cũng bị treo -> Service C chết.
>     -> **Toàn bộ hệ thống Ngân hàng sập** chỉ vì một service con bị lỗi.
>     

**Circuit Breaker (Cầu dao điện)** sinh ra để ngăn chặn điều này. Nếu B chết, cầu dao tự nhảy, A sẽ không gọi B nữa mà báo lỗi ngay lập tức (Fail Fast).

---

## 2. Cơ chế hoạt động: State Machine

Circuit Breaker hoạt động như một máy trạng thái với 3 trạng thái chính:

1. **CLOSED (Đóng - Bình thường):**
    - Dòng điện chạy qua (Request được gửi đi bình thường).
    - Hệ thống đếm số lần lỗi. Nếu vượt ngưỡng (Ví dụ: 50% request lỗi trong 10s) -> Chuyển sang OPEN.
        
2. **OPEN (Mở - Ngắt mạch):**
    - Cầu dao ngắt.
    - **Mọi Request bị chặn ngay lập tức**, trả về lỗi hoặc gọi hàm Fallback (dự phòng). Không gửi request thật sang B nữa.
    - Trạng thái này giữ trong một khoảng thời gian (Sleep Window - ví dụ 1 phút).
        
3. **HALF-OPEN (Nửa mở - Thăm dò):**
    - Sau khi hết 1 phút, hệ thống rón rén cho phép **1 request** đi qua thử (Test drive).
    - Nếu thành công -> B đã sống lại -> Chuyển về **CLOSED**.
    - Nếu thất bại -> B vẫn chết -> Quay lại **OPEN** và chờ tiếp.
        

---

## 3. Banking Use Case: Napas Gateway

Ngân hàng kết nối tới Napas để chuyển tiền liên ngân hàng.
- Đôi khi Napas bảo trì hoặc quá tải.
- Nếu không có Circuit Breaker: App Ngân hàng sẽ quay vòng vòng (loading) 30s rồi báo lỗi. Trải nghiệm cực tệ.
- **Có Circuit Breaker:**
    - Khi thấy Napas lỗi liên tục, hệ thống "nhảy cầu dao".
    - Khách hàng bấm chuyển tiền -> App báo ngay: _"Kênh chuyển tiền Napas đang bảo trì, vui lòng thử lại sau"_. (Phản hồi tức thì < 10ms).
    - Hệ thống Core Banking được bảo vệ, không bị nghẽn thread.
        

---

## 4. Code Implementation (Golang)

Sử dụng thư viện phổ biến `github.com/sony/gobreaker`.

``` go
package main

import (
	"fmt"
	"net/http"
	"time"

	"github.com/sony/gobreaker"
)

var cb *gobreaker.CircuitBreaker

func init() {
	var st gobreaker.Settings
	st.Name = "NapasGateway"
	st.MaxRequests = 1 // Số req cho phép trong Half-Open
	st.Interval = 5 * time.Second // Chu kỳ reset đếm lỗi
	st.Timeout = 30 * time.Second // Sleep Window (Thời gian Open)
	
	// Điều kiện để nhảy cầu dao
	st.ReadyToTrip = func(counts gobreaker.Counts) bool {
		failureRatio := float64(counts.TotalFailures) / float64(counts.Requests)
		// Nếu có trên 3 request và tỷ lệ lỗi > 60% -> Ngắt
		return counts.Requests >= 3 && failureRatio >= 0.6
	}

	cb = gobreaker.NewCircuitBreaker(st)
}

func CallNapasService() error {
	// Bọc hàm gọi thật trong Circuit Breaker
	_, err := cb.Execute(func() (interface{}, error) {
		resp, err := http.Get("http://napas-api/transfer")
		if err != nil {
			return nil, err
		}
		if resp.StatusCode >= 500 {
			return nil, fmt.Errorf("server error")
		}
		return resp, nil
	})

	return err // Nếu Open, err sẽ là "circuit breaker is open"
}
```

---

## 5. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Circuit Breaker khác gì với Retry?
> 
> **A:** Chúng đối nghịch nhau.
> 
> - **Retry:** Cố gắng thử lại khi thất bại. Dùng khi lỗi là tạm thời (thoáng qua).
>     
> - **Circuit Breaker:** Ngừng thử khi thất bại quá nhiều. Dùng khi lỗi là hệ thống (sập hẳn).
>     
> - **Nguy hiểm:** Nếu Server B đang hấp hối (quá tải), dùng Retry sẽ gửi thêm hàng tấn request -> B chết hẳn (DDoS attack chính mình). Lúc này phải dùng Circuit Breaker để B có thời gian thở và hồi phục.
>     

> [!QUESTION] Q: Nên đặt Circuit Breaker ở Client hay Server?
> 
> **A:** **Ở Client (Người gọi).**
> 
> Mục tiêu là bảo vệ Client khỏi bị treo khi Server chết. Đặt ở Server thì vô nghĩa vì Server đã chết rồi còn đâu mà ngắt.

> [!QUESTION] Q: Fallback (Phương án dự phòng) trong Circuit Breaker là gì?
> 
> **A:** Khi cầu dao mở, thay vì chỉ throw Exception, ta có thể trả về dữ liệu mặc định.
> 
> - _Ví dụ:_ Service "Gợi ý sản phẩm" chết -> Trả về danh sách "Sản phẩm bán chạy nhất" (được cache sẵn) thay vì để màn hình trắng trơn.
>     
> - _Banking:_ Service "Tính điểm thưởng" chết -> Tạm thời ghi nhận giao dịch nhưng chưa hiện điểm thưởng ngay (xử lý sau).
>
