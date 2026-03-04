---
title: "Security - Threat Modeling & STRIDE"
tags:
  - "security"
  - "threat-modeling"
  - "stride"
  - "sdlc"
  - "backend"
  - "architecture"
  - "risk-management"
date: "2026-03-04"
author: "nathan.huynh"
summary: "---"
---

---

---

## 1. Bản chất: "Phòng bệnh hơn chữa bệnh"

Về mặt chuyên môn, **Threat Modeling** là một quá trình phân tích hệ thống một cách có cấu trúc nhằm xác định các mục tiêu bảo mật, các mối đe dọa tiềm tàng và các biện pháp giảm thiểu. **STRIDE** là mô hình do Microsoft phát triển, phân loại các mối đe dọa thành 6 nhóm dựa trên các thuộc tính của bảo mật (CIA Triad + Authentication/Authorization).

> [!SUMMARY] Mental Model: Bản thiết kế chống trộm
> 
> **Mô hình truyền thống:** Giống như bạn xây xong ngôi nhà, rồi mới đi thuê bảo vệ đứng ở cửa. Nếu kẻ trộm vào bằng đường ống khói hoặc cửa sổ tầng 2, bạn hoàn toàn bị động.
> 
> **Threat Modeling (STRIDE):** Giống như khi kiến trúc sư vẽ bản thiết kế nhà, bạn ngồi xuống và đặt câu hỏi cho từng chi tiết:
> 
> - "Cái khóa cửa này có dễ bị giả chìa không?" (**S**poofing)
>     
> - "Kẻ trộm có thể cưa song sắt cửa sổ không?" (**T**ampering)
>     
> - "Làm sao để trộm không thể chối là nó đã đột nhập?" (**R**epudiation)
>     
> 
> **Khác biệt lớn nhất:** Bạn tìm ra lỗ hổng **trên giấy** trước khi viết dòng code đầu tiên. Chi phí sửa lỗi ở giai đoạn thiết kế rẻ hơn gấp 10-100 lần so với khi đã lên Production.

---

## 2. Giải phẫu (Anatomy): 6 "Sát thủ" trong STRIDE

Để thực hiện STRIDE, ta thường bắt đầu bằng một **Data Flow Diagram (DFD)** để xem dữ liệu đi từ đâu đến đâu.

|**Chữ cái**|**Mối đe dọa**|**Vi phạm thuộc tính**|**Ví dụ thực tế**|
|---|---|---|---|
|**S**|**Spoofing** (Giả mạo)|Authentication|Dùng JWT giả, giả danh một Service khác.|
|**T**|**Tampering** (Can thiệp)|Integrity|Sửa đổi giá sản phẩm trong gói tin gửi lên API.|
|**R**|**Repudiation** (Chối bỏ)|Non-repudiation|User thực hiện giao dịch rồi nói "không phải tôi".|
|**I**|**Info Disclosure** (Lộ tin)|Confidentiality|Lộ Database connection string qua log.|
|**D**|**Denial of Service** (Từ chối DV)|Availability|Gửi hàng triệu request để làm sập Server.|
|**E**|**Elevation of Privilege** (Leo thang)|Authorization|User thường sửa `role_id` để thành Admin.|

### Minh họa: Một bản ghi Threat Model (JSON)

Trong các hệ thống hiện đại, Threat Model có thể được lưu trữ dưới dạng code (Threats-as-Code).

JSON

```
{
  "component": "Order-Service API",
  "threats": [
    {
      "category": "Tampering",
      "description": "Hacker modifies the order_amount in the POST /orders payload.",
      "mitigation": "Perform server-side validation and sign the payload if necessary.",
      "risk_level": "High"
    },
    {
      "category": "Elevation of Privilege",
      "description": "Regular user accesses /admin/delete-order endpoint.",
      "mitigation": "Implement RBAC middleware and validate JWT claims.",
      "risk_level": "Critical"
    }
  ]
}
```

---

## 3. So sánh: STRIDE vs. PASTA

Có nhiều bộ khung khác nhau, nhưng STRIDE và PASTA là hai cái tên phổ biến nhất cho Developer.

|**Đặc điểm**|**STRIDE**|**PASTA (Process for Attack Simulation)**|
|---|---|---|
|**Tiếp cận**|Developer-centric (Dựa trên hệ thống).|Risk-centric (Dựa trên mục tiêu kinh doanh).|
|**Độ khó**|Dễ học, dễ áp dụng nhanh.|Phức tạp, cần sự phối hợp với Business.|
|**Mục tiêu**|Tìm lỗi kỹ thuật.|Tìm lỗi chiến lược và rủi ro tài chính.|
|**Use Case**|Team Dev phân quyền/bảo mật Microservices.|Ngân hàng/Tập đoàn lớn lập kế hoạch an ninh.|

---

## 4. Vấn đề nhức nhối & Giải pháp

### Vấn đề 1: Phân tích quá đà (Analysis Paralysis)

Nếu bạn phân tích từng cái function nhỏ nhất, bạn sẽ không bao giờ xong.

- **Giải pháp:** Áp dụng mô hình 80/20. Tập trung STRIDE vào các **Entry Points** (điểm tiếp nhận request từ ngoài) và các luồng dữ liệu nhạy cảm (Thanh toán, PII).
    

### Vấn đề 2: Threat Model bị "bỏ xó"

Vẽ xong rồi để đó, code vẫn cứ viết theo kiểu cũ.

- **Giải pháp:** Tích hợp Threat Modeling vào **Definition of Done (DoD)**. Một tính năng chỉ được coi là hoàn thành nếu đã được review qua STRIDE.
    

---

## 5. Security Checklist cho Threat Modeling

1. **Vẽ DFD chính xác:** Nếu bạn thiếu một luồng dữ liệu, bạn sẽ bỏ lỡ toàn bộ mối đe dọa trên luồng đó.
    
2. **Xác định ranh giới (Trust Boundaries):** Nơi dữ liệu đi từ vùng ít tin tưởng (Public Internet) sang vùng tin tưởng (Internal Network). Đây là nơi "nóng" nhất.
    
3. **Cập nhật liên tục:** Mỗi khi thêm một công nghệ mới (ví dụ: dùng Redis làm cache), phải update lại Threat Model.
    
4. **Đánh giá mức độ ưu tiên:** Sử dụng công thức $Risk = Probability \times Impact$ để biết nên sửa lỗi nào trước.
    

---

## 6. Góc phỏng vấn thực chiến

> [!QUESTION] Q1: Làm sao để phân biệt Spoofing và Elevation of Privilege?
> 
> **A:** **Spoofing** là "tôi giả làm người khác" (ví dụ: dùng ID của sếp). **Elevation of Privilege** là "tôi vẫn là tôi, nhưng tôi làm được việc của sếp" (ví dụ: tôi là nhân viên nhưng vào được trang quản trị lương).

> [!QUESTION] Q2: Bạn sẽ làm gì nếu phát hiện một mối đe dọa (Threat) nhưng team Business không cho phép sửa vì tốn thời gian?
> 
> **A:** Với vai trò Tech Lead, tôi sẽ lập bảng đánh giá rủi ro: Nếu không sửa, thiệt hại tiềm tàng là bao nhiêu tiền/uy tín. Tôi sẽ đưa ra các lựa chọn: (1) Sửa triệt để, (2) Dùng biện pháp tạm thời (Workaround), hoặc (3) Chấp nhận rủi ro và ký biên bản xác nhận. Mục tiêu là để Business hiểu cái giá của việc "đi tắt".

> [!QUESTION] Q3: Tại sao "Repudiation" lại cực kỳ quan trọng trong hệ thống Banking?
> 
> **A:** Vì trong tài chính, tính minh bạch là sống còn. Nếu một user chuyển tiền đi rồi chối rằng "không phải tôi, hệ thống bị lỗi", ngân hàng sẽ mất tiền. Giải pháp thường là dùng **Digital Signature** (chữ ký số) và **Audit Log** không thể xóa (Immutable Log).

**Bạn có muốn mình cùng bạn thực hiện thử một buổi Threat Modeling ngắn cho một tính năng cụ thể (ví dụ: "Quên mật khẩu" hoặc "Thanh toán ví điện tử") không?**