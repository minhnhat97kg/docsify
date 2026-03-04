---
title: "AWS - IAM Roles & Policies (Least Privilege)"
tags:
  - "security"
  - "cloud"
  - "aws"
  - "iam"
  - "devops"
  - "terraform"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Trong bảo mật Cloud, tư duy mặc định phải là \"Zero Trust\" (Không tin ai cả)."
---

## 1. Nguyên lý cốt lõi: Least Privilege (Quyền tối thiểu)

Trong bảo mật Cloud, tư duy mặc định phải là **"Zero Trust"** (Không tin ai cả).

**Principle of Least Privilege (PoLP)** phát biểu rằng:

> Một thực thể (User/Service) chỉ được cấp **những quyền hạn tối thiểu nhất** cần thiết để hoàn thành công việc, trong **thời gian ngắn nhất** có thể.

- **Sai (Tiện tay):** Cấp quyền `AdministratorAccess` hoặc `s3:*` cho một EC2 instance chỉ cần đọc 1 file log.
    
- **Đúng (Bảo mật):** Chỉ cấp quyền `s3:GetObject` trên đúng cái Bucket `my-app-logs`.
    

---

## 2. User vs. Role: Sự khác biệt sống còn

Rất nhiều Developer nhầm lẫn giữa IAM User và IAM Role.

### A. IAM User (Con người)

- Đại diện cho một người cụ thể (Developer A, SysAdmin B).
    
- Có thông tin đăng nhập lâu dài (Long-term credentials): Password hoặc Access Key (`AKIA...`).
    
- **Rủi ro:** Nếu Hacker lấy được Access Key, hắn có thể dùng mãi mãi cho đến khi bạn phát hiện và xoá nó.
    

### B. IAM Role (Cái mũ / Chức danh)

- Không gắn liền với một người cụ thể. Nó là một tập hợp các quyền hạn.
    
- **Không có Password/Key cố định.**
    
- **Cơ chế:** Ai muốn dùng Role thì phải **"Assume Role"** (Đội mũ lên). Hệ thống sẽ cấp cho một **Temporary Token** (chìa khóa tạm thời) chỉ sống trong 1 giờ. Hết 1 giờ tự hủy.
    
- **Use Case:** Dùng cho **Máy móc** (EC2, Lambda, K8s Pods) hoặc cho User muốn chuyển đổi quyền hạn.
    

---

## 3. Cấu trúc của một IAM Policy

Policy là một file JSON định nghĩa "Ai được làm gì". Cấu trúc chuẩn gồm 4 phần:

1. **Effect:** `Allow` hoặc `Deny`.
    
2. **Action:** Hành động cụ thể (VD: `s3:ListBucket`, `dynamodb:PutItem`).
    
3. **Resource:** Tài nguyên chịu tác động (ARN - Amazon Resource Name).
    
4. **Condition (Optional):** Điều kiện ngữ cảnh (VD: Chỉ cho phép IP văn phòng, chỉ cho phép trong giờ hành chính).
    

**Ví dụ: Policy chuẩn Least Privilege**

``` json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowReadSpecificFile",
            "Effect": "Allow",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::my-sensitive-bucket/reports/*",
            "Condition": {
                "IpAddress": {"aws:SourceIp": "203.0.113.0/24"}
            }
        }
    ]
}
```

---

## 4. Cơ chế Assume Role (Kịch bản thực tế)

Làm sao một App chạy trên EC2 Server truy cập được vào S3 Bucket mà **không cần lưu Access Key trong code**?

1. **Setup:** Tạo một IAM Role có quyền đọc S3. Gắn Role này vào EC2 Instance (Instance Profile).
    
2. **Runtime:**
    
    - App (dùng AWS SDK) gọi đến dịch vụ metadata nội bộ của AWS (`169.254.169.254`).
        
    - Yêu cầu: "Cho tôi xin credential của Role hiện tại".
        
3. **STS (Security Token Service):** Trả về `AccessKey`, `SecretKey`, và `SessionToken` (Hạn dùng ngắn).
    
4. **Access:** App dùng bộ key tạm thời đó để gọi S3 API.
    
5. **Rotate:** SDK tự động xin cấp lại key mới khi key cũ sắp hết hạn. -> **Developer không cần quản lý key.**
    

---

## 5. IAM Policy Evaluation Logic (Logic Quyết định)

Khi một request gửi đến, AWS quyết định Cho phép hay Chặn theo quy trình nào?

1. **Mặc định là DENY (Implicit Deny):** Nếu không nói gì -> Cấm.
    
2. **Explicit ALLOW:** Có policy nào nói "Allow" không? Nếu có -> Xem xét cho qua.
    
3. **Explicit DENY:** Có policy nào nói "Deny" không?
    
    - **QUY TẮC VÀNG:** **Explicit Deny luôn thắng Explicit Allow.**
        
    - Ví dụ: Policy A cho phép `s3:*`. Policy B (Permission Boundary) cấm `s3:DeleteBucket`. -> Kết quả: Được làm tất cả trừ Delete.
        

---

## 6. Infrastructure as Code (Terraform)

Đừng click chuột trên Console để tạo quyền (dễ sai sót và khó audit). Hãy dùng Terraform.

Terraform

``` terraform
# 1. Tạo Policy (Document)
data "aws_iam_policy_document" "s3_read" {
  statement {
    effect  = "Allow"
    actions = ["s3:GetObject"]
    resources = ["arn:aws:s3:::my-app-data/*"]
  }
}

# 2. Tạo Role
resource "aws_iam_role" "app_role" {
  name = "my-app-role"
  
  # Trust Policy: Ai được phép đội cái mũ này? (EC2 được phép)
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

# 3. Gắn Policy vào Role
resource "aws_iam_role_policy" "attach" {
  name   = "s3-read-policy"
  role   = aws_iam_role.app_role.id
  policy = data.aws_iam_policy_document.s3_read.json
}
```

---

## 7. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Làm sao để Developer truy cập vào môi trường Production an toàn?
> 
> **A:** Không tạo IAM User trên tài khoản Prod.
> 
> Sử dụng mô hình **Bastion Account** hoặc **Identity Federation**.
> 
> 1. Developer login vào tài khoản Dev (hoặc dùng Google/Okta Single Sign-On).
>     
> 2. Từ tài khoản Dev, Developer thực hiện lệnh `AssumeRole` sang một Role đặc biệt trên tài khoản Prod.
>     
> 3. Role trên Prod được cấu hình chặt chẽ (chỉ đọc log, không được xóa DB). Mọi hành động đều được log lại qua CloudTrail.
>     

> [!QUESTION] Q: Bạn xử lý thế nào khi lỡ commit Access Key lên GitHub?
> 
> **A:** Quy trình ứng phó sự cố (Incident Response):
> 
> 4. **Revoke ngay lập tức:** Vào IAM Console disable hoặc delete key đó.
>     
> 5. **Rotate:** Tạo key mới cho ứng dụng.
>     
> 6. **Check Logs:** Quét AWS CloudTrail xem trong khoảng thời gian key bị lộ, Hacker đã dùng nó làm gì (Đào coin? Xóa dữ liệu?).
>     
> 7. **Prevention:** Cài đặt `git-secrets` hoặc pre-commit hook để chặn commit key lần sau.
>     

> [!QUESTION] Q: Policy Boundary là gì?
> 
> **A:** Là cái "Vòng kim cô".
> 
> Dù Admin có cấp cho bạn quyền `AdministratorAccess` (Full quyền), nhưng nếu bạn bị gán một Permission Boundary chỉ cho phép `s3:*`, thì bạn cũng **chỉ dùng được S3**.
> 
> Nó dùng để giới hạn quyền tối đa mà một User/Role có thể có, bất kể họ được cấp thêm policy gì sau này. Rất hữu ích khi phân quyền cho các team Dev tự quản lý tài nguyên của mình.
