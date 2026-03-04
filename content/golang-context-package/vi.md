---
title: "Golang: Context Package"
tags:
  - "golang"
  - "context"
  - "concurrency"
  - "backend"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Đây là giải thích chi tiết về Context Package - \"xương sống\" của lập trình Concurrency trong Go, đặc biệt quan trọng trong các hệ thống Backend/Banking để quản lý vòng đời request."
---

Đây là giải thích chi tiết về **Context Package** - "xương sống" của lập trình Concurrency trong Go, đặc biệt quan trọng trong các hệ thống Backend/Banking để quản lý vòng đời request.

---

# Golang: Context Package

## 1. Tổng quan (Mental Model)

> [!SUMMARY] Khái niệm
> 
> `context.Context` giống như một **"giấy thông hành"** được truyền từ hàm `main` xuống các hàm con, rồi xuống database/API layer.
> 
> Nó mang theo 3 thứ quan trọng:
> 
> 1. **Signal:** Tín hiệu để hủy bỏ công việc (Cancellation).
>     
> 2. **Time:** Thời hạn hoàn thành công việc (Deadline/Timeout).
>     
> 3. **Value:** Dữ liệu phạm vi request (RequestID, User Token...).
>     

---

## 2. Cancellation Propagation (Sự lan truyền hủy bỏ)

Context hoạt động theo mô hình **Cây (Tree Hierarchy)**.

- **Gốc (Root):** `context.Background()`
    
- **Nhánh (Child):** Được tạo ra từ cha bằng `WithCancel`, `WithTimeout`, v.v.
    

> [!DANGER] Nguyên tắc vàng (Propagation Rule)
> 
> Khi Context **Cha** bị hủy (do timeout hoặc gọi cancel):
> 
> -> **Tất cả Context Con, Cháu, Chắt...** sinh ra từ nó đều nhận được tín hiệu hủy **NGAY LẬP TỨC**.
> 
> _Ngược lại không đúng: Con hủy thì Cha không bị ảnh hưởng._

### Code Demo: Propagation

```go
package main

import (
	"context"
	"fmt"
	"time"
)

func main() {
	// 1. Tạo Context Cha
	parentCtx, parentCancel := context.WithCancel(context.Background())

	// 2. Tạo Context Con từ Cha
	childCtx, _ := context.WithCancel(parentCtx)

	// Goroutine theo dõi con
	go func() {
		<-childCtx.Done()
		fmt.Println("👶 Child Context: Đã chết theo cha!")
	}()

	fmt.Println("👨 Parent: Sắp hủy...")
	time.Sleep(1 * time.Second)

	// 3. Chỉ hủy Cha
	parentCancel()

	time.Sleep(1 * time.Second)
}
```

**Output:**

```text
👨 Parent: Sắp hủy...
👶 Child Context: Đã chết theo cha!
```

---

## 3. Timeout vs. Deadline

Hai khái niệm này mục đích giống nhau (dừng việc khi hết giờ) nhưng cách định nghĩa khác nhau.

|**Đặc điểm**|**WithTimeout**|**WithDeadline**|
|---|---|---|
|**Tham số**|`time.Duration` (Khoảng thời gian)|`time.Time` (Thời điểm cụ thể)|
|**Ví dụ**|"Chạy tối đa **5 giây** nữa."|"Phải xong trước **17:00:00 hôm nay**."|
|**Bản chất**|Gọi `WithDeadline(now + duration)`|Là hàm gốc.|
|**Use Case**|Hầu hết các API Call, DB Query.|Các tác vụ Cronjob, Batch job có giờ fix cứng.|

### Ví dụ thực tế: Database Query Timeout

Trong Banking, không bao giờ được để một query chạy mãi mãi.

```go
func GetBankAccount(accountID string) error {
    // 1. Thiết lập Timeout: Chỉ cho phép chạy trong 2 giây (SLA)
    // defer cancel() là BẮT BUỘC để giải phóng tài nguyên nếu xong sớm
    ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
    defer cancel()

    // 2. Truyền ctx vào hàm gọi Database/API
    // Giả sử hàm này mất 5 giây để chạy -> Sẽ bị lỗi
    err := callSlowDatabase(ctx)

    if err != nil {
        // Kiểm tra xem lỗi do timeout hay lỗi thật
        if ctx.Err() == context.DeadlineExceeded {
            return fmt.Errorf("❌ Lỗi: Query quá lâu (Timeout 2s)")
        }
        return err
    }
    return nil
}

func callSlowDatabase(ctx context.Context) error {
    // Giả lập DB chậm
    select {
    case <-time.After(5 * time.Second): // DB cần 5s
        return nil
    case <-ctx.Done(): // Context hết giờ sau 2s
        return ctx.Err() // Trả về context.DeadlineExceeded
    }
}
```

---

## 4. Best Practices (Luật bất thành văn)

> [!TIP] Interview Checklist
> 
> Khi code hoặc review code, hãy nhớ 4 luật này:

1. **Vị trí tham số:** `ctx context.Context` luôn phải là **tham số đầu tiên** của hàm.
    
    - `func DoSomething(ctx context.Context, arg string) ...`
        
2. **Không lưu trong Struct:** Không bao giờ lưu Context trong struct (trừ trường hợp rất đặc biệt). Hãy truyền nó qua từng hàm.
    
3. **Luôn gọi Cancel:** Khi dùng `WithCancel`, `WithTimeout`, `WithDeadline` -> Luôn phải `defer cancel()` ngay sau đó. Nếu không sẽ bị **Memory Leak** (Context không được giải phóng cho đến khi cha nó chết).
    
4. **Context Values (`WithValue`):**
    
    - Chỉ dùng cho dữ liệu **Request-scoped** (Request ID, User Identity, Tracing Span).
        
    - **KHÔNG** dùng để truyền tham số tùy chọn của hàm (Optional arguments).
        

---

## 5. Câu hỏi phỏng vấn nâng cao

> [!QUESTION] Q: Điều gì xảy ra nếu Context Con set Timeout dài hơn Context Cha?
> 
> **Ví dụ:** Cha (Timeout 2s) -> Con (Timeout 5s).
> 
> **A:** Context Con vẫn sẽ chết sau **2 giây**.
> 
> **Giải thích:** Context tuân theo luật "cái nào đến trước thì chết trước". Con bị giới hạn bởi vòng đời của Cha. Việc set 5s cho con trong trường hợp này là vô nghĩa về mặt mở rộng thời gian, nhưng nó vẫn có ý nghĩa nếu Cha sống lâu hơn 5s.

> [!QUESTION] Q: `context.Background()` và `context.TODO()` khác nhau gì?
> 
> **A:** Về mặt code: **Giống hệt nhau** (cả hai đều trả về một empty struct non-nil).
> 
> Về mặt ngữ nghĩa (Semantic):
> 
> - `Background()`: Dùng ở top-level (main, init, test entry).
>     
> - `TODO()`: Dùng khi chưa biết dùng context nào, hoặc code đang viết dở (placeholder) để trình phân tích code (linter) nhận biết.
>     

---

_Ghi chú: Copy vào Obsidian để hiển thị Callouts và Code block._