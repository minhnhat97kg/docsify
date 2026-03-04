---
title: "Golang - Mutex vs Atomic vs RWMutex"
tags:
  - "golang"
  - "backend"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Các hệ thống ngân hàng yêu cầu tính nhất quán dữ liệu (Data Consistency) tuyệt đối (tiền không được tự nhiên sinh ra hay mất đi)."
---

 Các hệ thống ngân hàng yêu cầu **tính nhất quán dữ liệu (Data Consistency)** tuyệt đối (tiền không được tự nhiên sinh ra hay mất đi).

Dưới đây là sự so sánh chi tiết giữa **Atomic**, **Mutex**, và **RWMutex** trong ngữ cảnh lập trình (sử dụng Go làm ví dụ vì tính rõ ràng của nó trong concurrency, nhưng nguyên lý áp dụng cho cả Java, C++, v.v.).

---

### 1. Tổng quan nhanh (The Big Picture)

Để giải quyết vấn đề **Race Condition** (khi nhiều luồng cùng truy cập và sửa đổi dữ liệu chung gây sai lệch), ta có 3 cấp độ "vũ khí":

- **Atomic:** Nhẹ nhất, nhanh nhất, xử lý ở cấp độ CPU. Dùng cho biến đơn giản (số đếm, cờ boolean).
    
- **Mutex (Mutual Exclusion):** Chắc chắn nhất. Chỉ 1 người được vào phòng tại 1 thời điểm. Dùng cho logic phức tạp.
    
- **RWMutex (Read-Write Mutex):** Linh hoạt. Cho phép nhiều người "đọc" cùng lúc, nhưng "ghi" thì phải một mình. Tối ưu cho hệ thống đọc nhiều - ghi ít.
    

---

### 2. Chi tiết và Ví dụ Ngân hàng

#### A. Atomic (Nguyên tử)

Đây là thao tác cấp thấp nhất, được hỗ trợ trực tiếp bởi phần cứng (CPU instructions). Một thao tác Atomic không thể bị ngắt quãng giữa chừng.

- **Đặc điểm:** Không dùng khóa (lock-free), rất nhanh.
    
- **Hạn chế:** Chỉ làm được các phép tính đơn giản trên các kiểu dữ liệu cơ bản (int, pointer). Không bảo vệ được một đoạn code logic dài.
    

**Ví dụ Banking:** Đếm tổng số lượng giao dịch (Transaction Counter) đang diễn ra trên toàn hệ thống. Bạn không cần lock cả database chỉ để tăng con số này lên 1.

Go

```
import "sync/atomic"

type BankMetrics struct {
    totalTx uint64
}

func (m *BankMetrics) RecordTransaction() {
    // Tăng biến đếm lên 1 một cách an toàn tuyệt đối
    // Không cần lock, rất nhanh
    atomic.AddUint64(&m.totalTx, 1) 
}

func (m *BankMetrics) GetTotal() uint64 {
    return atomic.LoadUint64(&m.totalTx)
}
```

#### B. Mutex (Mutual Exclusion)

Đây là chiếc "khóa độc quyền". Khi một Goroutine/Thread giữ khóa (`Lock`), tất cả các luồng khác muốn vào đều phải đứng chờ (`Block`) cho đến khi khóa được mở (`Unlock`).

- **Đặc điểm:** An toàn tuyệt đối cho các critical section (đoạn code quan trọng).
    
- **Hạn chế:** Hiệu năng thấp nếu có quá nhiều luồng tranh chấp (contention). Biến việc xử lý song song thành tuần tự ở đoạn code đó.
    

**Ví dụ Banking:** Chuyển tiền (Transfer). Logic này bắt buộc phải atomic ở mức logic (kiểm tra số dư -> trừ tiền người A -> cộng tiền người B). Bạn không thể dùng Atomic biến số ở đây vì nó gồm nhiều bước.

Go

``` go
import "sync"

type BankAccount struct {
    mu      sync.Mutex // Khóa bảo vệ
    balance int64
}

// Chuyển tiền an toàn
func (acc *BankAccount) Transfer(amount int64, to *BankAccount) {
    // Lock tài khoản gửi
    acc.mu.Lock()
    defer acc.mu.Unlock()

    if acc.balance >= amount {
        acc.balance -= amount
        
        // Lưu ý: Trong thực tế cần cẩn thận deadlock khi lock lồng nhau thế này,
        // nhưng đây là ví dụ về sự độc quyền.
        to.mu.Lock()
        to.balance += amount
        to.mu.Unlock()
    }
}
```

#### C. RWMutex (Read-Write Mutex)

Đây là phiên bản nâng cấp của Mutex, phân biệt rõ giữa việc **Đọc** và **Ghi**.

- **Nhiều người Đọc (RLock):** Cùng lúc được phép vào xem dữ liệu (vì xem thôi thì không làm sai dữ liệu).
    
- **Một người Ghi (Lock):** Khi có người muốn Ghi, nó chặn tất cả (cả người đọc lẫn người ghi khác).
    
- **Đặc điểm:** Tối ưu hóa hiệu năng cực tốt cho các hệ thống **Read-Heavy** (Đọc nhiều hơn Ghi).
    
- **Hạn chế:** Chi phí (overhead) để quản lý RWMutex cao hơn Mutex thường. Nếu hệ thống Ghi liên tục, nó chậm hơn Mutex thường.
    

**Ví dụ Banking:** Hệ thống tra cứu tỷ giá hối đoái (Exchange Rates). Tỷ giá chỉ thay đổi vài phút một lần (Ghi ít), nhưng hàng triệu user check tỷ giá mỗi giây (Đọc nhiều).

Go

``` go
import "sync"

type ExchangeRate struct {
    mu    sync.RWMutex
    rates map[string]float64
}

// 99% request sẽ gọi hàm này
func (e *ExchangeRate) GetRate(currency string) float64 {
    e.mu.RLock()         // Khóa Đọc: Cho phép nhiều người cùng vào lấy tỷ giá
    defer e.mu.RUnlock()
    return e.rates[currency]
}

// 1% request sẽ gọi hàm này (Admin cập nhật tỷ giá)
func (e *ExchangeRate) UpdateRate(currency string, rate float64) {
    e.mu.Lock()          // Khóa Ghi: Chặn tất cả, không ai được đọc hay ghi lúc này
    defer e.mu.Unlock()
    e.rates[currency] = rate
}
```

---

### 3. Bảng so sánh tổng hợp (Nên nhớ cho phỏng vấn)

|**Đặc điểm**|**Atomic**|**Mutex**|**RWMutex**|
|---|---|---|---|
|**Cơ chế**|CPU Instruction (CAS - Compare And Swap).|OS Scheduler / Semaphore.|Phức hợp (kết hợp Mutex và đếm số lượng readers).|
|**Tốc độ**|**Siêu nhanh** (Nanoseconds).|Trung bình.|Nhanh khi đọc, chậm hơn Mutex khi ghi.|
|**Phạm vi bảo vệ**|1 biến đơn lẻ (int, pointer).|1 đoạn code (Critical Section).|1 đoạn code (Phân loại Đọc/Ghi).|
|**Use Case**|Counter, Flag, gán con trỏ nhanh.|Logic nghiệp vụ phức tạp, ghi nhiều.|Cấu hình, Tỷ giá, Cache (Đọc nhiều > Ghi).|
|**Rủi ro**|Khó dùng cho logic phức tạp.|Bottleneck nếu lock quá lâu.|**Writer Starvation** (Người ghi bị đói nếu người đọc vào liên tục).|

### 4. Câu hỏi phỏng vấn liên quan (Gợi ý sâu hơn)

Khi phỏng vấn Bank, nếu bạn nói về RWMutex, người ta có thể hỏi bẫy:

> _"RWMutex có phải lúc nào cũng nhanh hơn Mutex không?"_

**Trả lời:** Không. RWMutex có chi phí quản lý nội bộ phức tạp hơn. Nếu tỉ lệ Ghi (Write) quá cao hoặc ngang bằng Đọc, RWMutex sẽ chậm hơn Mutex thường. Nó chỉ tỏa sáng khi **Read >> Write**.

### 5. Từ khóa cần tìm hiểu thêm

Để chuẩn bị tốt nhất, bạn hãy search thêm các keyword sau:

- _CAS (Compare-And-Swap) operation_ (Cơ chế lõi của Atomic).
    
- _Go Race Detector_ (Cách phát hiện lỗi Race condition).
    
- _Deadlock debugging_ (Làm sao xử lý khi 2 Mutex khóa chéo nhau).
    

Bạn có muốn tôi đi sâu vào ví dụ về **Deadlock** trong chuyển tiền ngân hàng không? Đây là câu hỏi kinh điển.