---
title: "Golang - Map Internals & Thread Safety"
tags:
  - "golang"
  - "internals"
  - "map"
  - "concurrency"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "> [!INFO] Mental Model > > Map trong Go là một Hash Table. > > Nó được thiết kế để tối ưu tốc độ, KHÔNG phải để an toàn đa luồng (Thread-safe)."
---

## 1. Cấu trúc nội tại (Map Anatomy)

> [!INFO] Mental Model
> 
> Map trong Go là một **Hash Table**.
> 
> Nó được thiết kế để tối ưu tốc độ, **KHÔNG** phải để an toàn đa luồng (Thread-safe).

Bên dưới `map` là một con trỏ trược tới struct `hmap` (định nghĩa trong `runtime/map.go`).

Go

```go
// Runtime structure (đơn giản hóa)
type hmap struct {
    count     int    // Số lượng phần tử hiện tại
    flags     uint8  // Trạng thái (đang ghi, đang resize...)
    B         uint8  // Logarit cơ số 2 của số lượng buckets (2^B buckets)
    buckets   unsafe.Pointer // Mảng các bucket
    oldbuckets unsafe.Pointer // Mảng bucket cũ (dùng khi resize)
}
```

### Bucket là gì?

- Mỗi bucket chứa tối đa **8 cặp key/value**.
    
- 8 bit cao (Top Hash) của mã hash được lưu riêng để so sánh nhanh.
    
- Nếu bucket đầy (Overflow), nó sẽ nối với một bucket tràn (overflow bucket) khác theo danh sách liên kết.
    

---

## 2. Vấn đề: Concurrent Map Writes

Đây là lỗi **Fatal Error** phổ biến nhất khi làm việc với Goroutine.

> [!DANGER] The Crash
> 
> `fatal error: concurrent map writes`
> 
> Go Runtime chủ động phát hiện việc có 1 luồng đang GHI và 1 luồng khác đang ĐỌC/GHI cùng lúc vào một map. Nó sẽ làm sập chương trình ngay lập tức (Panic không thể recover) để bảo vệ dữ liệu không bị hỏng (corruption).

### Code gây lỗi (Crash)

Go

```go
package main

import "time"

func main() {
	// Map không an toàn
	m := make(map[string]int)

	// Goroutine GHI
	go func() {
		for {
			m["balance"] = 100
		}
	}()

	// Goroutine ĐỌC (Hoặc Ghi khác) -> CRASH NGAY LẬP TỨC
	go func() {
		for {
			_ = m["balance"]
		}
	}()

	time.Sleep(1 * time.Second)
}
```

---

## 3. Giải pháp: Mutex vs sync.Map

Có 2 cách chính để xử lý map trong môi trường concurrency. Phỏng vấn viên sẽ hỏi khi nào dùng cái nào.

### Cách 1: Map thường + `sync.RWMutex` (Khuyên dùng 90%)

Dễ hiểu, hiệu năng tốt, type-safe (an toàn kiểu).

Go

```go
package main

import "sync"

type BankCache struct {
	mu    sync.RWMutex     // Khóa bảo vệ
	data  map[string]int   // Map thường
}

func (c *BankCache) Get(key string) int {
	c.mu.RLock()         // Cho phép nhiều người đọc cùng lúc
	defer c.mu.RUnlock()
	return c.data[key]
}

func (c *BankCache) Set(key string, value int) {
	c.mu.Lock()          // Chỉ 1 người được ghi
	defer c.mu.Unlock()
	c.data[key] = value
}
```

### Cách 2: `sync.Map` (Chuyên dụng)

Go 1.9 giới thiệu `sync.Map`. Nó không cần init (`make`), không cần Generic (lưu `interface{}`).

> [!QUESTION] Khi nào dùng `sync.Map`?
> 
> Chỉ dùng trong 2 trường hợp đặc biệt (theo document của Go):
> 
> 1. **Append-only:** Khi khóa (key) chỉ được thêm vào một lần và đọc rất nhiều lần (Cache entry).
>     
> 2. **Disjoint Sets:** Khi nhiều goroutine đọc/ghi các tập key khác nhau (ít va chạm).
>     

Nếu không rơi vào 2 trường hợp trên, `sync.Map` có thể **CHẬM HƠN** map thường + Mutex do chi phí ép kiểu (interface assertion) và cơ chế nội tại phức tạp.

Go

```go
package main

import (
	"fmt"
	"sync"
)

func main() {
	var m sync.Map

	// 1. Store (Lưu)
	m.Store("user_1", 5000)

	// 2. Load (Đọc)
	val, ok := m.Load("user_1")
	if ok {
		// Phải ép kiểu thủ công vì val là interface{}
		fmt.Println("Balance:", val.(int))
	}

	// 3. LoadOrStore (Atomic: Lấy ra, nếu chưa có thì lưu cái mới)
	// Rất hữu ích cho Lazy Loading Cache
	actual, loaded := m.LoadOrStore("user_2", 1000)
	if loaded {
		fmt.Println("Đã có sẵn:", actual)
	} else {
		fmt.Println("Mới tạo:", actual)
	}
}
```

---

## 4. Câu hỏi phỏng vấn nâng cao

> [!QUESTION] Q: Tại sao Go Map không hỗ trợ concurrency mặc định (như Java `ConcurrentHashMap`)?
> 
> **A:** Vì lý do **Hiệu năng (Performance)**.
> 
> Đa số trường hợp sử dụng map không cần thread-safety. Nếu thêm lock vào mọi thao tác map, nó sẽ làm chậm tất cả các chương trình đơn luồng. Go nhường quyền kiểm soát lại cho lập trình viên để chọn giải pháp tối ưu nhất (dùng Mutex bên ngoài).

> [!QUESTION] Q: Map resize (tăng kích thước) hoạt động thế nào?
> 
> **A:** Khi map đầy (Load Factor > 6.5), Go sẽ cấp phát mảng bucket mới lớn gấp đôi.
> 
> Quá trình di chuyển dữ liệu (Evacuation) diễn ra **từ từ (incrementally)** mỗi khi có thao tác thêm/xóa, chứ không làm một lần (gây lag hệ thống).

---

_Ghi chú: Copy nội dung trên vào Obsidian._