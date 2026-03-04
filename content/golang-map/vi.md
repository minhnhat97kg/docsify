---
title: "Golang - Map Internals"
tags:
  - "golang"
  - "backend"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Dưới đây là tóm tắt bài viết của Dave Cheney dưới định dạng Obsidian để bạn có thể copy trực tiếp vào vault của mình."
---

Dưới đây là tóm tắt bài viết của Dave Cheney dưới định dạng Obsidian để bạn có thể copy trực tiếp vào vault của mình.

---

Markdown

```markdown
---
tags:
  - golang
  - internal
  - performance
  - data-structure
source: https://dave.cheney.net/2018/05/29/how-the-go-runtime-implements-maps-efficiently-without-generics
author: [[Dave Cheney]]
---

# Tóm tắt: How the Go runtime implements maps efficiently without generics

Bài viết giải thích cơ chế bên dưới của [[Go Map]] trước phiên bản 1.18 (khi chưa có Generics), cách Go cân bằng giữa hiệu năng (như C++) và sự đơn giản khi biên dịch (tránh code bloat).

## 1. Vấn đề của Map khi thiếu Generics
Tại thời điểm viết bài, Go không có generics. Có hai cách tiếp cận phổ biến mà các ngôn ngữ khác sử dụng:
* **Cách của C++ (`std::map`):** Sử dụng Templates. Mỗi khi khai báo `map<int, string>`, trình biên dịch tạo ra một bản copy code riêng biệt cho cặp kiểu này.
    * *Ưu điểm:* Rất nhanh (inline code).
    * *Nhược điểm:* Tăng thời gian biên dịch và kích thước file binary (code bloat).
* **Cách của Java (`HashMap`):** Sử dụng Boxing (mọi thứ là `Object`).
    * *Ưu điểm:* Chỉ cần viết code map một lần.
    * *Nhược điểm:* Chậm do phải cấp phát bộ nhớ động cho wrapper object, tăng áp lực lên [[Garbage Collector|GC]] và cache CPU kém.

## 2. Giải pháp của Go: "Compile-time rewriting"
Go chọn cách tiếp cận lai (hybrid):
* Map trong Go thực chất là **syntactic sugar**.
* Trình biên dịch (Compiler) sẽ viết lại các thao tác map thành các lệnh gọi hàm runtime.

Ví dụ, câu lệnh:
```go
val := m[key]
```

Sẽ được compiler viết lại thành một lời gọi hàm runtime giống C:

Go

```go
runtime.mapaccess1(mapType, m, &key)
```

- `mapType`: Là một cấu trúc dữ liệu mô tả kiểu của Key và Value (kích thước, cách hash, cách so sánh...). Điều này giúp Runtime xử lý dữ liệu dưới dạng con trỏ thô (`unsafe.Pointer`) nhưng vẫn an toàn vì Compiler đã kiểm tra kiểu trước đó.
    

## 3. Cấu trúc dữ liệu bên dưới

### Header (`hmap`)

Là struct quản lý metadata của map:

- Số lượng phần tử (`count`).
    
- Số lượng bucket (dưới dạng logarit cơ số 2, biến `B`).
    
- Hash seed (để tránh tấn công Hash DoS).
    

### Buckets (`bmap`)

Dữ liệu thực tế được lưu trong các **Buckets**.

- Mỗi bucket chứa tối đa **8 keys** và **8 values**.
    
- Khi bucket đầy, nó sẽ nối (link) tới một "overflow bucket".
    

> [!NOTE] Memory Layout tối ưu
> 
> Thay vì lưu xen kẽ `Key/Value` (như `K1, V1, K2, V2`...), Go lưu **tách biệt** để tối ưu bộ nhớ (tránh padding alignment):
> 
> `K1, K2, ..., K8` | `V1, V2, ..., V8`
> 
> -> Điều này giúp loại bỏ các khoảng trống (padding) không cần thiết nếu kích thước Key và Value khác nhau (ví dụ: `map[int64]int8`).

## 4. Hash Function

Go không dùng một hàm hash cố định.

- Runtime sẽ chọn thuật toán hash phù hợp dựa trên phần cứng (ví dụ: dùng chỉ thị AES trên CPU hỗ trợ để hash nhanh hơn).
    
- Hàm hash và hàm so sánh (equality) được lưu trong `mapType` truyền vào runtime.
    

## 5. Kết luận

- Map trong Go nhanh ngang ngửa C++ (custom code generation) nhưng lại gọn nhẹ như Java (single implementation).
    
- Đánh đổi là độ phức tạp nằm ở Compiler và Runtime thay vì người dùng.
    

---

**Liên kết:**

- [[Golang Memory Model]]
    
- [[Hash Table Implementation]]
    
- [[Compiler Design]]