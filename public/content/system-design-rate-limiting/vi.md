---
title: "System Design - Rate Limiting"
tags:
  - "system-design"
  - "ratelimit"
  - "algorithm"
  - "uber"
  - "security"
  - "interview"
  - "banking"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Rate Limiting là \"người bảo vệ\" (Bouncer) đứng trước cổng API Gateway."
---

## 1. Tại sao cần Rate Limiting? (Bảo vệ hệ thống)

Rate Limiting là "người bảo vệ" (Bouncer) đứng trước cổng API Gateway.

Trong Ngân hàng, nó giải quyết 3 vấn đề sống còn:

1. **DDoS Protection:** Ngăn chặn Hacker spam hàng triệu request làm sập Core Banking.
    
2. **Fairness (Công bằng):** Không để một đối tác (Partner A) chiếm hết băng thông, khiến đối tác B không giao dịch được.
    
3. **Cost Control:** Giới hạn số lượng OTP SMS gửi đi (vì mỗi tin tốn tiền).
    

---

## 2. Hai thuật toán kinh điển

### A. Token Bucket (Xô Token) - _Phổ biến nhất_

> [!SUMMARY] Cơ chế
> 
> - Có một cái xô chứa được tối đa $N$ token.
>     
> - Có một "vòi nước" tự động nhỏ thêm token vào xô với tốc độ cố định (ví dụ: 10 token/giây).
>     
> - Mỗi khi có Request tới, nó phải lấy được 1 token từ xô thì mới được đi qua.
>     
> - Nếu xô rỗng -> Request bị chặn (Drop/Queue).
>     

- **Ưu điểm đặc biệt:** Cho phép **Burst** (Đột biến).
    
    - Nếu xô đang đầy (100 token), bạn có thể gửi bùm một phát 100 request cùng lúc. Sau đó mới bị giới hạn.
        
    - _Use Case:_ User F5 trang web (cần load 50 cái ảnh cùng lúc). Token Bucket xử lý rất tốt.
        

### B. Leaky Bucket (Xô Rò Rỉ) - _Traffic Shaping_

> [!SUMMARY] Cơ chế
> 
> - Request đổ vào xô (Queue) với tốc độ bất kỳ.
>     
> - Nhưng Request "rỉ" ra khỏi xô để vào server xử lý với **tốc độ cố định** (Constant Rate).
>     
> - Nếu xô đầy -> Request mới bị tràn ra ngoài (Drop).
>     

- **Ưu điểm đặc biệt:** **Làm mượt traffic (Smoothing).**
    
    - Dù bên ngoài bão tố (traffic lên xuống thất thường), Server bên trong vẫn nhận request đều đặn như vắt chanh.
        
    - _Use Case:_ Ghi log vào Database, đẩy job vào Queue (tránh làm quá tải Worker).
        

---

## 3. Deep Dive: `uber-go/ratelimit`

Thư viện này nổi tiếng vì cách tiếp cận thông minh: Nó **không dùng Timer** để fill token (vì Timer tốn CPU và không chính xác ở mili-giây).

Nó cài đặt biến thể của **Leaky Bucket** (gọi là GCRA - Generic Cell Rate Algorithm).

- **Tư duy:** Thay vì đếm token, nó tính toán **"Thời điểm dự kiến"** (Next expected arrival time).
    
- Ví dụ: Rate = 10 req/s -> Mỗi request cách nhau 100ms.
    
- Request 1 đến lúc `t`. Request 2 phải đến lúc `t + 100ms`.
    
- Nếu Request 2 đến lúc `t + 10ms` -> Nó phải **ngủ (sleep)** 90ms nữa mới được chạy.
    

**Code Demo (Golang):**

Go

```go
package main

import (
	"fmt"
	"time"

	"go.uber.org/ratelimit"
)

func main() {
	// Tạo limiter: 10 request mỗi giây (Leaky Bucket)
	// withoutSlack: Cấu hình nghiêm ngặt, không cho phép burst
	rl := ratelimit.New(10, ratelimit.WithoutSlack)

	prev := time.Now()
	for i := 0; i < 10; i++ {
		now := rl.Take() // Hàm này sẽ BLOCK (Sleep) cho đến khi được phép chạy

		fmt.Println(i, now.Sub(prev)) // Output sẽ luôn xấp xỉ 100ms
		prev = now
	}
}
```

_Kết quả:_ Các dòng in ra sẽ cách nhau **đều đặn** 100ms, bất kể vòng lặp for chạy nhanh thế nào.

---

## 4. Distributed Rate Limiting (Redis)

Thư viện Uber chỉ chạy trên 1 máy (Local Limit).

Nếu bạn có 100 Pods chạy Microservices, bạn cần **Redis** để đếm tổng toàn hệ thống.

**Thuật toán: Sliding Window Log (Lua Script)**

Để đảm bảo chính xác và Atomic, ta không dùng lệnh GET/SET rời rạc. Ta dùng Lua Script chạy trực tiếp trên Redis.

Lua

```lua
-- Pseudo Code cho Redis Lua Script
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2]) -- ví dụ 1000ms
local now = tonumber(ARGV[3])

-- 1. Xóa các request cũ quá hạn (ngoài cửa sổ trượt)
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)

-- 2. Đếm số request hiện tại trong cửa sổ
local count = redis.call('ZCARD', key)

-- 3. Nếu chưa vượt quá giới hạn -> Cho phép
if count < limit then
    redis.call('ZADD', key, now, now) -- Thêm request mới (score = timestamp)
    redis.call('PEXPIRE', key, window) -- Set TTL tự dọn dẹp
    return 1 -- Allowed
else
    return 0 -- Rejected (429 Too Many Requests)
end
```

---

## 5. System Design: Đặt Rate Limiter ở đâu?

1. **API Gateway (Kong, NGINX):**
    
    - _Vị trí:_ Tuyến đầu.
        
    - _Mục tiêu:_ Chặn DDoS, bảo vệ toàn bộ hạ tầng.
        
    - _Loại:_ Thường là Token Bucket (IP-based).
        
2. **Middleware (Application Side):**
    
    - _Vị trí:_ Trong code Go/Java.
        
    - _Mục tiêu:_ Business Logic (Ví dụ: User chỉ được rút tiền 5 lần/ngày).
        
    - _Loại:_ Distributed Limiter (Redis).
        
3. **Database Side:**
    
    - _Vị trí:_ Trước khi query DB.
        
    - _Mục tiêu:_ Tránh sập DB (như thư viện `uber-go/ratelimit`).
        
    - _Loại:_ Leaky Bucket (để làm phẳng traffic ghi xuống DB).
        

---

## 6. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Làm sao xử lý Rate Limit cho VIP User vs. User thường?
> 
> **A:** Sử dụng **Tiered Rate Limiting**.
> 
> Thay vì hardcode giới hạn, ta lưu config trong DB/Redis:
> 
> - `Tier_Standard`: 10 req/s.
>     
> - `Tier_VIP`: 100 req/s.
>     
>     Khi Middleware check limit, nó sẽ lấy UserID -> Tra cứu Tier -> Áp dụng limit tương ứng.
>     

> [!QUESTION] Q: Nếu Redis (dùng để đếm limit) bị sập thì sao?
> 
> **A:**
> 
> - **Fail Open:** Chấp nhận cho qua (Allow all). Vì thà để hệ thống chịu tải cao còn hơn chặn nhầm tất cả User không cho giao dịch. (Ưu tiên Availability).
>     
> - **Local Fallback:** Nếu Redis chết, chuyển sang dùng In-memory Limiter cục bộ tạm thời (dù không chính xác 100% nhưng vẫn đỡ hơn không có gì).
>     

> [!QUESTION] Q: HTTP Code trả về là gì?
> 
> **A:** **429 Too Many Requests**.
> 
> Nên kèm theo Header: `Retry-After: 30` (Báo cho Client biết sau 30s hãy quay lại).