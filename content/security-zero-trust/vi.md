---
title: "Security - Zero Trust"
tags:
  - "security"
  - "zerotrust"
  - "zta"
  - "infrastructure"
  - "beyondcorp"
  - "nist"
  - "cloud-native"
date: "2026-03-04"
author: "nathan.huynh"
summary: "---"
---

---

---

## 1. Bản chất: "Never Trust, Always Verify"

Về mặt kỹ thuật, **Zero Trust** là một mô hình bảo mật loại bỏ khái niệm "tin tưởng mặc định" (implicit trust). Thay vì tin tưởng bất cứ ai dựa trên vị trí mạng của họ (ví dụ: đang ở trong mạng nội bộ/VPN), ZTA yêu cầu mọi yêu cầu truy cập phải được xác thực, cấp quyền và kiểm tra liên tục trước khi được chấp nhận.

> [!SUMMARY] Mental Model: Khách sạn cao cấp vs. Lâu đài trung cổ
> 
> **Mô hình truyền thống (Castle-and-Moat):** Giống như một tòa lâu đài có tường cao hào sâu. Nếu bạn đi qua cổng chính, bạn được tự do đi lại trong sân, vào bếp hay phòng khách vì "bạn đã ở trong lâu đài". Tuy nhiên, nếu giặc đã leo tường vào được, chúng cũng có toàn quyền y như bạn.
> 
> **Mô hình Zero Trust (Modern Hotel):** Bạn vào sảnh khách sạn. Để lên thang máy, bạn cần thẻ phòng. Thẻ đó chỉ cho phép bạn lên đúng tầng của mình. Để vào phòng, bạn quẹt thẻ lại lần nữa. Để dùng Wi-Fi hay Mini-bar, bạn phải xác thực thêm. Kể cả khi bạn đã ở trong phòng, nhân viên an ninh vẫn có thể vô hiệu hóa thẻ của bạn ngay lập tức nếu phát hiện bất thường.
> 
> **Khác biệt lớn nhất:** ZTA thu hẹp "vùng tin tưởng" (Trust Zone) xuống mức nhỏ nhất có thể — đôi khi chỉ là một ứng dụng hoặc một dòng dữ liệu duy nhất.

---

## 2. Giải phẫu (Anatomy/Architecture)

Kiến trúc Zero Trust được xây dựng dựa trên sự phân tách giữa **Control Plane** (Mặt phẳng điều khiển) và **Data Plane** (Mặt phẳng dữ liệu).

### Các thành phần cốt lõi:

1. **Policy Decision Point (PDP):** Bộ não điều khiển. Nó quyết định xem một User/Service có được truy cập tài nguyên hay không dựa trên Policy.
    
2. **Policy Enforcement Point (PEP):** Cánh cổng gác đường (ví dụ: API Gateway, Sidecar Proxy). Nó thực thi quyết định từ PDP.
    
3. **Implicit Trust Zone:** Tài nguyên thực tế mà bạn muốn bảo vệ.
    

### Minh họa Policy-as-Code (Sử dụng OPA - Open Policy Agent)

Trong ZTA, chính sách không nên "hard-code". Chúng ta sử dụng ngôn ngữ khai báo để PDP có thể tính toán logic.

Code snippet

```
# Ngôn ngữ: Rego (OPA)
package hcm_city.authz

default allow = false

# Chỉ cho phép truy cập nếu:
allow {
    input.method == "GET"
    input.subject.role == "developer"
    input.subject.location == "office"  # Thuộc tính môi trường
    input.resource.type == "source_code"
    not is_compromised(input.subject.user_id) # Kiểm tra rủi ro liên tục
}

is_compromised(user_id) {
    # Giả định query từ một hệ thống Threat Intel
    data.compromised_users[user_id]
}
```

---

## 3. So sánh: Perimeter Security vs. Zero Trust

|**Đặc điểm**|**Perimeter Security (Truyền thống)**|**Zero Trust Architecture**|
|---|---|---|
|**Giả định**|Tin tưởng mọi thứ bên trong mạng nội bộ.|Không tin tưởng bất kỳ ai, bất kỳ đâu.|
|**Xác thực**|Một lần duy nhất (Single Sign-On tại cửa ngõ).|Xác thực liên tục (Continuous Validation).|
|**Phạm vi bảo mật**|Network-centric (IP, Subnet, VLAN).|Resource-centric (User, Device, App).|
|**Khả năng chống lại tấn công**|Dễ bị "Lateral Movement" (di chuyển ngang).|Chặn đứng di chuyển ngang bằng Micro-segmentation.|
|**Trải nghiệm người dùng**|Phụ thuộc vào VPN (chậm, phiền).|Truy cập trực tiếp qua IAP (nhanh, mượt).|

---

## 4. Vấn đề nhức nhối & Giải pháp

### Vấn đề 1: Độ trễ (Performance Latency)

Vì mỗi request đều phải qua PDP để "xin phép", hệ thống có thể bị chậm lại.

- **Giải pháp:** Sử dụng **Edge Authorization**. Đẩy các Policy nhẹ xuống PEP (Sidecar) để tính toán tại chỗ, chỉ gọi về PDP trung tâm khi cần các quyết định phức tạp.
    

### Vấn đề 2: Sự phức tạp khi triển khai (Operational Complexity)

Chuyển đổi sang Zero Trust không thể làm trong một đêm. Nó đòi hỏi sự phối hợp giữa Identity, Network và App Team.

- **Giải pháp:** Triển khai theo lộ trình **"Identity-First"**. Bắt đầu bằng việc áp dụng MFA (Multi-Factor Auth) mạnh mẽ, sau đó mới đến mTLS cho Microservices và cuối cùng là các Policy dựa trên ngữ cảnh (Context-aware).
    

---

## 5. Security/Performance Checklist

1. **Identity is the new Perimeter:** Mỗi thực thể (người hoặc máy) phải có một danh tính số duy nhất và mạnh (ví dụ: SPIFFE ID).
    
2. **Device Posture Check:** Không chỉ xác thực User, phải check cả thiết bị (Máy có cài đủ phần mềm diệt virus không? Có bị jailbreak không?).
    
3. **Micro-segmentation:** Chia nhỏ mạng nội bộ. Service A và Service B không được thấy nhau nếu không có luồng nghiệp vụ liên quan.
    
4. **Least Privilege:** Cấp quyền vừa đủ và có thời hạn (Just-in-time access).
    
5. **Encrypt Everything:** Luôn mã hóa dữ liệu cả khi đang truyền (Transit) và khi đang nghỉ (At rest).
    

---

## 6. Góc phỏng vấn thực chiến

> [!QUESTION] Q1: Tại sao VPN không được coi là Zero Trust?
> 
> **A:** VPN dựa trên niềm tin vào vị trí mạng. Một khi bạn đã kết nối VPN thành công, bạn thường có thể nhìn thấy và truy cập vào nhiều tài nguyên trong mạng nội bộ mà bạn không thực sự cần. Zero Trust thay thế VPN bằng "Identity-Aware Proxy", nơi bạn chỉ thấy đúng ứng dụng mình được phép.

> [!QUESTION] Q2: "Lateral Movement" là gì và ZTA ngăn chặn nó như thế nào?
> 
> **A:** Lateral Movement là kỹ thuật hacker chiếm được một server yếu trong mạng, rồi từ đó dùng "niềm tin nội bộ" để tấn công các server quan trọng hơn (như DB). ZTA ngăn chặn bằng mTLS và Micro-segmentation: Kể cả khi hacker chiếm được Server A, chúng không có Certificate hợp lệ để gọi sang Server B.

> [!QUESTION] Q3: Làm sao để xử lý các ứng dụng cũ (Legacy) không hỗ trợ mTLS hay các chuẩn auth hiện đại trong mô hình Zero Trust?
> 
> **A:** Chúng ta sử dụng mô hình **"Sidecar Proxy"** hoặc **"Ambassador"**. Ứng dụng cũ vẫn chạy HTTP thường, nhưng mọi traffic đi ra/vào đều qua một Proxy (như Envoy). Proxy này sẽ chịu trách nhiệm thực hiện mTLS và xác thực với hệ thống Zero Trust thay cho ứng dụng cũ.

> [!QUESTION] Q4: Theo bạn, thành phần nào là quan trọng nhất trong ZTA?
> 
> **A:** Đó là **Identity (Danh tính)**. Không có định danh chính xác và tin cậy cho cả User và Machine, mọi chính sách phân quyền đều trở nên vô nghĩa.

**Bạn có muốn mình demo cách triển khai một "Identity-Aware Proxy" đơn giản để bảo vệ một ứng dụng nội bộ mà không cần dùng đến VPN không?**