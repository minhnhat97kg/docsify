---
title: "DevOps - Docker Multistage Builds (Golang)"
tags:
  - "devops"
  - "aws"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Khi mới học Docker với Go, ta thường viết Dockerfile thế này:"
---

## 1. Vấn đề: Image "Béo phì"

Khi mới học Docker với Go, ta thường viết Dockerfile thế này:

Dockerfile

```dockerfile
# Cách làm ngây thơ (Single Stage)
FROM golang:1.21
WORKDIR /app
COPY . .
RUN go build -o myapp main.go
CMD ["./myapp"]
```

> [!DANGER] Hậu quả
> 
> - **Kích thước:** Image nặng **800MB - 1GB**.
>     
> - **Lý do:** Nó chứa cả Source Code + Go Compiler + Toàn bộ Linux OS (Debian/Ubuntu) + Thư viện không cần thiết.
>     
> - **Bảo mật:** Hacker xâm nhập được container sẽ có đủ công cụ (gcc, apt, shell) để tấn công tiếp.
>     

**Giải pháp:** Go là ngôn ngữ biên dịch (Compiled Language). Kết quả cuối cùng là một **file Binary** duy nhất. Nó không cần Go Compiler hay Source code để chạy.

-> **Multistage Build:** Dùng một image to để build, sau đó copy file Binary sang một image siêu nhỏ để chạy.

---

## 2. The "Golden" Dockerfile cho Golang

Đây là template chuẩn mực cho môi trường Production (Bank/Fintech), tối ưu xuống còn **~10MB - 20MB**.

Dockerfile

```dockerfile
# --- STAGE 1: Builder (Môi trường Build) ---
FROM golang:1.21-alpine AS builder

# 1. Cài đặt chứng chỉ SSL và git (nếu cần tải private module)
RUN apk update && apk add --no-cache git ca-certificates tzdata

# 2. Tạo user non-root (Bảo mật)
ENV USER=appuser
ENV UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    "${USER}"

WORKDIR /app

# 3. Tối ưu Layer Caching (Quan trọng)
# Copy go.mod trước để cache các thư viện.
# Nếu code thay đổi nhưng thư viện không đổi -> Docker sẽ bỏ qua bước download này.
COPY go.mod go.sum ./
RUN go mod download

# 4. Build Binary
COPY . .
# CGO_ENABLED=0: Tắt liên kết thư viện C động (Static Linking) -> Để chạy được trên Scratch
# -ldflags="-w -s": Loại bỏ thông tin debug (DWARF) -> Giảm size binary thêm 20-30%
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o /go/bin/myapp main.go

# --- STAGE 2: Runner (Môi trường Chạy) ---
# Dùng 'scratch' - Image rỗng hoàn toàn (0 MB)
FROM scratch

# Copy các file cần thiết từ Builder sang
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /etc/passwd /etc/passwd
COPY --from=builder /etc/group /etc/group

# Copy file thực thi
COPY --from=builder /go/bin/myapp /myapp

# Sử dụng user non-root đã tạo
USER appuser:appuser

ENTRYPOINT ["/myapp"]
```

---

## 3. Các kỹ thuật tối ưu cốt lõi

### A. `scratch` vs. `alpine`

- **Alpine Linux (~5MB):** Là một bản Linux siêu nhỏ. Có shell (`/bin/sh`), có package manager (`apk`).
    
    - _Ưu điểm:_ Có thể `docker exec` vào để debug, ping, curl.
        
    - _Dùng khi:_ Cần debug hoặc App cần thư viện C bên ngoài.
        
- **Scratch (0MB):** Image rỗng tuếch. Không có gì cả, kể cả kernel (nó dùng kernel của máy host).
    
    - _Ưu điểm:_ Size nhỏ nhất có thể. **Bảo mật tuyệt đối** (Hacker vào được cũng không có shell để gõ lệnh).
        
    - _Dùng khi:_ Production (Deploy & Forget).
        

### B. `CGO_ENABLED=0` (Static Linking)

Mặc định, Go có thể link động tới thư viện C chuẩn (`glibc` hoặc `musl`) của hệ điều hành.

- Nếu dùng `scratch` (không có OS), binary sẽ lỗi "File not found" dù file nằm sờ sờ ra đó.
    
- **Giải pháp:** `CGO_ENABLED=0` báo cho Go compiler biết: _"Hãy nhúng tất cả mọi thứ mày cần vào file binary đi. Tao không muốn phụ thuộc OS."_
    

### C. Layer Caching (Thứ tự Copy)

Docker build theo từng lớp (Layer). Nếu lớp trước không đổi, nó dùng Cache.

- **Tệ:** `COPY . .` -> `RUN go mod download`. (Sửa 1 dòng code -> Docker tải lại toàn bộ thư viện -> Chậm).
    
- **Tốt:** `COPY go.mod ...` -> `RUN go mod download` -> `COPY . .`. (Sửa code -> Docker dùng lại cache thư viện -> Build siêu nhanh).
    

---

## 4. Bảo mật: SSL Certs & Non-root User

Khi dùng `FROM scratch`, bạn sẽ gặp 2 lỗi phổ biến:

1. **Lỗi gọi API:** `x509: certificate signed by unknown authority`.
    
    - _Lý do:_ `scratch` không có danh sách Root CA (như GlobalSign, DigiCert...) nên không verify được HTTPS.
        
    - _Fix:_ Phải copy `/etc/ssl/certs/ca-certificates.crt` từ image builder sang.
        
2. **Lỗi bảo mật:** App chạy quyền `root`.
    
    - _Lý do:_ Container mặc định là root.
        
    - _Fix:_ Tạo user trong builder, copy file `/etc/passwd` sang runner và set `USER appuser`.
        

---

## 5. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Tại sao tôi build xong image `scratch` nhưng không chạy được, báo lỗi `exec format error`?
> 
> **A:**
> 
> Do kiến trúc CPU (Architecture Mismatch).
> 
> Ví dụ: Bạn build trên MacBook M1 (ARM64) nhưng đem deploy lên Server Linux (AMD64).
> 
> _Fix:_ Thêm tham số `GOARCH=amd64` vào lệnh build: `GOOS=linux GOARCH=amd64 go build ...`

> [!QUESTION] Q: Làm sao debug trong `scratch` image khi nó không có shell?
> 
> **A:**
> 
> 1. **Ephemeral Containers (K8s):** Kubernetes cho phép attach một "debug container" (như busybox) vào cùng Pod để soi process/file/network.
>     
> 2. **Distroless Images (Google):** Một giải pháp trung gian giữa `scratch` và `alpine`. Nó chứa các thư viện tối thiểu để chạy app nhưng không có shell. Google cung cấp phiên bản `distroless:debug` có busybox để debug khi cần.
>     

> [!QUESTION] Q: `docker history` cho thấy gì?
> 
> **A:** Nó cho thấy các layer. Trong Multistage Build, `docker history` của image cuối cùng sẽ **không chứa** các layer của Stage 1 (Source code, Go compiler...). Nó chỉ chứa các layer của Stage 2 -> Bí mật source code được bảo toàn.
