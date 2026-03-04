---
title: "System Design - Distributed Locking (Redlock)"
tags:
  - "system-design"
  - "distributed-systems"
  - "redis"
  - "redlock"
  - "concurrency"
  - "interview"
  - "banking"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Trong lập trình đơn luồng hoặc đơn máy (Monolith), ta dùng để chặn Race Condition."
---

## 1. Vấn đề: Local Mutex vs. Distributed Lock

Trong lập trình đơn luồng hoặc đơn máy (Monolith), ta dùng `sync.Mutex` để chặn Race Condition.

Nhưng trong **Microservices**, Service A chạy trên 10 server (Pods) khác nhau.

- `sync.Mutex` chỉ khóa được trong nội bộ RAM của 1 server.
    
- -> Server 1 và Server 2 vẫn có thể cùng lúc chọc vào Database để sửa cùng một bản ghi.
    

**Giải pháp:** Cần một cái khóa nằm bên ngoài (External Lock Manager). Redis là lựa chọn phổ biến nhất vì tốc độ nhanh.

---

## 2. Cách tiếp cận ngây thơ (Single Instance)

Cách phổ biến nhất mà các Junior hay làm (và sai trong hệ thống lớn):

Sử dụng lệnh `SETNX` (Set if Not Exists).

Bash

```
SET resource_name my_random_value NX PX 30000
```

- `NX`: Chỉ set nếu key chưa tồn tại (tức là chưa ai khóa).
    
- `PX 30000`: Tự động hết hạn (TTL) sau 30 giây. (Tránh trường hợp Service crash mà quên trả chìa khóa -> Deadlock vĩnh viễn).
    

> [!DANGER] Vấn đề (Single Point of Failure)
> 
> Nếu Redis Master bị sập sau khi nhận khóa nhưng **trước khi** kịp sync sang Slave.
> 
> 1. Client A lấy khóa trên Master.
>     
> 2. Master sập.
>     
> 3. Slave lên làm Master (nhưng chưa có dữ liệu khóa của A).
>     
> 4. Client B lấy khóa trên Master mới -> Thành công.
>     
>     -> **An toàn bị phá vỡ (Safety Violation).** Cả A và B đều nghĩ mình đang giữ khóa.
>     

---

## 3. Redlock Algorithm (Giải pháp của Redis)

Để giải quyết vấn đề Master sập, Redis đề xuất thuật toán **Redlock**.

Yêu cầu: Chạy **N** Redis Master độc lập (thường là 5 node), nằm trên các máy vật lý/zone khác nhau.

### Thuật toán (5 bước)

1. Lấy thời gian hiện tại (`start_time`).
    
2. Cố gắng lấy khóa (dùng `SETNX`) trên **tất cả N instances** tuần tự.
    
    - Thời gian chờ (Timeout) cho mỗi node phải rất nhỏ (ví dụ 5-50ms) so với thời gian khóa (10s). Để tránh bị kẹt nếu một node Redis bị chết.
        
3. Tính toán thời gian đã trôi qua: `elapsed = now - start_time`.
    
4. **Điều kiện thành công:**
    
    - Lấy được khóa trên **Đa số** (Majority) node (N/2 + 1). Ví dụ: 3/5 node.
        
    - `elapsed` < `Validity Time` (Thời gian hiệu lực của khóa).
        
5. Nếu thành công: Thời gian hiệu lực thực tế = `Validity Time - elapsed`.
    
    - Nếu thất bại (không đủ quorum hoặc hết giờ): Gửi lệnh **Unlock** tới tất cả các node (kể cả node mình chưa kịp lock) để dọn dẹp.
        

---

## 4. Code Implementation (Golang)

Đừng tự viết lại Redlock. Hãy dùng thư viện chuẩn `go-redsync`.

Go

```
package main

import (
    "github.com/go-redsync/redsync/v4"
    "github.com/go-redsync/redsync/v4/redis/goredis/v9"
    goredislib "github.com/redis/go-redis/v9"
)

func main() {
    // 1. Kết nối tới các Redis Pool độc lập
    client1 := goredislib.NewClient(&goredislib.Options{Addr: "localhost:6379"})
    client2 := goredislib.NewClient(&goredislib.Options{Addr: "localhost:6380"})
    client3 := goredislib.NewClient(&goredislib.Options{Addr: "localhost:6381"})
    // ... (Cần 5 node cho production)

    pool1 := goredis.NewPool(client1)
    pool2 := goredis.NewPool(client2)
    pool3 := goredis.NewPool(client3)

    // 2. Khởi tạo Redsync
    rs := redsync.New(pool1, pool2, pool3)

    // 3. Tạo Mutex (Khóa phân tán)
    mutexname := "my-global-mutex"
    // Expiry: 8 giây. Tries: Thử lại 32 lần nếu trượt.
    mutex := rs.NewMutex(mutexname, redsync.WithExpiry(8*time.Second))

    // 4. Bắt đầu khóa (Lock)
    if err := mutex.Lock(); err != nil {
        panic(err) // Không lấy được khóa
    }

    // --- CRITICAL SECTION (Thao tác DB, API...) ---
    processBankingTransaction()
    // ----------------------------------------------

    // 5. Mở khóa (Unlock)
    if ok, err := mutex.Unlock(); !ok || err != nil {
        panic("unlock failed")
    }
}
```

---

## 5. Mối nguy hiểm: The "Fencing Token" Problem

Đây là phần phân biệt Senior và Mid-level.

**Câu hỏi:** Điều gì xảy ra nếu Client A lấy được khóa, nhưng bị treo (GC Pause - Garbage Collection dừng thế giới) trong 10 phút?

1. A lấy khóa (TTL 10s).
    
2. A bị GC Pause (ứng dụng đơ).
    
3. Hết 10s, Redis xóa khóa của A.
    
4. B lấy khóa -> B ghi dữ liệu vào DB.
    
5. A tỉnh dậy (hết đơ) -> A tiếp tục ghi đè dữ liệu vào DB (vì A tưởng mình vẫn còn khóa).
    
    -> **Dữ liệu bị hỏng (Data Corruption).**
    

### Giải pháp: Fencing Token

Distributed Lock phải trả về một con số tăng dần (Token).

- A lấy khóa -> Token = 33.
    
- B lấy khóa (sau khi A hết hạn) -> Token = 34.
    
- Khi ghi vào Database, DB phải check:
    
    - `UPDATE ... WHERE id=1 AND last_token < 33`.
        
- Khi A tỉnh dậy, gửi Token 33. DB thấy hiện tại đã là 34 -> **Từ chối (Reject)**.
    

> [!WARNING] Lưu ý về Redlock
> 
> Redlock **không sinh ra** Fencing Token tự nhiên (do nó không có cơ chế đồng thuận Consensus mạnh như Raft/Paxos). Nó chỉ dựa vào thời gian.
> 
> -> Martin Kleppmann (tác giả Designing Data-Intensive Applications) đã chỉ trích Redlock vì lý do này.

---

## 6. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Khi nào nên dùng Redlock vs. ZooKeeper/Etcd?
> 
> **A:**
> 
> - **Redlock (Redis):** Ưu tiên **Hiệu năng** (Performance). Dùng khi bạn cần khóa nhanh, chấp nhận rủi ro rất nhỏ (clock drift) hoặc dùng cho các tác vụ không quá quan trọng (vd: cronjob gửi email trùng lặp tí cũng không chết ai, hoặc chặn spam).
>     
> - **ZooKeeper/Etcd/Consul:** Ưu tiên **Tính đúng đắn** (Correctness). Dùng cho Core Banking, Leader Election. Chúng dùng thuật toán Consensus (Raft/Paxos) đảm bảo an toàn tuyệt đối hơn, có Fencing Token chuẩn, nhưng chậm hơn Redis.
>     

> [!QUESTION] Q: Tại sao cần random value trong câu lệnh SETNX?
> 
> **A:** Để đảm bảo an toàn khi Unlock.
> 
> `if redis.get("lock_key") == my_random_value then redis.del("lock_key")`.
> 
> Tránh trường hợp: A bị treo -> Khóa hết hạn -> B lấy khóa -> A tỉnh dậy -> A xóa nhầm khóa của B.

> [!QUESTION] Q: Đồng hồ máy chủ (System Clock) bị lệch thì sao?
> 
> **A:** Redlock phụ thuộc nặng vào đồng hồ hệ thống. Nếu một server trong cụm Redis bị nhảy thời gian (do NTP update), nó có thể làm trôi hiệu lực khóa, khiến khóa hết hạn sớm hơn dự kiến -> Phá vỡ an toàn. Đây là điểm yếu chí mạng của Redlock.