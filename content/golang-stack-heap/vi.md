---
title: "Golang - Stack & Heap"
tags:
  - "golang"
  - "backend"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Mỗi khi một Goroutine khởi chạy, nó được cấp một khối bộ nhớ gọi là Stack."
---

#### 1. Stack Frame (Khung ngăn xếp)

Mỗi khi một Goroutine khởi chạy, nó được cấp một khối bộ nhớ gọi là **Stack**.

- Khi một hàm được gọi, một **Stack Frame** mới được tạo ra trên đỉnh của Stack để chứa các biến cục bộ của hàm đó.
    
- Khi hàm thực thi xong, Stack Frame đó bị "xóa" (thực tế là đánh dấu không còn hợp lệ), và bộ nhớ đó sẵn sàng cho hàm tiếp theo sử dụng.
    
- **Lợi ích:** Cơ chế này "tự làm sạch" (self-cleaning), rất nhanh và không cần Garbage Collector (GC) dọn dẹp.
    

#### 2. Truyền Giá Trị (Pass by Value) - Mặc định

Trong Go, mọi thứ mặc định là **truyền giá trị (copy)**. Khi bạn truyền một biến vào hàm, Go tạo ra một bản sao của biến đó trong Stack Frame của hàm mới.

**Ví dụ:**

```go
func main() {
    count := 10
    // Giá trị 10 được copy sang hàm inc.
    // Biến count ở main KHÔNG bị thay đổi.
    inc(count)
    println(count) // Vẫn in ra 10
}

func inc(val int) {
    val++ // Chỉ tăng bản sao cục bộ trong frame của inc
}
```

#### 3. Chia sẻ xuống (Sharing Down) - Dùng Con trỏ

Để hàm con thay đổi dữ liệu của hàm cha, ta dùng **Con trỏ (Pointer)**. Đây là việc truyền địa chỉ bộ nhớ thay vì truyền giá trị. Vì Stack Frame của hàm con nằm "trên" hàm cha, nó có thể truy cập ngược xuống địa chỉ của hàm cha một cách an toàn.

**Ví dụ:**

```go
func main() {
    count := 10
    // Truyền địa chỉ của count (&count)
    inc(&count)
    println(count) // In ra 11 (đã bị thay đổi)
}

func inc(val *int) {
    // *val truy cập vào địa chỉ bộ nhớ đó để sửa đổi
    *val++
}
```

#### 4. Chia sẻ lên (Sharing Up) & Escape Analysis

Đây là điểm đặc biệt của Go so với C/C++.

- **Vấn đề:** Điều gì xảy ra khi một hàm trả về con trỏ trỏ tới một biến cục bộ của nó? Theo lý thuyết Stack, khi hàm kết thúc, Stack Frame bị xóa, con trỏ đó sẽ trỏ vào vùng nhớ rác (dangling pointer).
    
- **Giải pháp của Go:** Trình biên dịch thực hiện **Escape Analysis** (Phân tích thoát).
    
    - Nếu compiler thấy một biến được "chia sẻ lên" (trả về địa chỉ ra khỏi hàm tạo ra nó), nó sẽ **không đặt biến đó lên Stack**.
        
    - Thay vào đó, biến sẽ được đưa lên **Heap** (vùng nhớ động).
        

**Ví dụ:**

```go
// Hàm này trả về con trỏ *user
func createUserV2() *user {
    // Biến u được khai báo cục bộ
    u := user{name: "Bill", email: "bill@ardanlabs.com"}

    // Trả về địa chỉ của u.
    // Go phát hiện u được "share up", nên u sẽ "Escape to Heap" (Thoát ra Heap).
    // Dù hàm createUserV2 kết thúc, u vẫn tồn tại trên Heap.
    return &u
}
```

#### 5. Kết luận quan trọng

1. **Stack rất nhanh:** Dữ liệu trên Stack không gây áp lực cho Garbage Collector (GC).
    
2. **Heap tốn kém:** Dữ liệu trên Heap cần GC dọn dẹp, gây tốn tài nguyên hơn.
    
3. **Quy tắc:**
    
    - **Chia sẻ xuống (Sharing Down):** Thường vẫn ở trên Stack.
        
    - **Chia sẻ lên (Sharing Up):** Chắc chắn sẽ thoát ra Heap (Escape to Heap).
        
4. **Lời khuyên:** Đừng quá lạm dụng con trỏ chỉ để "tiết kiệm bộ nhớ" trừ khi cấu trúc dữ liệu rất lớn. Việc copy giá trị trên Stack thường nhanh hơn chi phí quản lý bộ nhớ trên Heap.

**Escape Analysis** (Phân tích sự thoát ly) là một kỹ thuật tối ưu hóa được trình biên dịch (compiler) sử dụng để xác định vị trí lưu trữ dữ liệu của một biến trong bộ nhớ: nên đặt trên **Stack** (Ngăn xếp) hay **Heap** (Đống).

Mục tiêu chính của nó là giảm tải cho bộ thu gom rác (Garbage Collector - GC) và tăng hiệu năng chương trình bằng cách ưu tiên cấp phát trên Stack bất cứ khi nào có thể.

Dưới đây là giải thích chi tiết về cơ chế này:

### 1. Cơ chế hoạt động cốt lõi

Trình biên dịch sẽ quét mã nguồn của bạn để xem phạm vi sử dụng (scope) của một biến/đối tượng:

- **Không thoát ly (Does not escape):** Nếu một biến được khai báo trong một hàm và **chỉ** được sử dụng trong hàm đó (không được trả về, không gán cho biến toàn cục, không chia sẻ sang thread khác), trình biên dịch xác định nó an toàn để đặt trên **Stack**.
    
- **Thoát ly (Escapes):** Nếu biến đó được tham chiếu ra bên ngoài hàm (ví dụ: hàm trả về con trỏ tới biến đó), trình biên dịch buộc phải cấp phát nó trên **Heap** để dữ liệu vẫn tồn tại sau khi hàm kết thúc.
    

### 2. Stack vs. Heap: Tại sao điều này quan trọng?

Để hiểu giá trị của Escape Analysis, cần so sánh hai vùng nhớ:

|**Đặc điểm**|**Stack (Ngăn xếp)**|**Heap (Đống)**|
|---|---|---|
|**Tốc độ cấp phát**|Rất nhanh (chỉ cần di chuyển con trỏ stack).|Chậm hơn (cần tìm block nhớ trống).|
|**Dọn dẹp**|Tự động dọn dẹp ngay khi hàm kết thúc.|Cần Garbage Collector (GC) quét và xóa.|
|**Chi phí**|Rất rẻ.|Đắt đỏ (gây áp lực lên CPU/RAM).|

**Kết luận:** Escape Analysis cố gắng đưa càng nhiều biến vào Stack càng tốt để "né" việc sử dụng Heap và GC.

### 3. Ví dụ minh họa

Hãy xem xét hai trường hợp (sử dụng cú pháp giả lập giống Go/C):

#### Trường hợp 1: Không thoát ly (Ở lại Stack)

```go
func main() {
   tinhToan()
}

func tinhToan() {
   // Biến x được tạo ra, sử dụng, và kết thúc chỉ trong hàm này.
   // Trình biên dịch sẽ cấp phát x trên STACK.
   x := 10
   println(x)
}
```

#### Trường hợp 2: Bị thoát ly (Đẩy lên Heap)

```go
func main() {
   ketQua := taoGiaTri()
   // ketQua ở đây tham chiếu tới vùng nhớ được tạo trong taoGiaTri
   println(*ketQua)
}

func taoGiaTri() *int {
   x := 10
   // Hàm trả về "địa chỉ" (con trỏ) của x ra bên ngoài.
   // Nếu x nằm trên Stack, nó sẽ bị xóa khi hàm kết thúc -> Lỗi.
   // Do đó, trình biên dịch buộc phải đưa x lên HEAP.
   return &x
}
```

### 4. Lợi ích của Escape Analysis

1. **Giảm áp lực cho Garbage Collector:** Vì các biến trên Stack tự động hủy, GC không cần tốn công theo dõi và dọn dẹp chúng. Điều này giảm thiểu tình trạng "Stop-the-world" (ngưng trệ hệ thống để dọn rác).
    
2. **Tăng tốc độ cấp phát:** Cấp phát trên Stack chỉ mất vài chu kỳ CPU, trong khi Heap tốn kém hơn nhiều.
    
3. **Tối ưu hóa Cache CPU:** Dữ liệu trên Stack thường nằm liền kề nhau trong bộ nhớ, giúp CPU cache hoạt động hiệu quả hơn (tăng tỉ lệ cache hit).
    

### 5. Khi nào bạn cần quan tâm?

Hầu hết thời gian, trình biên dịch (như trong Java, Go, .NET) tự động làm việc này. Tuy nhiên, nếu bạn đang viết code hiệu năng cao (high-performance), bạn nên lưu ý:

- Hạn chế truyền hoặc trả về các con trỏ (pointers) nếu không cần thiết.
    
- Hiểu rằng việc chia sẻ biến giữa các goroutine/thread thường sẽ đẩy biến đó lên Heap.
    
