---
title: "Golang - Interface Internals"
tags:
  - "golang"
  - "internals"
  - "interface"
  - "interview"
  - "gotchas"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Trong Go runtime, Interface không chỉ là một con trỏ đơn thuần. Nó thực chất là một struct chứa 2 từ máy (machine words) (thường là 16 bytes trên hệ điều hành 64-bit)."
---

## 1. Cấu trúc nội tại (Internal Structure)

Trong Go runtime, Interface không chỉ là một con trỏ đơn thuần. Nó thực chất là một struct chứa **2 từ máy (machine words)** (thường là 16 bytes trên hệ điều hành 64-bit).

Tùy thuộc vào việc interface đó có phương thức (method) hay không, Go sử dụng 2 cấu trúc khác nhau: `eface` và `iface`.

### A. `eface` (Empty Interface - `interface{}`)

Dùng cho các interface **rỗng**, không có phương thức nào (mọi kiểu dữ liệu đều thỏa mãn).

**Cấu trúc (`runtime/runtime2.go`):**

```go
type eface struct {
    _type *_type          // Con trỏ tới thông tin kiểu dữ liệu (Type Descriptor)
    data  unsafe.Pointer  // Con trỏ tới dữ liệu thực tế (Concrete Data)
}
```

- **`_type`**: Chứa metadata về kiểu dữ liệu (tên kiểu, kích thước, hash...). Giúp Go thực hiện Type Assertion (`val.(int)`).
    
- **`data`**: Trỏ tới vùng nhớ heap (hoặc stack nếu escape analysis cho phép) chứa giá trị thực.
    

### B. `iface` (Non-empty Interface)

Dùng cho các interface **có phương thức** (ví dụ: `io.Reader`, `fmt.Stringer`).

**Cấu trúc (`runtime/runtime2.go`):**

```go
type iface struct {
    tab  *itab           // Con trỏ tới bảng Interface Table
    data unsafe.Pointer  // Con trỏ tới dữ liệu thực tế
}
```

- **`tab` (`itab`)**: Đây là điểm khác biệt chính. Nó chứa:
    
    - Con trỏ tới `_type` (như eface).
        
    - Danh sách các **hàm (function pointers)** khớp với interface đó. Điều này giúp việc gọi hàm qua interface (`i.Read()`) rất nhanh (dynamic dispatch) mà không cần reflection.
        

---

## 2. The Nil Interface Trap (Cái bẫy Nil Interface)

Đây là câu hỏi phỏng vấn "sát thủ" và là nguồn gốc của nhiều bug runtime.

> [!ERROR] The Rule
> 
> Một Interface chỉ bằng `nil` khi và chỉ khi **CẢ HAI** thành phần của nó (`type` và `data`) đều là `nil`.

### Kịch bản lỗi kinh điển

Bạn trả về một con trỏ `nil` của một struct cụ thể, nhưng hàm lại trả về kiểu `interface`.

```go
package main

import "fmt"

// Định nghĩa lỗi tùy chỉnh
type MyError struct {
    Msg string
}

func (e *MyError) Error() string {
    return e.Msg
}

// Hàm này có vấn đề!
func runTask(fail bool) error {
    var err *MyError = nil // Khởi tạo con trỏ struct là nil
    if fail {
        err = &MyError{Msg: "Boom!"}
    }
    // TRAP: Trả về 'err' (đang là nil pointer cụ thể) dưới dạng 'error' interface
    return err
}

func main() {
    err := runTask(false)

    if err != nil {
        fmt.Println("⚠️ Có lỗi xảy ra (nhưng thực ra là không)!")
        fmt.Printf("Giá trị err: %v\n", err)
        fmt.Printf("Kiểu err: %T\n", err)
    } else {
        fmt.Println("✅ Thành công")
    }
}
```

**Kết quả chạy:**

```text
⚠️ Có lỗi xảy ra (nhưng thực ra là không)!
Giá trị err: <nil>
Kiểu err: *main.MyError
```

### Tại sao lại như vậy? (Deep Dive)

Khi lệnh `return err` chạy, Go thực hiện **boxing** (đóng gói) con trỏ `*MyError` vào trong interface `error`.

Cấu trúc bộ nhớ của biến `err` (interface) lúc này sẽ như sau:

|**Thành phần**|**Giá trị**|**Giải thích**|
|---|---|---|
|**Type** (`tab/_type`)|`*main.MyError`|Không phải `nil` vì nó giữ thông tin kiểu con trỏ.|
|**Data** (`data`)|`nil` (0x0)|Giá trị thực tế là con trỏ nil.|

**So sánh logic:**

- `err == nil` thực chất là so sánh: `(type=*MyError, data=nil) == (type=nil, data=nil)`
    
- Kết quả là **FALSE**.
    

### Cách sửa (Best Practices)

> [!TIP] Solution
> 
> Luôn trả về `nil` interface một cách tường minh nếu không có lỗi, thay vì trả về con trỏ typed nil.

**Sửa lại hàm `runTask`:**

```go
func runTask(fail bool) error {
    if fail {
        return &MyError{Msg: "Boom!"}
    }
    return nil // ✅ Trả về nil interface thực sự (type=nil, data=nil)
}
```

---

## 3. Tổng kết so sánh

|**Đặc điểm**|**eface (Empty)**|**iface (Non-empty)**|
|---|---|---|
|**Đại diện**|`interface{}` hoặc `any` (Go 1.18+)|Interface có methods (vd: `io.Reader`)|
|**Metadata**|`_type` pointer|`itab` pointer (chứa cả methods dispatch)|
|**Kích thước**|2 words|2 words|
|**Hiệu năng**|Nhanh hơn khi gán/copy.|Chậm hơn xíu do khởi tạo `itab` (nhưng cache tốt).|

> [!QUESTION] Câu hỏi phỏng vấn
> 
> **Q:** `var i interface{} = (*int)(nil)`. Hỏi `i == nil` trả về true hay false?
> 
> **A:** `False`. Vì `i` có Type là `*int`, Data là `nil`. Interface chỉ nil khi Type cũng nil.
