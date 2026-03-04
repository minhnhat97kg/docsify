---
title: "Golang - SOLID Design Principles"
tags:
  - "golang"
  - "solid"
  - "architecture"
  - "design-patterns"
  - "refactoring"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Go không phải là ngôn ngữ hướng đối tượng (OOP) theo kiểu Java/C#."
---

## 1. Context: Go khác gì OOP truyền thống?

Go không phải là ngôn ngữ hướng đối tượng (OOP) theo kiểu Java/C#.

- Không có `class`, chỉ có `struct`.
    
- Không có kế thừa (`extends`), chỉ có `composition` (embedding).
    
- Không có `implements`, interface được thỏa mãn ngầm định (implicitly).
    

Vì vậy, cách áp dụng SOLID trong Go sẽ linh hoạt và "thực dụng" hơn.

---

## 2. S - Single Responsibility Principle (SRP)

> **"A class should have one, and only one, reason to change."**

Trong Go, nguyên lý này áp dụng cho **Function**, **Type**, và quan trọng nhất là **Package**.

### Bad Practice: `package utils`

Tạo một package tên là `utils` hoặc `common` là vi phạm SRP nghiêm trọng nhất trong Go.

- Nó trở thành cái "bãi rác" chứa đủ thứ: Xử lý chuỗi, Kết nối DB, Tính toán thuế...
    
- Khi bạn sửa hàm xử lý chuỗi, bạn phải re-compile cả những phần code dùng DB (dù chúng chả liên quan).
    

### Good Practice: Small Packages

Chia nhỏ package theo **Business Domain**.

- `package user`: Chỉ lo việc User.
    
- `package tax`: Chỉ lo tính thuế.
    
- `package db`: Chỉ lo kết nối DB.
    

**Code Example:**

Go

```
// Tệ: Hàm làm quá nhiều việc
func ProcessPayment(u User) {
    // 1. Validate
    if u.Balance < 10 { ... }
    // 2. Trừ tiền DB
    db.Exec("UPDATE ...")
    // 3. Gửi Email
    smtp.SendMail(...)
}

// Tốt: Tách nhỏ (Decoupling)
func ProcessPayment(u User, notifier Notifier, repo Repository) {
    // Chỉ điều phối, không thực thi chi tiết
    repo.DeductBalance(u.ID, 10)
    notifier.Notify(u.Email, "Paid")
}
```

---

## 3. O - Open/Closed Principle (OCP)

> **"Software entities should be open for extension, but closed for modification."**

Trong Go, OCP đạt được thông qua **Embedding (Composition)** và **Interface**.

Bạn muốn thêm tính năng mới? Đừng sửa code cũ. Hãy tạo một Type mới nhúng Type cũ hoặc implement cùng Interface.

### Ví dụ: Hệ thống thanh toán

Bạn có `CashPayment`. Sếp bảo thêm `CardPayment`.

**Cách sai (Sửa code cũ):**

Go

```
func Pay(method string, amount int) {
    if method == "cash" { ... }
    else if method == "card" { ... } // Sửa hàm này -> Rủi ro bug
}
```

**Cách đúng (Dùng Interface):**

Go

```
type PaymentMethod interface {
    Pay(amount int) error
}

type Cash struct {}
func (c Cash) Pay(amount int) error { /*...*/ }

type Card struct {}
func (c Card) Pay(amount int) error { /*...*/ }

// Hàm này không bao giờ cần sửa nữa, dù có thêm Crypto/Visa/Momo
func Process(p PaymentMethod, amount int) {
    p.Pay(amount)
}
```

---

## 4. L - Liskov Substitution Principle (LSP)

> **"Subtypes must be substitutable for their base types."**

Trong Go không có kế thừa, nên LSP nói về **Hợp đồng của Interface (Interface Contract)**.

Nếu một hàm nhận vào `io.Reader`, thì dù bạn truyền vào `os.File` (File thật) hay `bytes.Buffer` (RAM), nó phải hoạt động đúng mà không crash.

**Quy tắc:** Đừng hứa một đằng làm một nẻo. Nếu interface method trả về `error`, thì implementation không được phép `panic`.

---

## 5. I - Interface Segregation Principle (ISP)

> **"Clients should not be forced to depend on methods they do not use."**

Đây là nguyên lý quan trọng nhất trong Go.

**Rule of Thumb:** Interface càng nhỏ càng tốt. Tốt nhất là 1-2 methods.

### Go Philosophy: "The consumer defines the interface"

Khác với Java (Người tạo class định nghĩa interface to đùng), trong Go, **người dùng** định nghĩa interface họ cần.

**Bad Practice (Interface khổng lồ):**

Go

```
// Interface này bắt người dùng phải implement cả 3 hàm
// Dù tôi chỉ muốn lưu User, tôi vẫn phải viết hàm Delete/Get thừa thãi.
type UserStore interface {
    Save(u User) error
    Delete(id int) error
    Get(id int) (User, error)
}
```

**Good Practice (Interface nhỏ):**

Go

```
// Tôi chỉ cần Save, tôi định nghĩa interface này ngay tại chỗ tôi dùng
type UserSaver interface {
    Save(u User) error
}

func Register(s UserSaver, u User) {
    s.Save(u)
}
```

_Ví dụ kinh điển:_ `io.Reader` (chỉ có 1 hàm `Read`), `io.Writer` (chỉ có 1 hàm `Write`). Nhờ nó nhỏ nên hàng nghìn thư viện Go ghép nối được với nhau.

---

## 6. D - Dependency Inversion Principle (DIP)

> **"High-level modules should not depend on low-level modules. Both should depend on abstractions."**

Trong Go, DIP được tóm gọn bằng câu thần chú:

**"Accept Interfaces, Return Structs"** (Nhận đầu vào là Interface, Trả đầu ra là Struct).

- **Tại sao nhận Interface?** Để dễ Unit Test (Mocking) và dễ thay đổi Implementation (OCP).
    
- **Tại sao trả về Struct?** Để người dùng không bị buộc phải dùng interface do bạn định nghĩa (họ có thể tự định nghĩa interface hẹp hơn theo ISP).
    

### Code Example: Clean Architecture

Go

```
// --- Low Level (Database) ---
type PostgresDB struct {}
func (db PostgresDB) Query() {} // Concrete implementation

// --- High Level (Business Logic) ---

// 1. Định nghĩa cái mình cần (Abstraction)
type DataProvider interface {
    Query()
}

// 2. Inject dependency vào (Dependency Injection)
type Service struct {
    db DataProvider // Service không phụ thuộc PostgresDB cụ thể
}

func NewService(db DataProvider) *Service {
    return &Service{db: db}
}
```

---

## 7. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Tại sao Go Developer hay nói "Accept Interfaces, Return Structs"?
> 
> **A:**
> 
> - **Accept Interfaces:** Giúp hàm của bạn linh hoạt. Ví dụ hàm nhận `io.Writer` có thể ghi ra File, ra HTTP Response, hoặc ra Console mà không cần sửa code. Đồng thời dễ Mock khi test.
>     
> - **Return Structs:** Nếu bạn trả về Interface, bạn đang ép người dùng phải phụ thuộc vào interface đó. Trả về Struct giúp người dùng tự do định nghĩa interface (ISP) phù hợp với nhu cầu của họ ở phía calling code. Trừ trường hợp Factory Pattern thì mới trả về Interface.
>     

> [!QUESTION] Q: Embedding trong Go có phải là Kế thừa (Inheritance) không?
> 
> **A:**
> 
> **Không.** Embedding là **Composition (Thành phần)**.
> 
> Dù bạn có thể gọi method của struct con trực tiếp (`car.Engine.Start()` -> `car.Start()`), nhưng `Car` không phải là `Engine`. Bạn không thể gán biến kiểu `Car` vào biến kiểu `Engine` (trừ khi dùng Interface).
> 
> Embedding giúp tái sử dụng code (Reuse) chứ không tạo ra phân cấp kiểu (Type Hierarchy).