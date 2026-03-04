---
title: "Thiết kế Hệ thống Core Banking (Mini)"
tags:
  - "backend"
date: "2026-03-04"
author: "nathan.huynh"
summary: "Chào mừng bạn đến với bài thi tốt nghiệp:."
---

Chào mừng bạn đến với bài thi tốt nghiệp:.

Đây là tổng hợp kiến thức từ đầu chuỗi bài học đến giờ: Networking (VPC), Compute (EKS), Database (RDS), Security (KMS/IAM), và Infrastructure as Code (Terraform).

Chúng ta sẽ thiết kế một hệ thống chuyển tiền nội bộ (Internal Transfer System) đảm bảo tính toàn vẹn dữ liệu tuyệt đối (Strong Consistency).

---

# PHẦN 1: PHÂN TÍCH & THIẾT KẾ (ARCHITECTURE)

## 1. Yêu cầu (Requirements)

- **Functional:**
    
    - Tạo tài khoản (Account).
        
    - Nạp tiền (Deposit).
        
    - Chuyển tiền (Transfer).
        
    - Xem lịch sử giao dịch (Audit Log).
        
- **Non-Functional:**
    
    - **Consistency:** Tiền không được mất. Tổng tiền hệ thống phải bảo toàn (ACID).
        
    - **Security:** Database không được public. Dữ liệu nhạy cảm phải mã hóa.
        
    - **Availability:** Multi-AZ (Chịu được lỗi sập 1 Data Center).
        

## 2. Mô hình Kiến trúc (High-Level Design)

Chúng ta sẽ sử dụng mô hình **3-Tier Architecture** triển khai trên AWS.

- **Public Subnet:** Chứa **ALB (Load Balancer)** và **NAT Gateway**.
    
- **Private App Subnet:** Chứa **EKS Worker Nodes** (Chạy các Microservices: `Core-Service`, `Auth-Service`).
    
- **Private Data Subnet:** Chứa **RDS PostgreSQL** (Multi-AZ) và **Redis**.
    

## 3. Database Design: The Ledger (Quan trọng nhất)

Trong Banking, **không bao giờ** dùng một cột `current_balance` rồi cộng trừ trực tiếp (`balance = balance + 100`).

Hãy dùng mô hình **Double-Entry Bookkeeping (Kế toán kép)**.

- **Bảng `accounts`:** Chỉ để định danh User.
    
- **Bảng `ledger_entries` (Sổ cái):** Lưu biến động số dư. Mọi giao dịch sinh ra 2 dòng:
    
    1. Tài khoản A: `-100.000` (Debit).
        
    2. Tài khoản B: `+100.000` (Credit).
        
- **Tính số dư:** `SUM(amount) WHERE account_id = X`. (Có thể cache lại snapshot số dư để đọc nhanh hơn).
    

---

# PHẦN 2: TRIỂN KHAI HẠ TẦNG (TERRAFORM)

Dưới đây là code Terraform để dựng hệ thống chuẩn Banking (Security-First).

### Bước 1: Networking (VPC "Kín cổng cao tường")

File `vpc.tf`: Chia mạng thành Public và Private.

Terraform

``` json
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"

  name = "banking-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["ap-southeast-1a", "ap-southeast-1b"] # Multi-AZ
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"] # App + Data
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"] # ALB + NAT

  enable_nat_gateway = true # Để Private App đi ra Internet tải thư viện
  single_nat_gateway = false # High Availability: Mỗi AZ 1 NAT
  enable_vpn_gateway = false

  tags = {
    Environment = "production"
    Project     = "core-banking"
  }
}
```

### Bước 2: Security Groups (Lớp bảo vệ)

File `security.tf`: Nguyên tắc "Chain of Trust".

Terraform

``` json
# 1. SG cho Load Balancer (Mở cửa cho khách)
resource "aws_security_group" "alb_sg" {
  name   = "alb-sg"
  vpc_id = module.vpc.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # HTTPS từ Internet
  }
}

# 2. SG cho App Server (Chỉ nhận từ ALB)
resource "aws_security_group" "app_sg" {
  name   = "app-sg"
  vpc_id = module.vpc.vpc_id

  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id] # Chỉ tin tưởng ALB
  }
}

# 3. SG cho Database (Chỉ nhận từ App - Quan trọng nhất)
resource "aws_security_group" "db_sg" {
  name   = "db-sg"
  vpc_id = module.vpc.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app_sg.id] # Chỉ tin tưởng App
  }
}
```

### Bước 3: Database (RDS Multi-AZ & Encryption)

File `rds.tf`: Dữ liệu tiền tệ phải an toàn tuyệt đối.

Terraform

```
resource "aws_db_instance" "core_banking" {
  identifier        = "banking-ledger-prod"
  engine            = "postgres"
  engine_version    = "14.10"
  instance_class    = "db.t3.medium"
  allocated_storage = 100

  db_name  = "ledger"
  username = "dbadmin"
  password = var.db_password # Lấy từ Secrets Manager, không hardcode!

  # Networking
  vpc_security_group_ids = [aws_security_group.db_sg.id]
  db_subnet_group_name   = module.vpc.database_subnet_group

  # High Availability & Durability
  multi_az            = true # Tự động Failover sang AZ khác nếu sập
  deletion_protection = true # Chống lỡ tay xóa nhầm
  
  # Security (Mã hóa đĩa cứng)
  storage_encrypted = true 
  kms_key_id        = aws_kms_key.banking_key.arn 

  # Backup
  backup_retention_period = 35 # Lưu backup 35 ngày
}
```

### Bước 4: KMS Key (Chìa khóa mã hóa)

File `kms.tf`: Quản lý khóa mã hóa cho DB.

Terraform

```
resource "aws_kms_key" "banking_key" {
  description             = "KMS key for Banking Data"
  deletion_window_in_days = 30
  enable_key_rotation     = true # Tự động xoay vòng khóa mỗi năm
}
```

---

# PHẦN 3: LOGIC XỬ LÝ GIAO DỊCH (CODE LOGIC)

Hạ tầng đã xong. Giờ đến phần mềm (Golang).

Làm sao để đảm bảo chuyển tiền không bị lỗi **Race Condition**?

### Kịch bản: Pessimistic Locking (Khóa bi quan)

Khi User A chuyển tiền cho User B. Ta phải khóa dòng dữ liệu của cả A và B trong Database để không ai khác được can thiệp.

Go

``` go
func TransferMoney(ctx context.Context, db *sql.DB, fromID, toID int, amount float64) error {
    tx, err := db.BeginTx(ctx, nil)
    if err != nil { return err }
    defer tx.Rollback()

    // 1. SELECT FOR UPDATE: Khóa tài khoản người gửi
    // Quan trọng: Phải order by ID để tránh Deadlock (A->B và B->A cùng lúc)
    // Giả sử logic sort ID đã xử lý.
    var currentBalance float64
    err = tx.QueryRowContext(ctx, "SELECT balance FROM accounts WHERE id = $1 FOR UPDATE", fromID).Scan(&currentBalance)
    if err != nil { return err }

    // 2. Check số dư
    if currentBalance < amount {
        return fmt.Errorf("insufficient funds")
    }

    // 3. Thực hiện Ledger Entry (Ghi sổ kép)
    // Trừ tiền A
    _, err = tx.ExecContext(ctx, "INSERT INTO ledger (account_id, amount, type) VALUES ($1, $2, 'DEBIT')", fromID, -amount)
    
    // Cộng tiền B
    _, err = tx.ExecContext(ctx, "INSERT INTO ledger (account_id, amount, type) VALUES ($1, $2, 'CREDIT')", toID, amount)

    // 4. Update Snapshot (để hiển thị cho nhanh)
    _, err = tx.ExecContext(ctx, "UPDATE accounts SET balance = balance - $1 WHERE id = $2", amount, fromID)
    _, err = tx.ExecContext(ctx, "UPDATE accounts SET balance = balance + $1 WHERE id = $2", amount, toID)

    // 5. Commit Transaction (Tất cả thành công hoặc tất cả thất bại)
    return tx.Commit()
}
```

---

# PHẦN 4: GIẢI THÍCH CHI TIẾT (WHY?)

Tại sao tôi thiết kế như vậy?

1. **Tại sao dùng VPC Private Subnets?**
    
    - Database chứa tiền của khách. Nếu để ở Public Subnet, chỉ cần một lỗ hổng Zero-day của Postgres, Hacker có thể Scan IP và tấn công Brute-force. Ở Private Subnet, Hacker phải chiếm được Bastion Host hoặc App Server trước -> Tăng độ khó (Defense in Depth).
        
2. **Tại sao dùng RDS Multi-AZ?**
    
    - Ngân hàng không được phép dừng hoạt động (Downtime). Nếu Data Center A bị cháy, RDS tự động chuyển DNS sang Data Center B trong vòng 60s. Giao dịch tiếp tục bình thường.
        
3. **Tại sao dùng KMS Encryption?**
    
    - Tuân thủ PCI-DSS. Nếu ổ cứng vật lý của AWS bị đánh cắp, kẻ trộm cũng không đọc được dữ liệu vì không có KMS Key để giải mã.
        
4. **Tại sao dùng Pessimistic Locking (`FOR UPDATE`)?**
    
    - Để đảm bảo **Strong Consistency**. Nếu dùng Optimistic Locking (check version), khi traffic cao (ví dụ trả lương hàng loạt), tỷ lệ giao dịch bị fail sẽ rất cao, gây trải nghiệm tệ. Lock DB tuy chậm hơn một chút nhưng chắc chắn đúng.
        
5. **Tại sao không dùng NoSQL (DynamoDB)?**
    
    - DynamoDB rất tốt, nhưng với Core Banking cần tính toán số dư phức tạp và Transaction nhiều bảng, RDBMS (Postgres) vẫn là vua về độ tin cậy và ACID.
        

Chúng ta sẽ sử dụng **Golang** (ngôn ngữ tiêu chuẩn cho Fintech hiện nay) và kiến trúc **Microservices**.

---

# 1. Kiến trúc Tổng thể (Internal Architecture)

Chúng ta sẽ không viết một cục Monolith. Hãy chia tách dựa trên **Domain-Driven Design (DDD)**.

- **API Gateway (Bff):** Entry point, AuthN, Rate Limiting. Giao tiếp REST/GraphQL với Client.
    
- **Auth Service:** Quản lý Identity, cấp phát JWT Token.
    
- **Core Banking Service (The Ledger):** Quan trọng nhất. Quản lý tài khoản, số dư, lịch sử giao dịch nội bộ. (Dùng gRPC để tối ưu tốc độ).
    
- **Payment Gateway Service:** Kết nối với đối tác bên ngoài (Visa/Napas/Momo).
    
- **Worker Service:** Xử lý tác vụ nền (Gửi email, đối soát, report).
    

---

# 2. Cấu trúc Code (Golang Clean Architecture)

Để code dễ bảo trì và test, ta áp dụng **Clean Architecture** (hoặc Hexagonal Architecture).

Plaintext

```
/core-banking
├── cmd/                # Entry point (main.go)
├── internal/
│   ├── domain/         # Entities (Structs) & Repository Interfaces (Pure logic)
│   ├── usecase/        # Business Logic (Transfer, Deposit rules)
│   ├── adapter/        # Implementation (Postgres, gRPC Handler, Redis)
│   │   ├── repository/ # SQL Queries
│   │   ├── handler/    # API Handlers
│   └── infrastructure/ # DB Connection, Logger, Config
├── pkg/                # Shared libraries (Utils, Validators)
└── api/                # Proto files (gRPC definition)
```

### Tại sao lại cấu trúc này?

- **Dependency Rule:** `Domain` không phụ thuộc vào ai cả. `Adapter` (Postgres) phụ thuộc vào `Domain`.
    
- **Dễ đổi DB:** Muốn đổi từ Postgres sang MySQL? Chỉ cần viết lại `adapter/repository`, logic nghiệp vụ trong `usecase` giữ nguyên.
    

---

# 3. Các vấn đề cốt lõi của Backend Ngân hàng

Dưới đây là 3 kỹ thuật bắt buộc phải có, nếu thiếu thì chưa phải là Banking System.

## A. Kiểu dữ liệu tiền tệ (Never use Float)

> [!DANGER] Sai lầm chết người
> 
> Tuyệt đối **KHÔNG** dùng `float64` để lưu tiền.
> 
> `0.1 + 0.2 = 0.30000000000000004` -> Sai lệch số dư.

**Giải pháp:**

1. **Cách 1 (Integer):** Lưu đơn vị nhỏ nhất (micros/cents). 100.000 VNĐ -> Lưu `100000` (nếu không có hào/xu) hoặc `10000000` (nếu tính chính xác 2 số thập phân).
    
2. **Cách 2 (Decimal Library):** Dùng thư viện `github.com/shopspring/decimal` trong Go.
    

Go

```
// internal/domain/transaction.go
import "github.com/shopspring/decimal"

type Transaction struct {
    ID        string          `json:"id"`
    Amount    decimal.Decimal `json:"amount"` // An toàn tuyệt đối
    Currency  string          `json:"currency"`
}
```

## B. Idempotency (Tính Lũy Đẳng) - Chống Duplicate

**Vấn đề:** Mạng lag, User bấm nút "Chuyển tiền" 2 lần. Hoặc API Gateway retry lại request.

**Hậu quả:** Trừ tiền 2 lần.

**Giải pháp:** Bắt buộc Client phải gửi kèm `Idempotency-Key` (UUID) trong Header.

**Code Logic (Middleware):**

Go

```
func IdempotencyMiddleware(redisClient *redis.Client) gin.HandlerFunc {
    return func(c *gin.Context) {
        key := c.GetHeader("Idempotency-Key")
        if key == "" {
            c.Next(); return
        }

        // 1. Check Redis xem key này đã xử lý chưa
        val, err := redisClient.Get(ctx, "idem:"+key).Result()
        if err == nil {
            // Nếu đã có kết quả -> Trả về kết quả cũ ngay lập tức
            c.JSON(200, json.Unmarshal(val))
            c.Abort()
            return
        }

        // 2. Lock key này lại (SetNX) để tránh 2 request chạy song song
        acquired := redisClient.SetNX(ctx, "lock:"+key, 1, 10*time.Second).Val()
        if !acquired {
            c.JSON(409, gin.H{"error": "Request is processing"})
            c.Abort()
            return
        }

        // 3. Cho phép xử lý tiếp
        c.Next()

        // 4. Lưu response vào Redis sau khi xử lý xong
        redisClient.Set(ctx, "idem:"+key, responseBody, 24*time.Hour)
    }
}
```

## C. Distributed Transaction (Outbox Pattern)

**Vấn đề:** Sau khi chuyển tiền thành công (DB Commit), cần bắn Event sang Kafka để báo cho Notification Service gửi Email.

- Nếu bắn Kafka lỗi -> User bị trừ tiền nhưng không nhận được mail.
    
- Nếu bắn Kafka trước rồi mới Commit DB -> Mail gửi rồi nhưng DB lỗi rollback -> Mail báo ảo.
    

**Giải pháp:** **Transactional Outbox**.

**SQL Schema:**

SQL

```
CREATE TABLE outbox (
    id UUID PRIMARY KEY,
    topic VARCHAR(50),
    payload JSONB,
    status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Golang Logic (Trong cùng 1 Transaction):**

Go

```
func (u *TransferUsecase) Transfer(ctx context.Context, req TransferReq) error {
    tx, _ := u.db.BeginTx(ctx, nil)
    defer tx.Rollback()

    // 1. Trừ tiền A, Cộng tiền B (Logic Ledger như bài trước)
    if err := u.repo.UpdateBalances(ctx, tx, req); err != nil {
        return err
    }

    // 2. Lưu Event vào bảng Outbox (Thay vì bắn Kafka ngay)
    eventPayload := map[string]interface{}{
        "from": req.FromID, "to": req.ToID, "amount": req.Amount,
    }
    bytes, _ := json.Marshal(eventPayload)
    
    _, err := tx.ExecContext(ctx, 
        "INSERT INTO outbox (topic, payload) VALUES ($1, $2)", 
        "transaction_completed", bytes)
    if err != nil { return err }

    // 3. Commit (Đảm bảo cả tiền và event đều được lưu hoặc không lưu gì cả)
    return tx.Commit()
}
```

_Sau đó, một **Debezium** hoặc một **Cron Worker** sẽ quét bảng `outbox` để bắn sang Kafka._

---

# 4. API Specification (gRPC vs REST)

### Internal (Core Service <-> Payment Service)

Dùng **gRPC (Protobuf)** để tối ưu tốc độ và Type-safety.

Protocol Buffers

```
// transaction.proto
service TransactionService {
  rpc Transfer (TransferRequest) returns (TransferResponse);
}

message TransferRequest {
  string from_account_id = 1;
  string to_account_id = 2;
  int64 amount_micros = 3; // Dùng int64, đơn vị micros
  string idempotency_key = 4;
}
```

### External (Mobile App -> Gateway)

Dùng **RESTful API (JSON)** để dễ tích hợp với Frontend.

- `POST /api/v1/transfers`
    
- Header: `Authorization: Bearer <jwt>`, `Idempotency-Key: <uuid>`
    

---

# 5. Observability (Giám sát)

Backend không thể chạy mù. Cần setup bộ 3 quyền lực:

1. **Structured Logging (Zap/Logrus):**
    
    - Không log `fmt.Println("Error")`.
        
    - Log JSON: `{"level":"error", "msg":"balance insufficient", "user_id":123, "trace_id":"abc"}`.
        
2. **Distributed Tracing (OpenTelemetry/Jaeger):**
    
    - Gắn `TraceID` vào mọi request. Để biết request đi từ Gateway -> Core -> DB mất bao lâu ở từng khâu.
        
3. **Metrics (Prometheus):**
    
    - Đo đạc Business Metrics: `total_money_transferred`, `failed_transaction_count`.
        

---

# 6. Checklist Bảo mật Backend

1. **Input Validation:** Validate dữ liệu ngay từ Controller. Không tin tưởng client. (Số tiền > 0, ID đúng format).
    
2. **Rate Limiting:** Mỗi user chỉ được gọi API chuyển tiền 1 lần/giây. (Dùng Redis Token Bucket).
    
3. **Sensitive Data:** Không bao giờ log số thẻ, password, số dư ra file log. (Dùng log masking).
    

Chào mừng bạn đến với "trái tim" của hệ thống xử lý bất đồng bộ.

Trong các hệ thống tài chính, **Worker** (hay còn gọi là Relay Service) chịu trách nhiệm đảm bảo **Sự nhất quán cuối cùng (Eventual Consistency)**. Nếu Worker chết, người dùng chuyển tiền xong nhưng không nhận được email, hoặc tệ hơn là hệ thống đối soát không ghi nhận.

Dưới đây là thiết kế chi tiết (Deep Dive) vào Code của Worker xử lý **Outbox Pattern** bằng Golang, PostgreSQL và Kafka.

---

# 1. Database Schema (Bảng Outbox)

Đầu tiên, ta cần cấu trúc bảng `outbox` tối ưu cho việc quét (polling) và khóa (locking).

SQL

```
CREATE TYPE outbox_status AS ENUM ('PENDING', 'PROCESSING', 'DONE', 'FAILED');

CREATE TABLE outbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_id VARCHAR(255) NOT NULL, -- ID của User hoặc Transaction
    topic VARCHAR(255) NOT NULL,        -- Kafka Topic (vd: transaction_events)
    payload JSONB NOT NULL,             -- Dữ liệu (Message Body)
    status outbox_status DEFAULT 'PENDING',
    retry_count INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index cực quan trọng để query PENDING cho nhanh
CREATE INDEX idx_outbox_status_created ON outbox (status, created_at) WHERE status = 'PENDING';
```

---

# 2. Repository Layer (Vũ khí bí mật: SKIP LOCKED)

Vấn đề lớn nhất khi chạy nhiều Worker (ví dụ 5 Pods) cùng quét 1 bảng DB là **Race Condition** (Tranh chấp). 5 Pod cùng đọc được 1 dòng `PENDING` và cùng bắn Kafka -> Duplicate message.

**Giải pháp Senior:** Sử dụng câu lệnh `SELECT ... FOR UPDATE SKIP LOCKED` của PostgreSQL.

- Nó sẽ khóa các dòng đang được đọc bởi Transaction này.
    
- Các Transaction khác (Worker khác) sẽ **bỏ qua** các dòng đang bị khóa và đọc các dòng tiếp theo. -> **Không bao giờ giẫm chân nhau.**
    

Go

```
// internal/adapter/repository/outbox_repo.go

type OutboxRepository struct {
    db *sql.DB
}

type OutboxEvent struct {
    ID      string
    Topic   string
    Payload []byte
}

// FetchPendingEvents lấy ra N events chưa xử lý và KHÓA chúng lại
func (r *OutboxRepository) FetchPendingEvents(ctx context.Context, limit int) ([]OutboxEvent, error) {
    // Query thần thánh:
    // 1. Lấy dòng PENDING
    // 2. Sắp xếp cũ nhất trước (FIFO)
    // 3. Giới hạn số lượng (Batch processing)
    // 4. FOR UPDATE: Khóa dòng này lại
    // 5. SKIP LOCKED: Nếu ai đang khóa rồi thì bỏ qua, tìm dòng khác
    query := `
        SELECT id, topic, payload
        FROM outbox
        WHERE status = 'PENDING'
        ORDER BY created_at ASC
        LIMIT $1
        FOR UPDATE SKIP LOCKED
    `

    rows, err := r.db.QueryContext(ctx, query, limit)
    if err != nil {
        return nil, err
    }
    defer rows.Close()

    var events []OutboxEvent
    for rows.Next() {
        var e OutboxEvent
        if err := rows.Scan(&e.ID, &e.Topic, &e.Payload); err != nil {
            return nil, err
        }
        events = append(events, e)
    }
    return events, nil
}

// UpdateStatus cập nhật trạng thái sau khi bắn Kafka xong
func (r *OutboxRepository) UpdateStatus(ctx context.Context, id string, status string, errMsg string) error {
    query := `
        UPDATE outbox 
        SET status = $1, error_message = $2, updated_at = NOW() 
        WHERE id = $3
    `
    _, err := r.db.ExecContext(ctx, query, status, errMsg, id)
    return err
}
```

---

# 3. Kafka Producer Layer (Interface)

Ta cần một Interface để decouple logic worker khỏi thư viện Kafka (dễ test và dễ đổi sang RabbitMQ nếu cần).

Go

```
// internal/domain/publisher.go
type EventPublisher interface {
    Publish(ctx context.Context, topic string, key string, payload []byte) error
}

// internal/adapter/kafka/producer.go
type SaramaProducer struct {
    producer sarama.SyncProducer
}

func (p *SaramaProducer) Publish(ctx context.Context, topic string, key string, payload []byte) error {
    msg := &sarama.ProducerMessage{
        Topic: topic,
        Key:   sarama.StringEncoder(key), // Key quan trọng để đảm bảo thứ tự trong Partition
        Value: sarama.ByteEncoder(payload),
    }
    _, _, err := p.producer.SendMessage(msg)
    return err
}
```

---

# 4. Worker Core Logic (The Loop)

Đây là nơi phối hợp tất cả. Worker sẽ chạy một vòng lặp vô tận (Infinite Loop) để quét DB.

Go

```
// internal/worker/outbox_worker.go

type OutboxWorker struct {
    repo      *repository.OutboxRepository
    publisher domain.EventPublisher
    logger    *zap.Logger
    batchSize int
    interval  time.Duration
}

func NewOutboxWorker(repo *repository.OutboxRepository, pub domain.EventPublisher) *OutboxWorker {
    return &OutboxWorker{
        repo:      repo,
        publisher: pub,
        logger:    zap.NewExample(),
        batchSize: 50,              // Xử lý 50 event mỗi lần
        interval:  2 * time.Second, // Nghỉ 2s nếu không có việc
    }
}

// Run bắt đầu quá trình polling
func (w *OutboxWorker) Run(ctx context.Context) {
    ticker := time.NewTicker(w.interval)
    defer ticker.Stop()

    w.logger.Info("Starting Outbox Worker...")

    for {
        select {
        case <-ctx.Done(): // Graceful Shutdown
            w.logger.Info("Stopping worker...")
            return
        case <-ticker.C:
            w.processBatch(ctx)
        }
    }
}

func (w *OutboxWorker) processBatch(ctx context.Context) {
    // 1. Tạo Transaction (Quan trọng: Fetch và Update phải chung context hoặc xử lý kỹ)
    // Lưu ý: SKIP LOCKED thường cần chạy trong transaction. 
    // Ở code production, bạn nên truyền tx vào repo.
    
    events, err := w.repo.FetchPendingEvents(ctx, w.batchSize)
    if err != nil {
        w.logger.Error("Failed to fetch events", zap.Error(err))
        return
    }

    if len(events) == 0 {
        return // Không có việc thì đợi tick tiếp theo
    }

    w.logger.Info("Processing events", zap.Int("count", len(events)))

    var wg sync.WaitGroup
    
    // 2. Xử lý song song hoặc tuần tự (Ở đây làm tuần tự cho an toàn thứ tự)
    for _, event := range events {
        // Retry logic đơn giản: Nếu lỗi thì đánh dấu FAILED, worker khác sẽ không lấy lại (do query where PENDING)
        // Thực tế: Cần Retry logic (Exponential Backoff)
        
        err := w.publisher.Publish(ctx, event.Topic, event.ID, event.Payload)
        
        status := "DONE"
        errMsg := ""
        if err != nil {
            status = "FAILED"
            errMsg = err.Error()
            w.logger.Error("Failed to publish kafka", zap.String("id", event.ID), zap.Error(err))
        }

        // 3. Update DB
        if err := w.repo.UpdateStatus(ctx, event.ID, status, errMsg); err != nil {
            w.logger.Error("Failed to update status", zap.Error(err))
        }
    }
}
```

---

# 5. Entry Point & Graceful Shutdown

Để đảm bảo khi deploy, Worker không bị giết đột ngột khi đang bắn Kafka dở (gây mất mát hoặc duplicate).

Go

```
// cmd/worker/main.go

func main() {
    // 1. Init Dependencies (DB, Kafka...)
    db, _ := sql.Open("postgres", "...")
    kafkaProd, _ := kafka.NewProducer(...)
    
    repo := repository.NewOutboxRepo(db)
    worker := worker.NewOutboxWorker(repo, kafkaProd)

    // 2. Setup Context với Signal (Ctrl+C hoặc Kubernetes Terminate)
    ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
    defer stop()

    // 3. Chạy worker trong Goroutine
    go worker.Run(ctx)

    // 4. Block main thread chờ tín hiệu dừng
    <-ctx.Done()
    
    // 5. Cleanup (Đóng kết nối DB, Kafka)
    log.Println("Graceful shutdown completed.")
}
```

---

# 6. Các chiến lược nâng cao (Senior Optimization)

Đoạn code trên là bản chuẩn, nhưng với hệ thống **High Frequency**, bạn cần tối ưu thêm:

### A. Batch Update (Giảm tải DB)

Thay vì Update từng dòng `DONE`, hãy gom ID lại và update 1 lần:

SQL

```
UPDATE outbox SET status = 'DONE' WHERE id = ANY($1::uuid[]);
```

### B. Cleanup / Archiving (Dọn rác)

Bảng `outbox` sẽ phình to rất nhanh (triệu dòng/ngày).

- **Giải pháp:** Tạo một Cronjob chạy lúc 3h sáng hoặc sử dụng **Table Partitioning** (Partition theo ngày). Drop partition cũ sau 7 ngày.
    
- **Đừng xóa ngay:** `DELETE FROM outbox WHERE status = 'DONE'` mỗi giây sẽ làm Database bị _Fragmentation_ (phân mảnh) và chậm.
    

### C. Debezium (CDC - Change Data Capture)

Nếu hệ thống quá lớn (ví dụ Shopee/Grab), việc Polling DB (`SELECT`) liên tục sẽ gây áp lực lên DB chính.

- **Giải pháp:** Sử dụng **Debezium**.
    
- Debezium đọc trực tiếp **WAL Log (Binlog)** của Postgres -> Tự động bắn sang Kafka.
    
- **Lợi ích:** Không cần viết code Worker Polling.
    
- **Bất lợi:** Cấu hình hạ tầng phức tạp hơn.
    

### D. Dead Letter Queue (DLQ)

Nếu một event bị lỗi (`status = 'FAILED'`) do format sai hoặc Kafka lỗi lâu dài.

- Cần có API hoặc Admin Tool để **Retry** các event này thủ công hoặc tự động sau một khoảng thời gian dài.
    

Đây là toàn bộ logic code để xây dựng một Worker Service bền bỉ. Bạn có thể copy cấu trúc này vào dự án Golang của mình và nó sẽ chạy rất ổn định.

Testing cho hệ thống Ngân hàng (Banking) không chỉ đơn thuần là `assert.Equal(a, b)`. Đó là cuộc chiến chứng minh rằng hệ thống **không thể sai sót** ngay cả khi bị tấn công dồn dập (Concurrency) hay hạ tầng gặp sự cố.

Dưới đây là chiến lược Testing 4 tầng (Testing Pyramid) chuyên biệt cho hệ thống tài chính, từ Unit Test đến Race Condition Test.

---

# 1. Unit Test (Logic Nghiệp Vụ)

Ở tầng này, ta test **Business Logic** thuần túy trong `domain` hoặc `usecase`. Tuyệt đối **KHÔNG** kết nối Database thật, **KHÔNG** gọi Kafka thật. Ta dùng **Mock**.

**Công cụ:** `testify` (assert), `gomock` (mocking).

### Kịch bản: Test logic validate chuyển tiền

- Input: Số dư 50k, Chuyển 100k.
    
- Expect: Error "Insufficient funds".
    

**Code Example:**

Go

```
// transaction_test.go
func TestTransfer_InsufficientFunds(t *testing.T) {
    // 1. Setup Mock
    ctrl := gomock.NewController(t)
    defer ctrl.Finish()

    mockRepo := mocks.NewMockTransactionRepository(ctrl)
    
    // Giả lập: User A có 50.000
    mockRepo.EXPECT().GetBalance(gomock.Any(), "user_A").Return(decimal.NewFromInt(50000), nil)

    // 2. Init Usecase
    usecase := NewTransactionUsecase(mockRepo)

    // 3. Action: Chuyển 100.000
    err := usecase.Transfer(context.Background(), "user_A", "user_B", decimal.NewFromInt(100000))

    // 4. Assert
    assert.Error(t, err)
    assert.Equal(t, "insufficient funds", err.Error())
}
```

---

# 2. Integration Test (DB & Transaction) - QUAN TRỌNG NHẤT

Với Banking, Unit Test là chưa đủ vì logic quan trọng nhất nằm ở **SQL Transaction** và **Locking**. Mocking SQL (`sqlmock`) là vô dụng ở đây vì nó không mô phỏng được việc khóa dòng (`FOR UPDATE`).

**Giải pháp Senior:** Dùng **Testcontainers**.

Khi chạy test, Go sẽ tự động bật một Docker Container chứa PostgreSQL thật, chạy migration, test xong tự hủy.

**Công cụ:** `testcontainers-go`, `dockertest`.

### Kịch bản: Test Transaction Commit & Rollback

- Test case: Chuyển tiền thành công -> DB phải có 2 dòng Ledger, 1 dòng Outbox.
    

**Code Example:**

Go

```
// repository_test.go
func TestTransfer_Integration(t *testing.T) {
    // 1. Setup Postgres thật bằng Docker (code setup lược bỏ cho gọn)
    db := setupTestContainerDB(t) 
    repo := NewTransactionRepository(db)

    // 2. Prepare Data: Tạo 2 user, mỗi người 1 triệu
    repo.CreateAccount(ctx, "A", 1000000)
    repo.CreateAccount(ctx, "B", 1000000)

    // 3. Action
    err := repo.TransferMoney(ctx, "A", "B", 200000)

    // 4. Assert (Kiểm tra dữ liệu thật trong DB)
    assert.NoError(t, err)

    balA, _ := repo.GetBalance(ctx, "A")
    balB, _ := repo.GetBalance(ctx, "B")

    assert.True(t, balA.Equal(decimal.NewFromInt(800000)), "A phải còn 800k")
    assert.True(t, balB.Equal(decimal.NewFromInt(1200000)), "B phải có 1tr2")

    // Kiểm tra Outbox
    var outboxCount int
    db.QueryRow("SELECT count(*) FROM outbox").Scan(&outboxCount)
    assert.Equal(t, 1, outboxCount, "Phải sinh ra 1 outbox event")
}
```

---

# 3. Race Condition Test (Bài test tử thần)

Đây là bài test để chứng minh cơ chế **Pessimistic Locking (`SELECT FOR UPDATE`)** hoạt động đúng.

Nếu không có `FOR UPDATE`, bài test này sẽ fail ngay lập tức.

**Kịch bản:**

- User A có 1.000 VNĐ.
    
- Ta bắn **100 Goroutines** cùng lúc (Concurrent), mỗi thread chuyển 10 VNĐ cho B.
    
- **Kết quả đúng:** A còn 0 VNĐ.
    
- **Kết quả sai (Bug):** A còn 900 VNĐ (Do race condition, nhiều thread đọc cùng lúc thấy còn tiền).
    

**Code Example:**

Go

```
func TestTransfer_Concurrency_RaceCondition(t *testing.T) {
    db := setupTestContainerDB(t)
    repo := NewTransactionRepository(db)
    
    // Setup: A có 1000
    repo.CreateAccount(ctx, "A", 1000)
    repo.CreateAccount(ctx, "B", 0)

    // Chạy 100 luồng song song
    concurrency := 100
    amountPerTx := 10
    
    var wg sync.WaitGroup
    wg.Add(concurrency)

    for i := 0; i < concurrency; i++ {
        go func() {
            defer wg.Done()
            // Mỗi thread cố gắng chuyển 10 đồng
            _ = repo.TransferMoney(context.Background(), "A", "B", decimal.NewFromInt(int64(amountPerTx)))
        }()
    }

    // Chờ tất cả chạy xong
    wg.Wait()

    // ASSERT
    balA, _ := repo.GetBalance(ctx, "A")
    
    // Nếu không có Locking, balA sẽ > 0 (SAI)
    // Nếu có Locking, balA phải bằng 0 (ĐÚNG)
    assert.True(t, balA.Equal(decimal.Zero), "Balance của A phải về 0. Actual: %s", balA.String())
}
```

> [!TIP]
> 
> Hãy thử xóa dòng `FOR UPDATE` trong code Repository và chạy bài test này. Bạn sẽ thấy nó Fail ngay lập tức. Đây là cách tốt nhất để demo cho team thấy tầm quan trọng của Locking.

---

# 4. Worker & Kafka Test

Làm sao test cái Worker chạy vòng lặp vô tận? Chúng ta không test vòng lặp, ta test **Logic xử lý 1 Batch**.

**Kịch bản:**

1. Insert giả 1 dòng `PENDING` vào bảng `outbox`.
    
2. Gọi hàm `worker.processBatch()`.
    
3. Kiểm tra xem Mock Kafka Producer có được gọi không.
    
4. Kiểm tra xem dòng trong DB có đổi sang `DONE` không.
    

---

# 5. Fuzz Testing (Tìm lỗi tiềm ẩn)

Từ Go 1.18, Go hỗ trợ **Fuzzing** native. Nó sẽ tự động sinh ra các input "quái dị" (số âm, chuỗi unicode lạ, số cực lớn) để xem code có bị crash không.

Go

```
func FuzzTransferInput(f *testing.F) {
    f.Add(100, -50) // Seed input mẫu
    f.Fuzz(func(t *testing.T, balance int, amount int) {
        // Gọi hàm logic
        newBal, err := CalculateNewBalance(balance, amount)
        
        // Assert các quy luật bất biến
        if amount < 0 && err == nil {
             t.Errorf("Chuyển tiền âm mà không báo lỗi!")
        }
    })
}
```

---

# 6. CI/CD Pipeline cho Testing

Đừng chạy test bằng cơm. Hãy đưa vào `Makefile` và CI (GitHub Actions).

**Makefile:**

Makefile

```
test-unit:
	go test -v -short ./...

test-integration:
	# Cần Docker chạy trước
	go test -v -run Integration ./...

test-race:
	# Detect race condition ở level memory
	go test -race ./...
```

**Chiến lược CI:**

1. **Pull Request:** Chạy `Unit Test` + `Linter`. (Nhanh, < 1 phút).
    
2. **Merge to Develop:** Chạy `Integration Test` + `Race Test`. (Chậm, tốn 5-10 phút).
    

### Tổng kết

Để hệ thống ngân hàng an toàn, bạn cần:

1. **Unit Test:** Logic tính toán tiền tệ (Decimal).
    
2. **Integration Test (Testcontainers):** Logic SQL Transaction, Commit/Rollback.
    
3. **Concurrency Test:** Logic Locking (Chống mất tiền).
    

Nếu bạn pass qua được **Bài 3 (Race Condition Test)**, hệ thống của bạn đã đạt tiêu chuẩn Fintech cơ bản.