---
title: "AWS - Security Groups vs NACL"
tags:
  - "aws"
  - "security"
  - "networking"
  - "vpc"
  - "firewall"
  - "devops"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Để bảo vệ server trên AWS, chúng ta có 2 lớp tường lửa hoạt động song song."
---

## 1. Bản chất: Hai lớp "Áo giáp"

Để bảo vệ server trên AWS, chúng ta có 2 lớp tường lửa hoạt động song song.

- **Network ACL (NACL):** Như **Cổng bảo vệ** của tòa nhà (Subnet). Nó kiểm soát ai được vào khu phố.
    
- **Security Group (SG):** Như **Cửa nhà** của từng căn hộ (Instance). Nó kiểm soát ai được vào phòng ngủ.
    

> [!SUMMARY] Quy tắc bất di bất dịch
> 
> Traffic muốn vào được Server phải đi qua **CẢ HAI** lớp:
> 
> Internet -> NACL (Allow?) -> Security Group (Allow?) -> EC2.

---

## 2. Security Group (SG) - Tường lửa "Thông minh" (Stateful)

Đây là lớp bảo vệ **quan trọng nhất** mà bạn dùng 99% thời gian.

- **Phạm vi:** Gắn trực tiếp vào **Instance** (EC2, RDS, ELB).
    
- **Cơ chế:** **Stateful (Có trạng thái)**.
    
    - _Nghĩa là:_ Nếu bạn cho phép traffic đi vào (Inbound) ở port 80, thì AWS **tự động** cho phép traffic trả lời đi ra (Outbound) mà không cần cấu hình gì thêm.
        
- **Luật:** Chỉ có **ALLOW**. (Mặc định là Deny All. Bạn chỉ có thể liệt kê những ai ĐƯỢC phép vào. Không thể viết luật "Cấm IP 1.2.3.4").
    

---

## 3. Network ACL (NACL) - Tường lửa "Thô sơ" (Stateless)

Đây là lớp bảo vệ bổ trợ ở mức mạng.

- **Phạm vi:** Gắn vào **Subnet**. Tất cả EC2 trong subnet đó đều chịu ảnh hưởng.
    
- **Cơ chế:** **Stateless (Không trạng thái)**.
    
    - _Nghĩa là:_ Nếu bạn cho phép Inbound port 80, traffic vào được. NHƯNG traffic trả lời đi ra sẽ **bị chặn** trừ khi bạn mở explicit Outbound rule cho các **Ephemeral Ports** (1024-65535).
        
- **Luật:** Có cả **ALLOW** và **DENY**.
    
    - Sắp xếp theo thứ tự ưu tiên (Rule Number). Số nhỏ ưu tiên trước.
        

---

## 4. So sánh chi tiết

|**Đặc điểm**|**Security Group (SG)**|**Network ACL (NACL)**|
|---|---|---|
|**Cấp độ**|Instance (EC2/RDS/Container)|Subnet (Mạng lưới)|
|**Trạng thái**|**Stateful:** Return traffic tự động được cho phép.|**Stateless:** Phải mở explicit Allow cho cả chiều về (Outbound).|
|**Loại Rules**|Chỉ **Allow**. (Mặc định chặn hết).|**Allow** và **Deny**.|
|**Thứ tự**|Không quan trọng (Tất cả rule được xét duyệt).|Quan trọng (Theo số thứ tự Rule #).|
|**Use Case**|Whitelist access (App A được gọi DB B).|Blacklist IP (Chặn IP Hacker), chặn cả dải mạng.|

---

## 5. Cạm bẫy Ephemeral Ports (Cổng tạm)

Rất nhiều người mới cấu hình NACL bị lỗi: _Web Server nhận được request nhưng Client bị timeout._

**Lý do:** Quên mở chiều về (Outbound).

Khi Client (Port 50000) gọi Server (Port 80):

1. **Inbound:** Client -> Server (Dst Port 80). -> **NACL phải Allow Port 80.**
    
2. **Outbound:** Server trả lời -> Client (Dst Port 50000). -> **NACL phải Allow Port 1024-65535.**
    

_Nếu bạn chặn Outbound 1024-65535, gói tin trả lời sẽ bị NACL giết chết ngay tại cửa Subnet._

---

## 6. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Tôi muốn chặn 1 IP cụ thể đang tấn công tôi, tôi nên dùng SG hay NACL?
> 
> **A:**
> 
> Dùng **NACL** (hoặc WAF).
> 
> Security Group KHÔNG có rule DENY, nên không thể chặn 1 IP cụ thể. Bạn chỉ có thể whitelist IP tốt.
> 
> NACL cho phép tạo Rule #1: `DENY Source: 1.2.3.4`, Rule #100: `ALLOW ALL`.

> [!QUESTION] Q: Một request đi từ Internet vào EC2. Nó bị SG chặn nhưng NACL cho phép. EC2 có nhận được không?
> 
> **A:**
> 
> **Không.**
> 
> Gói tin phải qua được **CẢ HAI** cửa. Nếu NACL cho qua (vào được Subnet) nhưng SG chặn (không vào được Instance) thì gói tin vẫn bị drop.

> [!QUESTION] Q: Tại sao trong kiến trúc 3-Tier, người ta ít khi chỉnh sửa NACL mà chỉ tập trung vào SG?
> 
> **A:**
> 
> Vì NACL quá phức tạp (Stateless) và dễ gây lỗi hệ thống diện rộng (chặn nhầm traffic trả về).
> 
> Best Practice của AWS là: Để NACL mặc định (Allow All), và quản lý chặt chẽ bằng Security Group (Defense in Depth vẫn tốt, nhưng Operational Overhead phải thấp). Chỉ dùng NACL khi thực sự cần chặn một dải mạng lớn.

---

**Next Step:**

Chúng ta đã đi qua hầu hết các service cốt lõi của AWS. Để hoàn thiện bức tranh Cloud Native, bạn có muốn tìm hiểu về **Infrastructure as Code (IaC)** chuyên sâu với **Terraform State Management** (cách làm việc nhóm mà không bị đè file state lên nhau) không?
