---
title: "Security - SQL Injection Prevention"
tags:
  - "security"
  - "sqlinjection"
  - "gorm"
  - "golang"
  - "database"
  - "owasp"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "SQL Injection (SQLi) xảy ra khi ứng dụng nhầm lẫn giữa Dữ liệu (Data) và Mã lệnh (Code)."
---

## 1. Bản chất: Code vs. Data

SQL Injection (SQLi) xảy ra khi ứng dụng **nhầm lẫn giữa Dữ liệu (Data) và Mã lệnh (Code)**.

Hacker lợi dụng việc nối chuỗi (String Concatenation) để chèn thêm các đoạn mã SQL độc hại, lừa Database thực thi những việc không được phép (Xóa bảng, Dump dữ liệu).

**Ví dụ kinh điển:**

- Query gốc: `SELECT * FROM users WHERE name = '` + **userInput** + `';`
    
- Input của Hacker: `' OR '1'='1`
    
- Query thực thi: `SELECT * FROM users WHERE name = '' OR '1'='1';` -> **Luôn đúng (True)** -> Hacker đăng nhập thành công mà không cần password.
    

---

## 2. Giải pháp: Parameterized Queries (Prepared Statements)

Đây là "viên đạn bạc" để giết chết SQLi.

Thay vì nối chuỗi, ta gửi câu SQL với các "chỗ trống" (Placeholders - `?` hoặc `$1`) cho Database trước. Sau đó mới gửi dữ liệu điền vào chỗ trống đó.

> [!SUMMARY] Cơ chế bảo vệ
> 
> Database sẽ coi toàn bộ dữ liệu người dùng gửi lên là **Chuỗi văn bản thuần túy (Literal String)**, không bao giờ biên dịch nó thành mã thực thi.
> 
> Dù Hacker gửi `' OR 1=1`, Database chỉ tìm user có tên là `"' OR 1=1"`.

---

## 3. GORM Security: Đúng và Sai

GORM mặc định rất an toàn nếu bạn dùng đúng API chuẩn. Nhưng nếu bạn dùng sai cách (đặc biệt là `fmt.Sprintf`), bạn sẽ mở toang cửa cho Hacker.

### A. Cách SAI (Vulnerable Code)

Tuyệt đối tránh sử dụng `fmt.Sprintf` hoặc cộng chuỗi (+) để tạo câu SQL.

Go

```
func GetUserBad(db *gorm.DB, username string) {
    var user User
    // ❌ NGUY HIỂM: Nối chuỗi trực tiếp
    // Nếu username = "admin'; DROP TABLE users; --"
    // -> Bảng users sẽ bay màu.
    query := fmt.Sprintf("name = '%s'", username)
    db.Where(query).First(&user)
}
```

### B. Cách ĐÚNG (Safe Code)

Sử dụng `?` (Positional Argument) hoặc Named Argument. GORM sẽ tự động chuyển đổi thành Parameterized Query.

Go

```
func GetUserGood(db *gorm.DB, username string) {
    var user User
    
    // ✅ AN TOÀN: Sử dụng ? làm placeholder
    db.Where("name = ?", username).First(&user)
    
    // ✅ AN TOÀN: Sử dụng Struct (GORM tự parse)
    db.Where(&User{Name: username}).First(&user)
    
    // ✅ AN TOÀN: Sử dụng Map
    db.Where(map[string]interface{}{"name": username}).First(&user)
}
```

---

## 4. Những cạm bẫy trong GORM (Hidden Dangers)

Một số hàm Raw SQL trong GORM cần đặc biệt chú ý.

### 1. `db.Raw()` và `db.Exec()`

Hai hàm này cho phép chạy SQL thô. Nếu bạn lười và nối chuỗi ở đây -> Dính SQLi ngay.

Go

```
// ❌ SAI
db.Exec("UPDATE users SET name = '" + newName + "' WHERE id = 1")

// ✅ ĐÚNG
db.Exec("UPDATE users SET name = ? WHERE id = ?", newName, 1)
```

### 2. SQL Injection qua `ORDER BY`

Đây là trường hợp Parameterized Query **KHÔNG** hoạt động. Database **không cho phép** tham số hóa tên bảng hoặc tên cột (Identifier).

- _Sai:_ `db.Order("?").Find(&users, sortColumn)` -> Lỗi cú pháp SQL.
    
- _Nguy hiểm:_ `db.Order(userInput).Find(&users)` -> Hacker có thể inject `id; DROP TABLE users`.
    

**Giải pháp: Whitelisting (Danh sách trắng)**

Go

```
func GetUsers(db *gorm.DB, sortCol string) {
    // Chỉ cho phép sắp xếp theo các cột quy định
    validColumns := map[string]bool{
        "name": true, 
        "created_at": true,
    }
    
    if !validColumns[sortCol] {
        sortCol = "created_at" // Fallback về mặc định nếu input láo
    }
    
    // Sau khi validate mới dám nối chuỗi
    db.Order(sortCol).Find(&users) 
}
```

---

## 5. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Tại sao không dùng Regular Expression (Regex) để lọc ký tự lạ (Sanitization) thay vì Parameterized Query?
> 
> **A:**
> 
> Đó là cách tiếp cận "Mèo đuổi chuột" và **không bao giờ an toàn tuyệt đối**.
> 
> Hacker luôn tìm ra cách lách luật (dùng encoding khác, dùng ký tự Unicode lạ...).
> 
> Parameterized Query giải quyết tận gốc vấn đề ở tầng Database Driver, không phải ở tầng lọc input.

> [!QUESTION] Q: `LIKE` query trong GORM xử lý thế nào cho an toàn?
> 
> **A:**
> 
> Vẫn dùng `?` như thường. Lưu ý là dấu `%` phải nằm trong tham số gửi đi, không nằm trong chuỗi SQL cố định.
> 
> Go
> 
> ```
> // ✅ ĐÚNG
> keyword := "%" + userInput + "%"
> db.Where("name LIKE ?", keyword).Find(&users)
> ```

> [!QUESTION] Q: Stored Procedures có chống được SQL Injection không?
> 
> **A:**
> 
> **Có và Không.**
> 
> - _Có:_ Nếu Stored Proc dùng tham số đầu vào chuẩn.
>     
> - _Không:_ Nếu bên trong Stored Proc lại dùng `EXECUTE IMMEDIATE` để nối chuỗi SQL động (Dynamic SQL) từ tham số đầu vào. Lúc này SQLi vẫn xảy ra ngay trong lòng DB.
>     

---

### Mẹo cuối cùng cho Developer:

> Luôn bật chế độ **Log Mode** của GORM khi Dev để nhìn thấy câu SQL thực tế được sinh ra.
> 
> `db.Debug().Where(...)` -> Sẽ thấy rõ `SELECT * FROM users WHERE name = 'abc'` (đã escape) hay `name = '' OR 1=1'` (chưa escape).