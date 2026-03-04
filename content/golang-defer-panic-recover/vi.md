---
title: "Golang: Defer, Panic, Recover"
tags:
  - "golang"
  - "control-flow"
  - "error-handling"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "> [!INFO] Mental Model > > Hãy tưởng tượng giống như việc xếp bát đĩa vào ngăn xếp (Stack). > > - Cái nào vào sau cùng (Last In) sẽ được lấy ra rửa trước tiên (First Out). > > - Nguyên lý: LIFO..."
---

# Golang: Defer, Panic, Recover

## 1. Defer: Cơ chế Stack (LIFO)

> [!INFO] Mental Model
> 
> Hãy tưởng tượng `defer` giống như việc xếp bát đĩa vào **ngăn xếp (Stack)**.
> 
> - Cái nào vào sau cùng (Last In) sẽ được lấy ra rửa trước tiên (First Out).
>     
> - Nguyên lý: **LIFO (Last-In, First-Out)**.
>     

### Tại sao lại cần LIFO?

Để đảm bảo tài nguyên được giải phóng đúng theo thứ tự ngược lại với lúc khởi tạo.

- Mở File A -> Mở File B.
    
- Khi đóng: Phải đóng File B trước -> Rồi mới đóng File A.
    

### Code Demo: LIFO Order

```go
package main

import "fmt"

func main() {
	fmt.Println("1. Bắt đầu")

	defer fmt.Println("2. Defer Lần 1 (Cuối cùng)")
	defer fmt.Println("3. Defer Lần 2 (Ở giữa)")
	defer fmt.Println("4. Defer Lần 3 (Đầu tiên)")

	fmt.Println("5. Kết thúc hàm Main")
	// Sau dòng này, các lệnh defer mới bắt đầu chạy ngược từ dưới lên
}
```

**Output:**

```text
1. Bắt đầu
2. Kết thúc hàm Main
3. Defer Lần 3 (Đầu tiên)
4. Defer Lần 2 (Ở giữa)
5. Defer Lần 1 (Cuối cùng)
```

---

## 2. Bẫy phỏng vấn: Defer Arguments Evaluation

Đây là câu hỏi loại "Senior" để xem bạn hiểu sâu đến đâu.

> [!WARNING] The Trap
> 
> Các tham số (arguments) của hàm trong `defer` được tính toán **NGAY LẬP TỨC** tại dòng code khai báo `defer`, chứ **KHÔNG PHẢI** đợi đến cuối hàm mới tính.

### Ví dụ "Sát thủ"

```go
func main() {
    i := 0
    // Giá trị i được "chụp ảnh" (snapshot) ngay lúc này là 0
    defer fmt.Println("Giá trị i (defer):", i)

    i++
    fmt.Println("Giá trị i (main):", i)
}
```

**Output:**

```text
Giá trị i (main): 1
Giá trị i (defer): 0  <-- BẤT NGỜ CHƯA?
```

**Cách sửa (Nếu muốn lấy giá trị mới nhất):**

Dùng hàm ẩn danh (Anonymous function/Closure) để tham chiếu tới biến `i` thay vì truyền giá trị `i`.

```go
defer func() {
    fmt.Println("Giá trị i (closure):", i) // Lúc này mới đọc giá trị i tại vùng nhớ
}()
```

---

## 3. Panic & Recover: Cơ chế "Túi khí" (Airbag)

Trong Go, `panic` là lỗi không thể xử lý bình thường (tương tự Unchecked Exception), nó sẽ làm sập chương trình. `recover` là cách duy nhất để bắt lại cú panic đó và giúp chương trình "hạ cánh mềm".

> [!DANGER] Nguyên tắc Recover
> 
> 1. `recover` chỉ có tác dụng khi được gọi **BÊN TRONG** một hàm `defer`.
>     
> 2. Nếu gọi `recover` ở chỗ khác, nó trả về `nil` và không có tác dụng gì.
>     

### Ví dụ Banking: Bảo vệ Server khỏi sập

Giả sử bạn có hàm tính toán lãi suất, nhưng nhỡ đâu có lỗi chia cho 0 (Divide by Zero) gây Panic. Bạn không muốn cả server ngân hàng sập chỉ vì 1 giao dịch lỗi.

```go
package main

import "fmt"

func SafeTransaction() {
    // 1. Kích hoạt lưới an toàn (Airbag)
    defer func() {
        if r := recover(); r != nil {
            // r chứa thông báo lỗi panic
            fmt.Println("⚠️ ĐÃ BẮT ĐƯỢC LỖI:", r)
            fmt.Println("🔄 Đang Rollback giao dịch... Xong.")
        }
    }()

    fmt.Println("-> Đang xử lý giao dịch...")

    // 2. Giả lập lỗi nghiêm trọng (Panic)
    triggerPanic()

    fmt.Println("-> Dòng này sẽ KHÔNG bao giờ chạy được")
}

func triggerPanic() {
    panic("Lỗi chia cho 0 tại Core Banking!")
}

func main() {
    SafeTransaction()
    fmt.Println("✅ Server vẫn sống, tiếp tục phục vụ khách hàng khác.")
}
```

**Output:**

```text
-> Đang xử lý giao dịch...
⚠️ ĐÃ BẮT ĐƯỢC LỖI: Lỗi chia cho 0 tại Core Banking!
🔄 Đang Rollback giao dịch... Xong.
✅ Server vẫn sống, tiếp tục phục vụ khách hàng khác.
```

---

## 4. Defer & Named Return Values (Nâng cao)

`defer` có thể **thay đổi giá trị trả về** của hàm nếu hàm đó sử dụng **Named Return Values** (giá trị trả về có đặt tên).

> [!TIP] Ứng dụng thực tế
> 
> Dùng để **bắt lỗi (Error Handling)** gọn gàng. Bạn có thể set biến `err` trong `defer` nếu có panic xảy ra.

```go
// Hàm trả về named variable "err"
func WriteToDatabase() (err error) {
    // Nếu có panic, convert nó thành error trả về êm đẹp
    defer func() {
        if r := recover(); r != nil {
            err = fmt.Errorf("panic recovered: %v", r)
        }
    }()

    panic("DB connection lost") // Gây panic
    return nil
}

func main() {
    err := WriteToDatabase()
    fmt.Println("Kết quả:", err)
    // Output: Kết quả: panic recovered: DB connection lost
}
```

---

## 5. Tổng kết cho phỏng vấn

|**Tính chất**|**Mô tả**|**Lưu ý quan trọng**|
|---|---|---|
|**Thứ tự**|LIFO (Vào sau ra trước).|Quan trọng khi giải phóng resource lồng nhau.|
|**Tham số**|Đánh giá ngay lập tức (Eager evaluation).|Dùng Closure nếu muốn lấy giá trị cuối cùng.|
|**Panic**|Dừng luồng, chạy hết các defer rồi crash.|Crash lan ra cả chương trình nếu không recover.|
|**Recover**|Chỉ hoạt động trong Defer.|Giúp convert Panic -> Error hoặc Log lại sự cố.|

> [!QUESTION] Câu hỏi tình huống
> 
> **Q:** Tôi có nên dùng `panic` và `recover` để thay thế `if err != nil` (giống try-catch trong Java) không?
> 
> **A:** **TUYỆT ĐỐI KHÔNG**.
> 
> Triết lý của Go là "Errors are values". Panic chỉ dùng cho lỗi không thể lường trước (logic sai, index out of range, nil pointer). Lỗi nghiệp vụ (không tìm thấy user, hết tiền) phải trả về `error`. Lạm dụng panic làm code khó đọc và chậm hơn (do stack unwinding).

---

_Ghi chú: Copy nội dung trên vào Obsidian._