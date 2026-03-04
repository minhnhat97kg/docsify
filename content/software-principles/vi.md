---
title: "Software Principles"
tags:
  - "clean-code"
  - "architecture"
  - "refactoring"
  - "principles"
  - "golang"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Nguyên lý này thường bị hiểu sai nhất. Mọi người nghĩ DRY đơn giản là \"Không được copy-paste code\"."
---

## 1. DRY (Don't Repeat Yourself) - Không lặp lại chính mình

Nguyên lý này thường bị hiểu sai nhất. Mọi người nghĩ DRY đơn giản là "Không được copy-paste code".

> [!QUOTE] Định nghĩa chuẩn (The Pragmatic Programmer)
> 
> "Mọi kiến thức phải có một hình diện duy nhất, rõ ràng và đáng tin cậy trong hệ thống."
> 
> (Every piece of knowledge must have a single, unambiguous, authoritative representation within a system).

### Hiểu lầm tai hại: Code giống nhau != Logic giống nhau

Bạn thấy 2 hàm `ValidateUser` và `ValidateAdmin` có 5 dòng code giống hệt nhau. Bạn gộp nó lại thành `ValidatePerson`.

- **Vấn đề:** 1 tháng sau, logic validate Admin thay đổi (cần check thêm IP), còn User thì không.
    
- **Hậu quả:** Bạn phải thêm `if type == "admin"` vào hàm chung. Hàm chung trở nên phức tạp, chằng chịt `if/else`. Đây gọi là **Coupling (Sự phụ thuộc)**.
    

**Nguyên tắc Senior:**

> **"Duplication is far cheaper than the wrong abstraction."** (Lặp lại code còn rẻ hơn nhiều so với trừu tượng hóa sai - Sandi Metz).

Nếu 2 đoạn code nhìn giống nhau nhưng **lý do thay đổi (Reason to change)** khác nhau -> **Đừng gộp**. Hãy để chúng trùng lặp (WET - Write Everything Twice).

---

## 2. KISS (Keep It Simple, Stupid) - Giữ cho nó đơn giản

Nguyên lý này tôn thờ sự đơn giản. Code phức tạp là kẻ thù của độ tin cậy.

> [!SUMMARY] Tư duy KISS
> 
> - Code được ĐỌC nhiều hơn VIẾT gấp 10 lần.
>     
> - Một giải pháp "ngu ngốc" (stupid) nhưng dễ hiểu luôn tốt hơn một giải pháp "thông minh" (clever) nhưng ai nhìn vào cũng sợ.
>     

### Ví dụ trong Golang

Golang là ngôn ngữ sinh ra để phục vụ KISS.

**Vi phạm KISS (Over-engineering):**

Sử dụng Reflection hoặc Interface quá mức cần thiết để làm code "linh hoạt".

Go

```
// Phức tạp không cần thiết
type StringProcessor interface {
    Process(s string) string
}
func ProcessData(p StringProcessor, data string) { ... }
```

**Tuân thủ KISS:**

Go

```
// Đơn giản, trực diện
func ProcessData(data string) string {
    return strings.ToUpper(data)
}
```

### Tại sao Golang bắt viết `if err != nil` liên tục?

Nhiều người chê Go vi phạm DRY vì phải copy-paste đoạn check lỗi này khắp nơi.

Nhưng đó là **KISS**.

- Nó giúp luồng code rõ ràng (Explicit).
    
- Không giấu lỗi vào trong các block `try-catch` ma thuật (Implicit).
    
- Đọc code là biết ngay chỗ nào có thể lỗi.
    

---

## 3. Chiến thuật áp dụng: Rule of Three

Làm sao biết khi nào nên DRY, khi nào nên KISS? Hãy dùng **Quy tắc số 3**.

1. **Lần 1:** Viết code giải quyết vấn đề. (Chấp nhận hardcode).
    
2. **Lần 2:** Bạn gặp lại vấn đề đó. Copy đoạn code cũ sang và sửa lại. (Chấp nhận trùng lặp - WET).
    
3. **Lần 3:** Bạn gặp lại nó lần nữa. Lúc này bạn đã đủ dữ kiện để biết những gì giống nhau, những gì khác nhau. -> **Refactor thành hàm chung (Abstraction).**
    

-> Đừng vội vã tạo thư viện chung (`common` package) ngay từ lần đầu tiên.

---

## 4. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Bạn chọn code lặp lại (Duplication) hay code bị phụ thuộc (Coupling)?
> 
> **A:**
> 
> Tôi sẽ chọn **Duplication**.
> 
> Vì gỡ bỏ code lặp lại rất dễ (chỉ cần xóa hoặc gom lại sau).
> 
> Nhưng gỡ bỏ sự phụ thuộc (Coupling) do trừu tượng hóa sai (Wrong Abstraction) là cực kỳ đau đớn, vì nó ảnh hưởng đến nhiều phần của hệ thống cùng lúc.

> [!QUESTION] Q: Microservices có cần tuân thủ DRY không?
> 
> **A:**
> 
> **Cần và Không.**
> 
> - _Trong nội bộ 1 service:_ Cần DRY.
>     
> - _Giữa các service:_ **Không nên DRY.**
>     
>     Nếu bạn tạo một thư viện `SharedModels` dùng chung cho Service A và Service B. Khi Service A cần sửa Model, Service B buộc phải update theo (Coupling).
>     
>     Trong Microservices, chấp nhận lặp lại code (Copy struct User ở cả 2 service) để đảm bảo tính **Decoupling (Độc lập)**.
>     

---

**Next Step:** Bạn muốn tìm hiểu về **YAGNI (You Aren't Gonna Need It)** - nguyên lý bổ trợ hoàn hảo cho KISS, hay chuyển sang chủ đề **Testing Strategies** (Unit vs Integration Test)?

### 1. YAGNI (You Aren't Gonna Need It) - Bạn sẽ không cần nó đâu

> [!QUOTE] Định nghĩa **"Đừng viết code cho tương lai. Chỉ viết code cho hiện tại."** Đừng thêm chức năng chỉ vì bạn nghĩ: "Sau này _có thể_ mình sẽ cần đến nó".

**Vấn đề:** Bạn đang viết hàm `SaveUser()`. Bạn nghĩ: "À, sau này chắc cần `DeleteUser`, `UpdateUser`, và cả `ExportToExcel` nữa". Thế là bạn hì hục viết hết các interface đó.

- **Hậu quả:** 3 tháng sau, requirements thay đổi. Sếp bảo không cần Excel nữa mà cần PDF. Code cũ vứt đi -> Lãng phí thời gian (Waste). Code thừa đó còn gây nhiễu, phải viết test, và có thể chứa bug.
    

**Cách áp dụng:**

- Chỉ implement những gì **cần thiết ngay lúc này** để tính năng chạy được.
    
- Tương lai là thứ không đoán định được. Khi nào cần thì hãy thêm (Just-in-Time implementation).
    

---

### 2. Law of Demeter (LoD) - Nguyên lý "Ít kiến thức nhất"

Còn gọi là: **"Don't talk to strangers" (Đừng nói chuyện với người lạ).**

> [!SUMMARY] Quy tắc Một đối tượng A chỉ nên gọi các phương thức của:
> 
> 1. Chính nó.
>     
> 2. Các tham số truyền vào nó.
>     
> 3. Các đối tượng mà nó trực tiếp tạo ra. -> **Cấm gọi bắc cầu quá xa.**
>     

**Ví dụ (Golang):** Bạn muốn lấy tên thành phố của khách hàng từ đơn hàng.

- **Vi phạm (Train Wreck - Tàu hỏa đâm nhau):**
    
    Go
    
    ```
    // Order biết quá nhiều về cấu trúc bên trong của Customer và Address
    city := order.Customer.Address.City 
    ```
    
    _Tại sao tệ?_ Nếu `Customer` đổi cấu trúc (không dùng `Address` struct nữa mà dùng `Location`), code này sẽ gãy.
    
- **Tuân thủ:**
    
    Go
    
    ```
    // Order cung cấp phương thức, giấu chi tiết bên trong
    city := order.GetCustomerCity()
    ```
    

---

### 3. SoC (Separation of Concerns) - Phân tách mối quan tâm

Đây là nền tảng của mọi kiến trúc hiện đại (MVC, Hexagonal, Microservices).

**Nguyên lý:** Chia hệ thống thành các phần riêng biệt, mỗi phần giải quyết một vấn đề cụ thể và không chồng chéo lên nhau.

- **HTML:** Lo việc hiển thị cấu trúc.
    
- **CSS:** Lo việc làm đẹp.
    
- **Javascript:** Lo hành vi.
    
- **SQL:** Lo dữ liệu.
    

**Trong Backend:**

- Đừng viết câu lệnh SQL (`SELECT *...`) ngay trong API Handler (Controller).
    
- Đừng để Business Logic nằm trong file HTML Template.
    
- -> Hãy tách ra: `Handler` chỉ parse request. `Service` tính toán logic. `Repository` gọi SQL.
    

---

### 4. Fail Fast (Thất bại nhanh)

> [!QUOTE] Định nghĩa Nếu có lỗi xảy ra, hãy báo lỗi và dừng ngay lập tức. Đừng cố gắng "lấp liếm" để chạy tiếp.

**Ví dụ:** Hàm khởi động ứng dụng cần đọc file Config. File bị thiếu.

- **Fail Slow (Nguy hiểm):** Code log ra một dòng warning: "Không thấy config, dùng default", rồi vẫn khởi động server. -> Sau này khi chạy thật, kết nối vào DB localhost (default) thay vì DB Production -> **Thảm họa**.
    
- **Fail Fast (An toàn):**
    
    Go
    
    ```
    func LoadConfig() {
        if fileMissing {
            panic("Config file not found! Application cannot start.")
        }
    }
    ```
    
    -> Ứng dụng sập ngay lúc khởi động (Crash Loop). Dev/DevOps biết ngay để sửa. Thà chết ngay còn hơn sống "dặt dẹo" gây lỗi ngầm.
    

---

### 5. Bonus: The Boy Scout Rule (Quy tắc Hướng đạo sinh)

> **"Always leave the campground cleaner than you found it."** (Luôn trả lại khu cắm trại sạch hơn lúc bạn mới đến).

**Áp dụng vào Code:**

- Bạn vào sửa một file cũ để fix bug.
    
- Bạn thấy biến đặt tên sai (`var x int`), hàm quá dài, comment thừa thãi.
    
- **Nhiệm vụ:** Fix bug xong, tiện tay đổi tên biến `x` thành `userCount`, xóa comment thừa.
    
- **Kết quả:** Codebase sạch dần theo thời gian thay vì mục nát dần (Technical Debt). Đừng đợi đến lúc "Refactoring Sprint" mới dọn dẹp (vì lúc đó sẽ không bao giờ đến).
    

---

### Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Sự khác biệt giữa YAGNI và KISS là gì? **A:**
> 
> - **YAGNI (Cái gì):** Nói về **Tính năng**. Đừng làm tính năng thừa. (Bớt việc).
>     
> - **KISS (Như thế nào):** Nói về **Giải pháp**. Khi làm tính năng đó, hãy chọn cách code đơn giản nhất, dễ hiểu nhất. (Làm việc một cách thông minh).
>     

> [!QUESTION] Q: Fail Fast có mâu thuẫn với tính ổn định (Robustness) không? **A:** Không. Fail Fast ở tầng **Backend/System** giúp phát hiện lỗi cấu hình/logic sớm để sửa. Tuy nhiên, ở tầng **User Interface**, ta cần Fail Safe (An toàn). Nếu một nút bấm bị lỗi, không được để crash cả trang web, mà chỉ hiện thông báo lỗi nhẹ nhàng cho User. 
### 6. CAP Theorem - Định lý "Tam giác bất khả thi"

> [!SUMMARY] Định lý phát biểu Trong một hệ thống phân tán (Distributed System) lưu trữ dữ liệu, bạn **chỉ có thể chọn 2 trong 3** thuộc tính sau:
> 
> 1. **C - Consistency (Tính nhất quán):** Mọi lần đọc đều trả về dữ liệu mới nhất hoặc trả về lỗi. (Tất cả các node nhìn thấy cùng một dữ liệu tại cùng một thời điểm).
>     
> 2. **A - Availability (Tính sẵn sàng):** Mọi request đều nhận được phản hồi (không bị lỗi), nhưng không đảm bảo dữ liệu là mới nhất.
>     
> 3. **P - Partition Tolerance (Khả năng chịu lỗi phân vùng):** Hệ thống vẫn hoạt động dù đường truyền mạng giữa các node bị đứt (gãy).
>     

---

### Sự thật tàn khốc: Bạn không có quyền chọn "CA"

Trong thế giới Microservices/Distributed Systems, mạng **luôn luôn** không đáng tin cậy. Dây cáp có thể đứt, Switch có thể hỏng. => **P (Partition Tolerance) là BẮT BUỘC.**

Vì vậy, thực tế bạn chỉ được chọn giữa **CP** hoặc **AP**:

#### 1. Chọn CP (Consistency + Partition Tolerance) - "Thà chết chứ không sai"

- **Kịch bản:** Hệ thống Ngân hàng (Core Banking).
    
- **Tình huống:** Node A (Sài Gòn) mất kết nối với Node B (Hà Nội).
    
- **Hành động:** Nếu User rút tiền ở Sài Gòn, hệ thống sẽ **từ chối giao dịch (trả về Error)** hoặc treo (Timeout) cho đến khi mạng nối lại.
    
- **Lý do:** Không thể để User rút tiền ở Sài Gòn rồi lại rút tiếp ở Hà Nội (Double Spending) khi 2 nơi chưa đồng bộ số dư.
    
- **Database:** HBase, MongoDB (mặc định), Redis (cấu hình strong), RDBMS Cluster.
    

#### 2. Chọn AP (Availability + Partition Tolerance) - "Thà sai chứ không chết"

- **Kịch bản:** Mạng xã hội (Facebook, TikTok), Giỏ hàng Tiki/Shopee.
    
- **Tình huống:** Node A mất kết nối với Node B.
    
- **Hành động:**
    
    - User post bài ở Sài Gòn -> Node A ghi nhận ngay (OK).
        
    - User ở Hà Nội (kết nối vào Node B) -> Chưa thấy bài post đó (Data cũ). -> **Chấp nhận được.**
        
    - Sau khi mạng nối lại, Node A sẽ đồng bộ sang Node B (Eventual Consistency).
        
- **Lý do:** Trải nghiệm người dùng quan trọng hơn. Không ai bỏ Facebook chỉ vì Newfeed cập nhật chậm 2 giây, nhưng họ sẽ bỏ nếu Facebook báo lỗi "Service Unavailable".
    
- **Database:** Cassandra, DynamoDB, CouchDB, DNS.
    

---

### Mở rộng: PACELC Theorem (Level Senior)

CAP chỉ nói về lúc mạng bị hỏng (Partition). Vậy lúc mạng **bình thường** thì sao? Định lý **PACELC** bổ sung cho CAP:

> **"If Partition (P), choose A or C. Else (E), choose Latency (L) or Consistency (C)."**

Nghĩa là: Ngay cả khi mạng ngon, bạn vẫn phải đánh đổi giữa **Tốc độ (Latency)** và **Nhất quán (Consistency)**.

- Muốn nhất quán (C): Phải chờ copy data sang tất cả các node -> Chậm (Latency cao).
    
- Muốn nhanh (L): Trả về ngay, copy sau -> Nhanh nhưng rủi ro data cũ.
    

---

### Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Một hệ thống RDBMS truyền thống (MySQL/PostgreSQL) đứng một mình (Single Node) thuộc loại nào trong CAP? **A:** Nó là **CA**. Vì nó chỉ có 1 node, nên không bao giờ có khái niệm "Partition" (P). Nó luôn Consistent và Available (trừ khi server cháy). Tuy nhiên, CAP theorem chỉ áp dụng cho **Distributed Systems**. Nên câu hỏi này là một cái bẫy. Khi bạn setup MySQL Master-Slave Replication, lúc đó CAP mới có ý nghĩa.

> [!QUESTION] Q: Làm sao thiết kế hệ thống vừa có C vừa có A cao? **A:** Không thể vi phạm định lý vật lý. Nhưng ta có thể "lách luật" bằng cách chia nhỏ yêu cầu:
> 
> - **Phần Billing (Tiền):** Chọn **CP**. Chấp nhận lúc cáp quang biển đứt thì không thanh toán được.
>     
> - **Phần Catalog (Xem sản phẩm):** Chọn **AP**. Cáp đứt vẫn xem hàng được (dù có thể tồn kho hiển thị sai). -> **Microservices** cho phép ta chọn chiến lược CAP khác nhau cho từng service.
>     

---

**Next Step:** Bạn đã có trong tay bộ công cụ tư duy rất mạnh:

1. **Code:** SOLID, DRY, KISS, YAGNI.
    
2. **Architecture:** Microservices, Clean Architecture, 12-Factor.
    
3. **Distributed Theory:** CAP, PACELC, Eventual Consistency.