---
title: "Golang: Goroutine Leak"
tags:
  - "golang"
  - "concurrency"
  - "memory-leak"
  - "performance"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Đã rõ. Tôi sẽ tuân thủ nghiêm ngặt việc sử dụng ` cho các đoạn mã Golang."
---

Đã rõ. Tôi sẽ tuân thủ nghiêm ngặt việc sử dụng ` ```go ` cho các đoạn mã Golang.

Chủ đề tiếp theo cực kỳ quan trọng đối với các hệ thống backend chạy lâu dài (Long-running services) của Ngân hàng: **Goroutine Leak** (Rò rỉ Goroutine).

---

# Golang: Goroutine Leak

## 1. Khái niệm (Mental Model)

> [!SUMMARY] Định nghĩa
> 
> **Goroutine Leak** xảy ra khi bạn khởi tạo một Goroutine nhưng nó **không bao giờ kết thúc** (không chạy đến dòng code cuối cùng hoặc không return).
> 
> Khác với Garbage Collector (GC) tự động dọn dẹp biến không dùng, **Go KHÔNG tự động dọn dẹp các Goroutine bị treo**. Chúng sẽ tồn tại mãi mãi, chiếm dụng RAM và CPU cho đến khi sập server (OOM - Out of Memory).

### Tại sao Ngân hàng sợ lỗi này?

Một API chuyển tiền bị leak 1 goroutine (2KB stack) thì không sao. Nhưng nếu API đó được gọi 1 triệu lần/ngày -> Server sẽ bị đầy bộ nhớ sau vài ngày mà không rõ nguyên nhân. Đây là "kẻ giết người thầm lặng".

---

## 2. Nguyên nhân phổ biến & Code Demo

Nguyên nhân số 1: **Blocked Channel**. Goroutine đứng chờ gửi/nhận từ một channel mà không có ai ở đầu dây bên kia.

### Kịch bản lỗi: "Gửi mà không ai nhận"

```go
package main

import (
	"fmt"
	"runtime"
	"time"
)

// Hàm này bị leak
func queryBankServer() int {
	ch := make(chan int)

	// Goroutine này sẽ bị TREO VĨNH VIỄN
	go func() {
		// Cố gắng gửi dữ liệu vào channel
		// Nhưng nếu main return trước khi nhận -> Goroutine này kẹt ở đây mãi mãi
		ch <- 100
	}()

	return <-ch
}

// Kịch bản rò rỉ thực tế hơn: Time out
func leakExample() {
	ch := make(chan int)

	go func() {
		// Giả lập xử lý chậm
		time.Sleep(2 * time.Second)
		ch <- 100 // BLOCK MÃI MÃI vì không còn ai lắng nghe (bên dưới đã return rồi)
		fmt.Println("Dòng này không bao giờ được in ra -> Goroutine đã bị Leak")
	}()

	// Main chỉ chờ 1 giây rồi bỏ đi
	select {
	case val := <-ch:
		fmt.Println("Nhận được:", val)
	case <-time.After(1 * time.Second):
		fmt.Println("Timeout! Bỏ qua, thoát hàm.")
		return // Thoát hàm leakExample, bỏ lại goroutine con bơ vơ
	}
}

func main() {
	fmt.Println("Số Goroutine ban đầu:", runtime.NumGoroutine())

	leakExample()

	time.Sleep(3 * time.Second) // Chờ xem goroutine con có chết không
	fmt.Println("Số Goroutine lúc sau:", runtime.NumGoroutine())
	// Kết quả: Vẫn cao hơn ban đầu -> LEAK!
}
```

---

## 3. Cách sửa (The Fix)

Có 2 cách chính để sửa lỗi leak do channel:

### Cách 1: Dùng Buffered Channel (Đủ chỗ chứa)

Nếu bạn biết chắc chỉ gửi 1 giá trị, hãy tạo buffer size = 1. Ngay cả khi không ai nhận, người gửi vẫn thả được hàng vào và đi về (return).

```go
func fixWithBuffer() {
	// Tạo buffer size 1
	ch := make(chan int, 1)

	go func() {
		time.Sleep(2 * time.Second)
		ch <- 100 // OK! Không bị block dù không ai nhận. Dữ liệu nằm trong buffer.
		fmt.Println("Goroutine con đã kết thúc an toàn.")
	}()

	select {
	case <-ch:
		// ...
	case <-time.After(1 * time.Second):
		return
	}
}
```

### Cách 2: Dùng Context (Chuẩn mực nhất)

Truyền tín hiệu `Done` vào để báo goroutine con tự sát.

```go
func fixWithContext() {
	// Tạo context có timeout
	ctx, cancel := context.WithTimeout(context.Background(), 1*time.Second)
	defer cancel()

	ch := make(chan int)

	go func() {
		// Logic gửi phải lắng nghe cả context
		select {
		case ch <- 100:
			// Gửi thành công
		case <-ctx.Done():
			// Main đã hủy hoặc timeout -> Rút lui ngay
			fmt.Println("Bị hủy, thoát goroutine con.")
			return
		}
	}()

	select {
	case <-ch:
		fmt.Println("Nhận được data")
	case <-ctx.Done():
		fmt.Println("Timeout ở Main")
	}
}
```

---

## 4. Cách phát hiện Leak (Công cụ)

Khi phỏng vấn, nếu được hỏi _"Làm sao biết server đang bị leak goroutine?"_, hãy trả lời:

1. **Monitoring (Prometheus/Grafana):** Theo dõi metric `go_goroutines`. Nếu biểu đồ đi lên theo đường chéo mà không bao giờ giảm xuống (răng cưa), đó là Leak.
    
2. **Pprof (Go Profiling):**
    
    - Truy cập endpoint debug: `/debug/pprof/goroutine?debug=1`.
        
    - Nó sẽ liệt kê tất cả goroutine đang chạy và dòng code nào đang giữ chúng (thường là dòng `ch <-` hoặc `select`).
        
3. **Uber Goleak (Dùng trong Unit Test):**
    
    - Thư viện `go.uber.org/goleak` giúp fail test ngay lập tức nếu sau khi chạy xong test mà vẫn còn goroutine dư thừa.
        

```go
func TestMain(m *testing.M) {
	goleak.VerifyTestMain(m)
}
```

---

## 5. Tổng kết

> [!TIP] Checklist tránh Leak
> 
> 1. Khi tạo Goroutine, phải luôn tự hỏi: **"Nó sẽ dừng lại khi nào và bằng cách nào?"**.
>     
> 2. Tuyệt đối cẩn thận khi gửi vào **Unbuffered Channel** mà không kiểm soát người nhận.
>     
> 3. Nếu Goroutine phụ thuộc vào I/O hoặc Time, phải luôn hỗ trợ **Context Cancellation**.
>     

---

_Ghi chú: Copy nội dung trên vào Obsidian._