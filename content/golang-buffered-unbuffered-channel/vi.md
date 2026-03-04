---
title: "Golang: Worker Pool with Context Cancellation"
tags:
  - "golang"
  - "concurrency"
  - "backend"
  - "interview"
  - "context"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Đây là kiến thức cốt lõi về Go Channels (kênh giao tiếp). Trong các hệ thống ngân hàng, việc hiểu sai về Channels có thể dẫn đến Deadlock (treo toàn bộ hệ thống) hoặc Memory Leak (tràn bộ nhớ)."
---

Đây là kiến thức cốt lõi về **Go Channels** (kênh giao tiếp). Trong các hệ thống ngân hàng, việc hiểu sai về Channels có thể dẫn đến **Deadlock** (treo toàn bộ hệ thống) hoặc **Memory Leak** (tràn bộ nhớ).

Dưới đây là giải thích chi tiết theo phong cách "Banking System".

---

### PHẦN 1: Buffered vs. Unbuffered Channels

Hãy tưởng tượng **Channel** là một đường ống chuyển tiền giữa bộ phận **Gửi (Sender)** và bộ phận **Nhận (Receiver)**.
#### 1. Unbuffered Channel (Kênh không bộ đệm)
Đây là kênh giao tiếp **đồng bộ (Synchronous)**.
- **Cơ chế:** "Tiền trao cháo múc".
    - Người Gửi sẽ bị **chặn (block)** cho đến khi Người Nhận sẵn sàng lấy dữ liệu.
    - Người Nhận cũng bị **chặn** cho đến khi Người Gửi đưa dữ liệu vào.
- **Đảm bảo:** Bạn biết chắc chắn 100% là bên kia đã nhận được gói tin thì dòng code tiếp theo mới chạy.
**Ví dụ Banking:** **Thanh toán tức thời (Real-time Payment/RTGS).**

Khi bạn chuyển 1 tỷ cho đối tác, hệ thống phải đảm bảo tiền đã sang tài khoản bên kia rồi mới báo "Thành công". Không được phép "để đó tí nữa chuyển".

```go
// Tạo kênh không bộ đệm (không có số size ở tham số thứ 2)
ch := make(chan string)

go func() {
    // Gửi yêu cầu chuyển tiền
    fmt.Println("Đang chuyển tiền...")
    ch <- "1 Tỷ VND" // BLOCK TẠI ĐÂY cho đến khi có người nhận
    fmt.Println("Bên kia đã nhận tiền!")
}()

// Main nhận tiền
msg := <-ch
fmt.Println("Đã nhận:", msg)
```

#### 2. Buffered Channel (Kênh có bộ đệm)

Đây là kênh giao tiếp **bất đồng bộ (Asynchronous)** (trong giới hạn sức chứa).

- **Cơ chế:** "Hòm thư góp ý".
    
    - Người Gửi cứ thả dữ liệu vào ống. Nếu ống chưa đầy (capacity), người gửi **không bị chặn** và đi làm việc khác ngay.
        
    - Người Gửi chỉ bị chặn khi ống đã **đầy**.
        
- **Đảm bảo:** Tốc độ nhanh hơn, nhưng không đảm bảo bên kia xử lý ngay lập tức.
    

**Ví dụ Banking:** **Hệ thống ghi Log giao dịch (Audit Logs).**

Khi user chuyển tiền xong, cần ghi log lại. Việc ghi log không nên làm chậm thao tác chuyển tiền. Ta đẩy log vào một hàng đợi (buffer). Nếu server log bị chậm, cũng không làm treo app chuyển tiền (trừ khi hàng đợi đầy).

```go
// Tạo kênh có bộ đệm chứa được 3 tin
ch := make(chan string, 3)

// Gửi 2 tin, KHÔNG HỀ BỊ BLOCK dù chưa có ai nhận
ch <- "Log 1: User A login"
ch <- "Log 2: User A check balance"

fmt.Println("Gửi log xong, đi làm việc khác")
```

#### Bảng so sánh (Cần nhớ khi phỏng vấn)

|**Đặc điểm**|**Unbuffered**|**Buffered**|
|---|---|---|
|**Khai báo**|`make(chan T)`|`make(chan T, capacity)`|
|**Tính chất**|Đồng bộ (Synchronous).|Bất đồng bộ (Asynchronous).|
|**Blocking**|Sender chặn đến khi Receiver lấy.|Sender chỉ chặn khi Buffer đầy.|
|**Ưu điểm**|Đảm bảo dữ liệu đã được trao tay (Guarantees).|Hiệu năng cao, giảm độ trễ (Latency).|
|**Rủi ro**|Dễ gây Deadlock nếu không có ai nhận.|Nếu crash, dữ liệu trong buffer bị mất.|

---

### PHẦN 2: Channel Axioms (Các tiên đề về Channel)

Đây là những "luật bất biến" (Physical Laws) của Channel. Trong phỏng vấn, nếu bạn nắm chắc cái này, bạn sẽ được đánh giá là Senior vì bạn biết cách tránh `Panic` và `Deadlock`.

Có 4 trường hợp (state) của channel cần quan tâm: **Nil** (chưa khởi tạo), **Open** (đang mở), và **Closed** (đã đóng).

#### 1. Gửi (Send)

- Gửi vào `nil` channel: **Block mãi mãi (Deadlock)**.
    
- Gửi vào `closed` channel: **PANIC** (Sập chương trình ngay lập tức).
    
    - _Bài học Bank:_ Không bao giờ được gửi tiền vào một tài khoản đã bị đóng (Closed).
        

#### 2. Nhận (Receive)

- Nhận từ `nil` channel: **Block mãi mãi (Deadlock)**.
    
- Nhận từ `closed` channel: **Về ngay lập tức (Không block)**, trả về [Zero Value] của kiểu dữ liệu (0, "", false, nil).
    
    - _Cơ chế kiểm tra:_ `val, ok := <-ch`. Nếu `ok` là `false` -> channel đã đóng.
        

#### 3. Đóng (Close)

- Đóng `nil` channel: **PANIC**.
    
- Đóng `closed` channel (đóng lại lần 2): **PANIC**.
    

#### Tóm tắt các "Tiên đề" (Axioms Cheat Sheet)

|**Hành động**|**Nil Channel**|**Open Channel**|**Closed Channel**|
|---|---|---|---|
|**Read (<-ch)**|Block vĩnh viễn ☠️|OK|**Trả về Zero Value** (Non-blocking) ✅|
|**Write (ch<-)**|Block vĩnh viễn ☠️|OK|**PANIC** 💥|
|**Close**|**PANIC** 💥|OK|**PANIC** 💥|

---

### 3. Áp dụng vào phỏng vấn Bank

Nhà tuyển dụng sẽ hỏi các câu tình huống dựa trên Axioms để bẫy bạn:

**Câu hỏi:** _"Làm sao để biết một channel đã bị đóng hay chưa trước khi gửi dữ liệu vào để tránh Panic?"_

**Trả lời (Cẩn thận bẫy):**

"Trong Go, **không có hàm nào** để kiểm tra channel đã đóng hay chưa (`IsClosed(ch)` không tồn tại).

Tư duy thiết kế chuẩn là: **Chỉ có người tạo ra channel (Sender) mới có quyền đóng channel đó.** Người nhận (Receiver) không bao giờ được đóng channel. Điều này đảm bảo ta không bao giờ gửi vào một channel đã đóng."

**Câu hỏi:** _"Tại sao đọc từ channel đã đóng lại không Panic mà trả về Zero Value?"_

**Trả lời:**

"Đây là cơ chế **Signaling (Báo hiệu)**. Ví dụ trong mô hình **Worker Pool**, khi ta muốn tắt 100 worker đang chạy, ta chỉ cần `close(jobs_channel)`. Tất cả 100 worker đang chờ đọc sẽ nhận được tín hiệu `closed` (thông qua zero value) và tự động thoát vòng lặp một cách êm đẹp (Graceful Shutdown)."

---

Đây là mô hình **Worker Pool** kinh điển. Trong phỏng vấn ngân hàng, đây là bài toán mô phỏng hệ thống **xử lý giao dịch cuối ngày (End-of-Day Batch Processing)**.

Ví dụ: Bạn có 1.000.000 giao dịch cần xử lý, nhưng hệ thống chỉ chịu tải được 5 luồng (goroutines) chạy song song cùng lúc để tránh sập Database.

### Mô hình:

1. **Jobs Channel:** Hàng đợi chứa các giao dịch (Buffered Channel).
    
2. **Workers:** Các nhân viên (Goroutines) lấy việc từ hàng đợi để làm.
    
3. **WaitGroup:** Cơ chế để quản lý (Main) chờ tất cả nhân viên làm xong mới được đi về.
    

---

### Code Mẫu (Golang)

Bạn có thể copy code này chạy thử ngay trên máy hoặc Go Playground.

```go
package main

import (
	"fmt"
	"sync"
	"time"
)

// Giả lập một giao dịch ngân hàng
type Transaction struct {
	ID     int
	Amount int
}

// Worker: Đóng vai trò là nhân viên xử lý
// id: ID của nhân viên (Worker 1, Worker 2...)
// jobs: Kênh để nhận việc
// wg: Để báo cáo khi hoàn thành công việc chung
func worker(workerID int, jobs <-chan Transaction, wg *sync.WaitGroup) {
	defer wg.Done() // Báo cáo "Tôi đã xong nhiệm vụ" khi hàm này kết thúc

	// Vòng lặp này sẽ chạy mãi cho đến khi channel 'jobs' bị đóng (CLOSE)
	// và không còn dữ liệu bên trong.
	for trans := range jobs {
		fmt.Printf("[Worker %d] Đang xử lý giao dịch #%d: %d VND\n", workerID, trans.ID, trans.Amount)

		// Giả lập thời gian xử lý (ví dụ: gọi xuống DB, check fraud...)
		time.Sleep(500 * time.Millisecond)

		fmt.Printf("[Worker %d] --> Xong giao dịch #%d\n", workerID, trans.ID)
	}

	fmt.Printf("[Worker %d] Đã nghỉ việc (Shutdown)\n", workerID)
}

func main() {
	// 1. Cấu hình
	const numJobs = 10
	const numWorkers = 3 // Giới hạn chỉ chạy 3 luồng cùng lúc

	// Tạo buffered channel để chứa việc.
	// Buffer giúp Main không bị block khi đẩy việc vào (trừ khi buffer đầy).
	jobs := make(chan Transaction, numJobs)

	// WaitGroup để chờ tất cả worker xong việc
	var wg sync.WaitGroup

	// 2. Khởi động các Workers (Tuyển nhân viên)
	// Lúc này chưa có việc, các worker sẽ ở trạng thái chờ (Block) ở dòng `range jobs`
	for w := 1; w <= numWorkers; w++ {
		wg.Add(1) // Đăng ký 1 worker cần chờ
		go worker(w, jobs, &wg)
	}

	// 3. Đẩy việc vào hàng đợi (Dispatcher)
	fmt.Println("=== BẮT ĐẦU ĐẨY GIAO DỊCH VÀO HỆ THỐNG ===")
	for j := 1; j <= numJobs; j++ {
		jobs <- Transaction{ID: j, Amount: j * 10000}
	}

	// 4. Graceful Shutdown: Đóng channel
	// Đây là tín hiệu quan trọng: "Không còn việc mới nữa, làm nốt đống cũ đi rồi nghỉ"
	close(jobs)
	fmt.Println("=== ĐÃ GỬI HẾT VIỆC, ĐÃ ĐÓNG CHANNEL ===")

	// 5. Chờ đợi (Blocking)
	// Main goroutine đứng đây chờ cho đến khi tất cả worker gọi wg.Done()
	wg.Wait()

	fmt.Println("=== TẤT CẢ GIAO DỊCH ĐÃ XỬ LÝ XONG ===")
}
```

---

### Giải thích cơ chế (Deep Dive)

Đây là cách dòng chảy dữ liệu hoạt động, hãy chú ý các điểm in đậm:

#### 1. Tại sao dùng `range jobs` trong hàm worker?

```go
for trans := range jobs { ... }
```

Đây là cách Go xử lý Graceful Shutdown dựa trên **Axioms** (Tiên đề) mình đã nói ở câu trước:

- Khi channel còn mở: Worker lấy từng việc ra làm.
    
- Khi channel bị **trống** (empty): Worker đứng chờ (block).
    
- Khi `close(jobs)` được gọi **VÀ** channel đã **trống**: Vòng lặp `range` tự động thoát (break). Worker chạy xuống dòng `wg.Done()` và kết thúc.
    

#### 2. Vai trò của `close(jobs)`

Nếu bạn quên dòng `close(jobs)` trong hàm main:

- Các worker sau khi làm hết 10 việc sẽ tiếp tục đứng chờ việc mới mãi mãi (vì nó không biết là sếp đã hết việc).
    
- Chương trình sẽ bị treo (nếu main cũng chờ) hoặc báo lỗi **Deadlock**.
    

#### 3. Vai trò của Buffered Channel `make(chan ..., numJobs)`

Nếu dùng **Unbuffered Channel**:

- Vòng lặp gửi việc ở `main` sẽ bị chặn liên tục cho đến khi có worker rảnh tay nhận việc. Tốc độ đẩy việc vào sẽ bị phụ thuộc vào tốc độ xử lý của worker.
    
    Nếu dùng **Buffered Channel**:
    
- `main` ném vèo một cái hết 10 việc vào ống (buffer) rồi đi làm việc khác (hoặc đóng channel ngay). Các worker cứ thong thả lấy từ buffer ra làm. Giúp tách biệt tốc độ giữa người gửi và người nhận.
    

---

### Câu hỏi phỏng vấn nâng cao (Follow-up)

Nếu người phỏng vấn hỏi tiếp:

_"Nếu trong quá trình xử lý, tôi muốn dừng hệ thống khẩn cấp (Cancel) ngay lập tức chứ không chờ làm hết việc trong buffer thì làm thế nào?"_

**Gợi ý trả lời:**

"Lúc đó chúng ta cần sử dụng **`context.Context`**.

Chúng ta sẽ truyền một `context.WithCancel` vào cho các Worker. Trong vòng lặp xử lý của Worker, ta thêm một `case <-ctx.Done():` để lắng nghe tín hiệu hủy. Khi Main gọi hàm `cancel()`, tất cả worker sẽ nhận tín hiệu và `return` ngay lập tức, bỏ qua các job còn lại trong channel."

Bạn có muốn tôi bổ sung đoạn code xử lý **Cancellation với Context** này vào không? (Rất hay dùng khi user bấm nút "Hủy giao dịch").

Đã rõ. Kể từ bây giờ, tôi sẽ định dạng câu trả lời tối ưu cho **Obsidian** (Markdown, Callouts, Tags, Links). Bạn có thể copy-paste trực tiếp nội dung này vào vault của bạn.

Dưới đây là phần giải thích và code mẫu cho **Worker Pool có cơ chế hủy (Cancellation) sử dụng `context`**.

---

# Golang: Worker Pool with Context Cancellation

## 1. Tổng quan

> [!SUMMARY] Vấn đề
> 
> Trong mô hình Worker Pool thông thường, nếu chương trình gặp lỗi hoặc người dùng bấm "Hủy", các Worker vẫn sẽ tiếp tục xử lý nốt các công việc trong hàng đợi (Buffer) rồi mới dừng.
> 
> **Giải pháp:** Sử dụng gói `context` để bắn tín hiệu "DỪNG NGAY" (Broadcast) tới tất cả Worker, buộc chúng phải bỏ dở công việc hiện tại và return lập tức.

## 2. Code Implementation

```go
package main

import (
	"context"
	"fmt"
	"sync"
	"time"
)

// --- Structs ---
type Transaction struct {
	ID     int
	Amount int
}

// --- Worker ---
// ctx: Context dùng để lắng nghe tín hiệu hủy
func worker(ctx context.Context, id int, jobs <-chan Transaction, wg *sync.WaitGroup) {
	defer wg.Done()
	fmt.Printf("[Worker %d] Sẵn sàng làm việc\n", id)

	for {
		select {
		// CASE 1: Lắng nghe tín hiệu hủy từ Context
		case <-ctx.Done():
			fmt.Printf("[Worker %d] 🛑 Nhận lệnh hủy! Dừng ngay lập tức.\n", id)
			return // Thoát hàm worker ngay

		// CASE 2: Nhận việc từ channel jobs
		case job, ok := <-jobs:
			if !ok {
				// Channel đã đóng và hết việc
				fmt.Printf("[Worker %d] Hết việc, nghỉ.\n", id)
				return
			}

			// Xử lý logic nghiệp vụ
			fmt.Printf("[Worker %d] 🔄 Đang xử lý GD #%d (%d VND)...\n", id, job.ID, job.Amount)

			// Giả lập xử lý tốn thời gian (quan trọng để thấy hiệu quả của Cancel)
			// Trong thực tế, nên truyền ctx vào cả hàm DB/API call
			select {
			case <-time.After(500 * time.Millisecond):
				fmt.Printf("[Worker %d] ✅ Xong GD #%d\n", id, job.ID)
			case <-ctx.Done():
				fmt.Printf("[Worker %d] 🛑 Bị hủy khi đang làm dở GD #%d!\n", id, job.ID)
				return
			}
		}
	}
}

// --- Main ---
func main() {
	// 1. Setup Context với hàm Cancel
	// ctx là context cha, cancel là cái nút bấm đỏ để kích hoạt hủy
	ctx, cancel := context.WithCancel(context.Background())

	const numJobs = 10
	const numWorkers = 3
	jobs := make(chan Transaction, numJobs)
	var wg sync.WaitGroup

	// 2. Khởi tạo Workers
	for w := 1; w <= numWorkers; w++ {
		wg.Add(1)
		// Truyền ctx vào cho worker
		go worker(ctx, w, jobs, &wg)
	}

	// 3. Đẩy việc vào (Producer)
	go func() {
		for j := 1; j <= numJobs; j++ {
			jobs <- Transaction{ID: j, Amount: j * 1000}
		}
		close(jobs) // Đóng channel khi gửi hết
	}()

	// 4. Giả lập tình huống: Chạy được 1 giây thì HỆ THỐNG GẶP SỰ CỐ
	time.Sleep(1 * time.Second)
	fmt.Println("\n!!! ⚠️ SỰ CỐ NGHIÊM TRỌNG - KÍCH HOẠT HỦY HỆ THỐNG !!!\n")

	cancel() // <--- BẤM NÚT HỦY (Gửi tín hiệu tới tất cả worker)

	// 5. Chờ tất cả rút lui an toàn
	wg.Wait()
	fmt.Println("\n=== Hệ thống đã dừng an toàn ===")
}
```

## 3. Phân tích kỹ thuật (Deep Dive)

### Cơ chế `select` trong vòng lặp

Để một Goroutine có thể vừa "làm việc" vừa "ngóng tín hiệu hủy", ta không thể dùng vòng lặp `for range` đơn thuần. Ta phải dùng `for { select { ... } }`.

> [!TIP] Pattern `Select`
> 
> Cấu trúc `select` cho phép Goroutine chờ trên nhiều channel cùng lúc. Cái nào đến trước thì xử lý cái đó.

1. **`case <-ctx.Done():`**
    
    - Kênh ưu tiên số 1.
        
    - Khi hàm `cancel()` được gọi ở Main, `ctx.Done()` sẽ đóng lại, trả về giá trị ngay lập tức -> Worker nhảy vào case này và `return` (thoát) ngay.
        
2. **`case job, ok := <-jobs:`**
    
    - Kênh công việc. Nếu chưa có lệnh hủy, worker sẽ lấy việc làm bình thường.
        

### Xử lý Hủy khi đang làm dở (`context` lồng nhau)

Trong đoạn code trên, tôi có thêm một khối `select` thứ 2 lồng bên trong logic xử lý:

```go
select {
case <-time.After(500 * time.Millisecond):
    // Xong việc
case <-ctx.Done():
    // Bị hủy giữa chừng
}
```

> [!WARNING] Lưu ý quan trọng
> 
> Nếu bạn gọi Database hoặc API bên thứ 3, hãy **luôn truyền `ctx`** vào hàm của thư viện (ví dụ: `db.QueryContext(ctx, ...)`). Thư viện sẽ tự động ngắt kết nối nếu `ctx` bị hủy, giúp tiết kiệm tài nguyên hệ thống triệt để.

## 4. Câu hỏi phỏng vấn liên quan

> [!QUESTION] Khi nào dùng `context.WithTimeout` thay vì `context.WithCancel`?
> 
> - **`WithCancel`**: Dùng khi việc hủy phụ thuộc vào **sự kiện** bên ngoài (User bấm nút Stop, Server shutdown, App crash).
>     
> - **`WithTimeout` / `WithDeadline`**: Dùng khi việc hủy phụ thuộc vào **thời gian** (SLA quy định request này chỉ được chạy tối đa 2s, quá 2s tự cắt).
>     
