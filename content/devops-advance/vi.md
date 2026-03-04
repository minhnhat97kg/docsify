---
title: "DevOps - Advance"
tags:
  - "devops"
  - "kubernetes"
  - "k8s"
  - "orchestration"
  - "scaling"
date: "2026-03-04"
author: "nathan.huynh"
summary: "---"
---

---

### 1. Kubernetes (K8s) - Hệ điều hành của Cloud

Bạn đã đóng gói App vào Docker Container. Nhưng ai sẽ bật nó lên? Ai restart nó khi nó chết? Ai scale nó từ 1 lên 100 cái? Đó là việc của K8s.

> [!SUMMARY] Mental Model
> 
> Hãy tưởng tượng K8s là một "Nhạc trưởng" (Orchestrator).
> 
> Docker Container là các "Nhạc công".
> 
> Nhạc trưởng không chơi nhạc, nhưng ông ta quyết định ai chơi, ai nghỉ, và đảm bảo cả dàn nhạc (Cluster) hoạt động hài hòa.

#### Key Concepts cần biết:

1. **Pod:** Đơn vị nhỏ nhất của K8s. Một Pod chứa 1 (hoặc vài) container. Pod chết là mất, K8s sẽ tạo Pod mới thay thế (Ephemeral).
    
2. **Deployment:** Quản lý phiên bản. Nó giúp bạn định nghĩa: "Tôi muốn chạy 3 bản sao (replicas) của Image v1.0". K8s sẽ đảm bảo luôn có đủ 3 cái chạy.
    
3. **Service:** Cổng giao tiếp. Vì Pod sinh ra và chết đi liên tục (IP thay đổi), Service cung cấp một địa chỉ IP tĩnh để các app khác gọi vào.
    
4. **Ingress:** Cánh cổng ra Internet (như NGINX), điều hướng traffic từ domain `bank.com` vào đúng Service bên trong.
    

#### Chiến thuật Zero-downtime (Cực quan trọng cho Bank)

Làm sao deploy code mới mà User không bị ngắt kết nối?

- **Rolling Update:** K8s thay thế từng Pod cũ bằng Pod mới (từng cái một).
    
- **Probes (Que thăm dò):**
    
    - _Liveness Probe:_ "Mày còn sống không?" -> Nếu chết, K8s kill và restart.
        
    - _Readiness Probe:_ "Mày đã khởi động xong chưa, nhận request được chưa?" -> Nếu chưa (đang load DB config), K8s sẽ không bắn traffic vào.
        

---

### 2. CI/CD & GitOps - Tự động hóa quy trình

Code nằm trên Git là code chết. Code chạy trên Server mới là code sống. CI/CD là băng chuyền đưa code ra chiến trường.

![Image of ci cd pipeline workflow diagram](https://encrypted-tbn3.gstatic.com/licensed-image?q=tbn:ANd9GcR6el1ka5n7b2Hq6MunZua6ci3WApntpKHgEJc-JLczb2UYvI2-cnsvujjuSMMbPq3jk-EeiTt10eNlIqEc51ZH5TfqCV223GeKdJCv6qC6xEkFyt8)

Shutterstock

Explore

#### Phân biệt CI và CD

1. **CI (Continuous Integration):**
    
    - Dev push code -> Hệ thống tự động: Build Docker Image -> Chạy Unit Test -> Chạy Security Scan (SonarQube).
        
    - _Mục tiêu:_ Phát hiện lỗi code sớm.
        
2. **CD (Continuous Delivery / Deployment):**
    
    - Tự động deploy Image mới vào môi trường Test/Staging/Production.
        

#### Deployment Strategies (Chiến lược thả lính)

- **Recreate:** Tắt hết cũ, bật mới. (Downtime vài giây -> **Cấm dùng cho Bank**).
    
- **Blue/Green:** Dựng song song 2 môi trường (Blue=Cũ, Green=Mới). Khi Green test ổn -> Switch Router sang Green. (An toàn, nhưng tốn gấp đôi Server).
    
- **Canary (Chim hoàng yến):** Cho 1% user dùng thử bản mới. Nếu không lỗi -> Tăng lên 10% -> 100%. (Rất phổ biến trong Fintech).
    

#### GitOps (Hiện đại)

Thay vì chạy lệnh `kubectl apply` thủ công (dễ sai sót), ta dùng **ArgoCD**.

- Trạng thái mong muốn của hệ thống được lưu trong Git (YAML files).
    
- ArgoCD tự động đồng bộ (Sync) Git vào K8s Cluster.
    
- Muốn đổi config? -> Tạo Pull Request trên Git.
    

---

### 3. Observability - "Ba Trụ Cột" (The Three Pillars)

Khi hệ thống microservices bị lỗi, bạn không thể SSH vào từng server để `tail -f log` được. Bạn cần **Observability**.

#### A. Logs (Nhật ký - ELK Stack / Loki)

- **Hỏi:** "Chuyện gì đã xảy ra?" (Error, Exception).
    
- **Tool:** Elasticsearch, Fluentd, Kibana (EFK) hoặc Loki (nhẹ hơn).
    
- **Lưu ý:** Log phải ở dạng **JSON** để máy dễ đọc (Structured Logging).
    

#### B. Metrics (Số liệu - Prometheus + Grafana)

- **Hỏi:** "Hệ thống có khỏe không?"
    
- **Dữ liệu:** CPU usage, RAM usage, Request/second, Latency p99.
    
- **Alert:** Nếu CPU > 80% trong 5 phút -> Bắn tin nhắn vào Slack/Telegram cho Dev.
    

#### C. Tracing (Truy vết - Jaeger / OpenTelemetry)

- **Hỏi:** "Tại sao request này chậm?"
    
- **Vấn đề:** 1 Request đi qua 5 Service (A -> B -> C -> D). Service C bị chậm làm cả dây chuyền chậm.
    
- **Giải pháp:** Mỗi request có một `TraceID` duy nhất. Hệ thống vẽ ra biểu đồ thời gian (Waterfall) xem request tốn bao nhiêu ms ở từng service. Đây là thứ bắt buộc khi làm **Microservices**.
    

---

### 4. Infrastructure as Code (IaC) - Terraform

Đừng bao giờ click chuột trên AWS/Google Cloud Console để tạo Server. Hãy viết code.

> [!SUMMARY] Terraform
> 
> Bạn viết 1 file `main.tf`:
> 
> `resource "aws_instance" "db" { ami = "...", instance_type = "t3.micro" }`
> 
> Chạy `terraform apply`. Terraform sẽ tự động gọi API của AWS để tạo đúng server đó.
> 
> Nếu bạn sửa `t3.micro` thành `t3.large` và chạy lại, Terraform tự động nâng cấp server.

- **Lợi ích:**
    
    - **Reproducibility:** Dựng lại toàn bộ hệ thống ngân hàng sang một Region mới chỉ trong 15 phút.
        
    - **Version Control:** Biết ai đã sửa cấu hình hạ tầng, vào lúc nào (thông qua Git Commit).
        
    - **State Locking:** Tránh việc 2 ông Dev cùng sửa hạ tầng một lúc gây xung đột.
        

---

### Câu hỏi phỏng vấn thực chiến (DevOps cho Dev)

> [!QUESTION] Q: Sự khác biệt giữa Docker Swarm và Kubernetes?
> 
> **A:**
> 
> - **Docker Swarm:** Dễ dùng, tích hợp sẵn trong Docker, nhưng tính năng hạn chế. Phù hợp team nhỏ, dự án đơn giản.
>     
> - **Kubernetes:** Phức tạp, steep learning curve, nhưng là chuẩn công nghiệp. Mạnh mẽ về Scaling, Self-healing, Ecosystem khổng lồ (Helm, Istio...). Ngân hàng 100% dùng K8s (hoặc OpenShift - bản K8s enterprise).
>     

> [!QUESTION] Q: Làm sao để debug một Pod đang bị CrashLoopBackOff trong K8s?
> 
> **A:** Quy trình chuẩn:
> 
> 1. `kubectl get pods` -> Xem trạng thái.
>     
> 2. `kubectl describe pod <tên-pod>` -> Xem Events (có bị thiếu RAM/CPU, hay liveness probe fail?).
>     
> 3. `kubectl logs <tên-pod> --previous` -> Xem log của lần crash trước đó (Quan trọng, vì pod hiện tại mới khởi động lại chưa có log).
>     

> [!QUESTION] Q: Prometheus lưu dữ liệu kiểu gì? Pull hay Push?
> 
> **A:**
> 
> Prometheus dùng cơ chế **PULL**.
> 
> Nó định kỳ (ví dụ 15s) gọi vào API `/metrics` của App để "kéo" số liệu về.
> 
> (Khác với các hệ thống cũ thường là App "đẩy" - Push log về server).
> 
> _Ưu điểm của Pull:_ Prometheus không bị quá tải nếu App gửi quá nhiều data; App không cần biết IP của Prometheus.

---
