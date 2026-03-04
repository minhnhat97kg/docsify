---
title: "Clean Architecture - Hexagonal, Ports & Adapters"
tags:
  - "architecture"
  - "golang"
  - "clean-architecture"
  - "hexagonal"
  - "refactoring"
  - "interview"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Trong kiến trúc phân tầng truyền thống (Controller -> Service -> Repository -> Database):"
---

## 1. Vấn đề: Spaghetti Code trong Layered Architecture

Trong kiến trúc phân tầng truyền thống (Controller -> Service -> Repository -> Database):

- **Vấn đề:** Tầng Business Logic (Service) thường phụ thuộc chặt chẽ vào tầng Data Access (Repository).
    
- **Hệ quả:** Nếu bạn thay đổi Database (từ MySQL sang MongoDB) hoặc thay đổi Framework (từ Gin sang Fiber), bạn phải sửa code ở Business Logic.
    
- **Database Driven:** Chúng ta thường thiết kế bảng DB trước rồi mới viết code -> DB chi phối Logic.
    

**Clean Architecture (Hexagonal)** giải quyết việc này bằng cách **Đảo ngược sự phụ thuộc (Dependency Inversion)**.

_Logic nằm ở trung tâm, mọi thứ khác (DB, UI, API) chỉ là plugin cắm vào._

---

## 2. Giải phẫu Hexagonal: Ports & Adapters

Hãy tưởng tượng ứng dụng của bạn là một cái máy tính (Core).

- Nó có các cổng USB (Ports).
    
- Bạn có thể cắm chuột, bàn phím, hay máy in vào (Adapters).
    
- Máy tính không quan tâm hãng sản xuất chuột là gì, miễn là nó tuân thủ chuẩn USB.
    

### A. Core (The Domain) - "Vùng bất khả xâm phạm"

- Nơi chứa Business Logic và Entities.
    
- **Nguyên tắc:** Không phụ thuộc vào bất kỳ thư viện bên ngoài nào (Không GORM, không Gin, không Redis). Chỉ dùng Go chuẩn.
    
- Nó định nghĩa các **Interfaces (Ports)** mà nó cần để giao tiếp.
    

### B. Ports (Cổng - Interfaces)

Là các hợp đồng giao tiếp (Interfaces). Có 2 loại:

1. **Primary Ports (Driving - Đầu vào):** Định nghĩa cách bên ngoài giao tiếp với Core. (Ví dụ: `UserService` interface).
    
2. **Secondary Ports (Driven - Đầu ra):** Định nghĩa những gì Core cần từ bên ngoài. (Ví dụ: `UserRepository` interface).
    

### C. Adapters (Bộ chuyển đổi - Implementations)

Là nơi code thực thi cụ thể nằm.

1. **Primary Adapters (Driving):** REST API Handler, gRPC Server, CLI Command (Gọi vào Core).
    
2. **Secondary Adapters (Driven):** Postgres Repository, Redis Cache, SMTP Client (Được Core gọi).
    

---

## 3. Cấu trúc thư mục (Go Standard Layout)

Plaintext

```
/cmd
  /api          # Main entry point (Wiring)
/internal
  /core
    /domain     # Entities (User struct - Pure Go)
    /ports      # Interfaces (UserService, UserRepository)
    /services   # Business Logic (Implementation of UserService)
  /adapters
    /handlers   # HTTP Gin/Fiber (Primary Adapter)
    /repositories # GORM/SQLx (Secondary Adapter)
```

---

## 4. Code Implementation (Golang)

Hãy xem cách chúng ta tách biệt hoàn toàn Logic khỏi Database.

### Bước 1: Domain (Core)

Không có tag `gorm` hay `json` ở đây (lý tưởng nhất).

Go

```
package domain

type User struct {
    ID    string
    Email string
    Name  string
}
```

### Bước 2: Ports (Core)

Core hét lên: _"Tôi cần ai đó lưu User, tôi không quan tâm lưu vào đâu!"_

Go

```
package ports

import "my-app/internal/core/domain"

// Primary Port (Input)
type UserService interface {
    Create(email, name string) (*domain.User, error)
}

// Secondary Port (Output)
type UserRepository interface {
    Save(user domain.User) error
    GetByEmail(email string) (*domain.User, error)
}
```

### Bước 3: Service (Core Logic)

Logic chỉ biết đến Interface `UserRepository`, không biết Postgres là gì.

Go

```
package services

import (
    "errors"
    "my-app/internal/core/domain"
    "my-app/internal/core/ports"
    "github.com/google/uuid"
)

type userService struct {
    repo ports.UserRepository // Dependency Injection
}

func NewUserService(repo ports.UserRepository) ports.UserService {
    return &userService{repo: repo}
}

func (s *userService) Create(email, name string) (*domain.User, error) {
    // 1. Validate Business Logic
    if email == "" { return nil, errors.New("empty email") }
    
    // 2. Logic nghiệp vụ
    user := domain.User{
        ID:    uuid.New().String(),
        Email: email,
        Name:  name,
    }

    // 3. Gọi Port (không biết bên dưới là SQL hay File)
    if err := s.repo.Save(user); err != nil {
        return nil, err
    }
    
    return &user, nil
}
```

### Bước 4: Adapter - Repository (Infrastructure)

Bây giờ mới là lúc dùng SQL.

Go

```
package repositories

import (
    "gorm.io/gorm"
    "my-app/internal/core/domain"
)

type postgresRepo struct {
    db *gorm.DB
}

func NewPostgresRepo(db *gorm.DB) *postgresRepo {
    return &postgresRepo{db: db}
}

// Implement Secondary Port
func (r *postgresRepo) Save(user domain.User) error {
    return r.db.Create(&user).Error
}
```

### Bước 5: Wiring (Dependency Injection tại Main)

Nơi duy nhất gắn kết mọi thứ.

Go

```
func main() {
    // 1. Init Infra
    db := gorm.Open(...)

    // 2. Init Adapters (Repository)
    repo := repositories.NewPostgresRepo(db)

    // 3. Init Core Service (Inject Repo vào Service)
    svc := services.NewUserService(repo)

    // 4. Init Handlers (Inject Service vào Handler)
    handler := handlers.NewUserHandler(svc)
    
    // 5. Run
    router.POST("/users", handler.CreateUser)
    router.Run(":8080")
}
```

---

## 5. Ưu điểm & Cái giá phải trả

|**Ưu điểm**|**Nhược điểm**|
|---|---|
|**Testability:** Có thể Unit Test Service dễ dàng bằng cách Mock Repository (vì nó là interface).|**Boilerplate Code:** Phải viết nhiều file, nhiều interface chuyển đổi dữ liệu (Mapping DTO <-> Domain).|
|**Flexibility:** Muốn đổi từ MySQL sang MongoDB? Chỉ cần viết lại Adapter Repository, Logic giữ nguyên 100%.|**Complexity:** Quá phức tạp cho các dự án CRUD đơn giản (Over-engineering).|
|**Technology Agnostic:** Core không phụ thuộc Framework.|Khó điều hướng code (Go to definition sẽ nhảy vào Interface thay vì Implementation).|

---

## 6. Câu hỏi phỏng vấn thực chiến

> [!QUESTION] Q: Tại sao không nên dùng Struct GORM (`gorm.Model`) trực tiếp trong Domain User?
> 
> **A:**
> 
> Nếu dùng `gorm.Model` trong Domain, bạn đã làm Domain phụ thuộc vào thư viện GORM.
> 
> Nếu sau này đổi sang MongoDB (không dùng GORM), bạn phải sửa lại Domain -> Vi phạm nguyên tắc Clean Architecture.
> 
> _Best Practice:_ Domain User nên trong sạch. Ở tầng Repository Adapter, ta tạo một struct `UserDBModel` riêng có tag GORM, và map dữ liệu qua lại.

> [!QUESTION] Q: Clean Architecture có làm chậm hệ thống không?
> 
> **A:**
> 
> Về mặt Runtime: Có chậm hơn một chút xíu (nano giây) do chi phí gọi qua Interface (Indirect Call) và chi phí copy/map dữ liệu giữa các tầng.
> 
> Tuy nhiên, sự chậm trễ này là **không đáng kể** so với Network I/O hay Database Query. Lợi ích về bảo trì và mở rộng lớn hơn nhiều.

> [!QUESTION] Q: Khi nào **KHÔNG NÊN** dùng Hexagonal?
> 
> **A:**
> 
> Khi làm MVP (Minimum Viable Product), Script tool nhỏ, hoặc dự án CRUD thuần túy không có logic nghiệp vụ phức tạp. Lúc đó Layered Architecture đơn giản là đủ. Hexagonal dành cho Core Banking, Enterprise App cần sống thọ 5-10 năm.