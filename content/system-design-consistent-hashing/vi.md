---
title: "System Design - Consistent Hashing"
tags:
  - "system-design"
  - "distributed-systems"
  - "hashing"
  - "scalability"
  - "load-balancing"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Để chia tải dữ liệu (Sharding) ra $N$ server, cách đơn giản nhất là dùng phép chia lấy dư:"
---

## 1. Vấn đề của Hashing Cổ điển (Modulo Hashing)

Để chia tải dữ liệu (Sharding) ra $N$ server, cách đơn giản nhất là dùng phép chia lấy dư:

$$server\_index = hash(key) \% N$$

- **Ví dụ:** Có 4 server ($N=4$).
    
- `hash("user_123")` = 10 -> $10 \% 4 = 2$ -> Vào Server 2.
    

> [!DANGER] Thảm họa Rebalancing
> 
> Điều gì xảy ra khi **1 Server bị chết** hoặc bạn **thêm 1 Server mới** (Scale up)?
> 
> - $N$ thay đổi từ 4 thành 5.
>     
> - Công thức đổi thành: $hash(key) \% 5$.
>     
> - **Hậu quả:** Hầu hết các key sẽ ra kết quả mới (ví dụ $10 \% 5 = 0$ -> chuyển sang Server 0).
>     
> - **Kết luận:** Gần như **100% dữ liệu** phải di chuyển giữa các server.
>     
>     - Với Database: Mạng bị nghẽn vì copy dữ liệu (Re-sharding storm).
>         
>     - Với Cache: Cache bị xóa sạch (Cache Stampede) -> DB sập.
>         

---

## 2. Giải pháp: Consistent Hashing (Băm nhất quán)

Consistent Hashing giải quyết vấn đề trên bằng cách đảm bảo: Khi thay đổi số lượng server ($N$), chỉ có $\frac{1}{N}$ số lượng key cần phải di chuyển.

### Mô hình Vòng tròn (Hash Ring)

1. **Không gian Hash:** Tưởng tượng dải số của hàm hash (ví dụ SHA-1 từ $0$ đến $2^{160}-1$) được uốn cong thành một vòng tròn khép kín.
2. **Server trên vòng tròn:** Băm IP hoặc ID của Server để đặt nó lên vòng tròn này.
3. **Key trên vòng tròn:** Băm Key (ví dụ `user_id`) để đặt nó lên vòng tròn.

### Quy tắc tìm Server (Clockwise Rule)

Để biết Key A thuộc về Server nào
- Từ vị trí của Key A, đi theo **chiều kim đồng hồ** (Clockwise).
- Gặp Server nào đầu tiên thì Key thuộc về Server đó.

---

## 3. Kịch bản Thêm/Xóa Server

### A. Thêm Server (Scale Out)

Giả sử ta thêm **Server 4** vào vòng tròn, nằm giữa Server 3 và Server 1.

- **Chỉ có** các Key nằm trong khoảng (Server 3 -> Server 4) là bị ảnh hưởng.
    
- Chúng sẽ được chuyển từ Server 1 (chủ cũ) sang Server 4 (chủ mới).
    
- Các Key khác vẫn giữ nguyên.
    
- _Kết quả:_ Di chuyển dữ liệu tối thiểu.
    

### B. Xóa Server (Failover)

Nếu **Server 2** bị cháy.

- Các Key đang thuộc về Server 2 sẽ đi tiếp theo chiều kim đồng hồ và gặp **Server 3**.
    
- Server 3 sẽ gánh phần việc của Server 2.
    
- Các server khác không bị ảnh hưởng.
    

---

## 4. Vấn đề Data Skew & Virtual Nodes

> [!WARNING] Vấn đề phân bố không đều (Hotspot)
> 
> Do tính ngẫu nhiên của Hashing, có thể các Server tập trung vào một góc của vòng tròn, hoặc khoảng cách giữa Server A và Server B quá lớn.
> 
> -> Server A nhận ít dữ liệu, Server B nhận quá nhiều (Data Skew).

### Giải pháp: Virtual Nodes (VNodes)

Thay vì mỗi Server vật lý chỉ là 1 điểm trên vòng tròn, ta biến nó thành **nhiều điểm ảo**.

- Server A (Vật lý) -> Có 100 VNodes trên vòng tròn: $A_1, A_2, ..., A_{100}$.
    
- Server B (Vật lý) -> Có 100 VNodes: $B_1, B_2, ..., B_{100}$.
    

**Lợi ích:**

1. **Cân bằng tải:** Các VNodes nằm rải rác xen kẽ nhau giúp chia đều dữ liệu hơn.
    
2. **Heterogeneity (Không đồng nhất):** Server mạnh (64GB RAM) có thể gán 200 VNodes, Server yếu (16GB RAM) gán 50 VNodes.
    

---

## 5. Code Implementation (Golang)

Trong thực tế, Hash Ring được cài đặt bằng một mảng đã sắp xếp (Sorted Array) các mã Hash của Server.

Go

```
package main

import (
	"hash/crc32"
	"sort"
	"strconv"
)

type HashRing struct {
	replicas int            // Số lượng VNodes cho mỗi server
	keys     []int          // Danh sách đã sort các mã hash của VNodes
	hashMap  map[int]string // Map từ Hash -> Tên Server vật lý
}

func NewHashRing(replicas int) *HashRing {
	return &HashRing{
		replicas: replicas,
		hashMap:  make(map[int]string),
	}
}

// Thêm Server vào Ring
func (h *HashRing) AddNode(nodeName string) {
	for i := 0; i < h.replicas; i++ {
		// Tạo VNode key: "ServerA#1", "ServerA#2"...
		vNodeKey := nodeName + "#" + strconv.Itoa(i)
		hash := int(crc32.ChecksumIEEE([]byte(vNodeKey)))
		
		h.keys = append(h.keys, hash)
		h.hashMap[hash] = nodeName
	}
	// Quan trọng: Phải sort lại để dùng Binary Search
	sort.Ints(h.keys)
}

// Tìm Server cho một Key bất kỳ
func (h *HashRing) GetNode(key string) string {
	if len(h.keys) == 0 {
		return ""
	}

	hash := int(crc32.ChecksumIEEE([]byte(key)))

	// Binary Search: Tìm vị trí server đầu tiên >= hash của key
	idx := sort.Search(len(h.keys), func(i int) bool {
		return h.keys[i] >= hash
	})

	// Nếu idx == len(h.keys), nghĩa là key lớn hơn tất cả node
	// -> Quay vòng về node đầu tiên (Circle structure)
	if idx == len(h.keys) {
		idx = 0
	}

	return h.hashMap[h.keys[idx]]
}
```

---

## 6. Ứng dụng thực tế

1. **Apache Cassandra / Amazon DynamoDB:**
    
    - Dùng Consistent Hashing để chia dữ liệu (Partitioning) ra các node.
        
    - Mỗi node chịu trách nhiệm lưu trữ một khoảng (Token Range) trên vòng tròn.
        
2. **Discord:**
    
    - Dùng để định tuyến (Route) voice chat traffic vào các Voice Server.
        
3. **Load Balancers (NGINX / HAProxy):**
    
    - Chế độ `hash $request_uri consistent;`.
        
    - Giúp User A luôn vào Server X (Sticky Session). Nếu Server X chết, User A chuyển sang Server Y, nhưng User B vẫn ở Server Z (không bị reset session hàng loạt).
        

---

## 7. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Độ phức tạp thuật toán (Time Complexity) để tìm Server là bao nhiêu?
> 
> **A:**
> 
> - Nếu dùng Mảng đã sắp xếp (Sorted Array): **$O(\log N)$** nhờ Binary Search.
>     
> - (Trong đó N là tổng số VNodes).
>     
> - Đây là mức chấp nhận được và rất nhanh.
>     

> [!QUESTION] Q: Tại sao Cassandra lại dùng Consistent Hashing?
> 
> **A:** Để đạt được **High Availability** và **Scalability**.
> 
> Khi thêm node mới vào cluster Cassandra, nó tự động gánh một phần range dữ liệu từ các node khác (Bootstrap) mà không cần tắt hệ thống. Khi node chết, các node hàng xóm (Replicas) sẽ thế chỗ ngay lập tức.

> [!QUESTION] Q: Làm sao để đảm bảo Replication (Sao lưu) với Consistent Hashing?
> 
> **A:**
> 
> Quy tắc: "Lưu tại Node tìm thấy và K Node tiếp theo".
> 
> Ví dụ cần Replication Factor = 3: Dữ liệu sẽ được lưu tại Server X (tìm thấy), và copy thêm sang Server Y, Server Z (2 server nằm kế tiếp X trên vòng tròn).