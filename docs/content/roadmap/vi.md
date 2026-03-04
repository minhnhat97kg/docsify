---
title: "9. Java & Spring Boot (Legacy Integration)"
tags:
  - "roadmap"
  - "learning"
date: "2026-03-04"
author: "nathan.huynh"
summary: "- Dave Cheney: Functional Options - Refactoring Guru: Singleton Go - Refactoring Guru: Factory Go - Refactoring Guru: Strategy Go - Refactoring Guru: Adapter Go"
---

### Go Patterns
- [ ] **Functional Options** - Config pattern tốt nhất cho Go struct.
	- [Dave Cheney: Functional Options](https://dave.cheney.net/2014/10/17/functional-options-for-friendly-apis)
- [ ] **Singleton** - Sử dụng `sync.Once`.
	- [Refactoring Guru: Singleton Go](https://refactoring.guru/design-patterns/singleton/go/example)
- [ ] **Factory Method** - Tạo object linh hoạt.
	- [Refactoring Guru: Factory Go](https://refactoring.guru/design-patterns/factory-method/go/example)
- [ ] **Strategy** - Thay đổi thuật toán runtime.
	- [Refactoring Guru: Strategy Go](https://refactoring.guru/design-patterns/strategy/go/example)
- [ ] **Adapter** - Tích hợp hệ thống cũ.
	- [Refactoring Guru: Adapter Go](https://refactoring.guru/design-patterns/adapter/go/example)

### Database & Storage
- [ ] **RDS / Aurora** - Multi-AZ (High Availability) vs Read Replicas (Scaling Read).
    - [RDS Multi-AZ](https://aws.amazon.com/rds/features/multi-az/)
- [ ] **S3 Consistency Model** - Strong Consistency (mới update gần đây).
    - [S3 Consistency](https://aws.amazon.com/s3/consistency/)
- [ ] **ElastiCache (Redis)** - Cluster mode enabled vs disabled.
    - [ElastiCache Redis](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/WhatIs.html)
    - 
## 9. Java & Spring Boot (Legacy Integration)
*Kỹ năng đọc hiểu hệ thống cũ để migrate sang Golang.*

### Spring Ecosystem
- [ ] **Dependency Injection (IoC)** - Hiểu cách Spring quản lý Bean (Singleton/Prototype).
    
    - [Baeldung: Spring Bean Scopes](https://www.baeldung.com/spring-bean-scopes)
- [ ] **Transaction Management** - Cơ chế `@Transactional` và AOP Proxy.
    - [Spring Docs: Transaction Management](https://docs.spring.io/spring-framework/reference/data-access/transaction.html)
- [ ] **Spring Boot vs Go** - So sánh kiến trúc (Thread-per-request vs Goroutines).
    - [Medium: Java Threads vs Go Routines](https://medium.com/@genchilu/java-thread-vs-go-routine-e25df5b50830)

### JVM Internals (So sánh với Go Runtime)
- [ ] **JVM Memory Model** - Heap (Eden, Survivor, Old Gen) vs Go Heap.
    
    - [DigitalOcean: Java Memory Management](https://www.digitalocean.com/community/tutorials/java-jvm-memory-model-memory-management-in-java)
- [ ] **Garbage Collection** - Generational GC (G1/ZGC) vs Go's Tricolor.
    - [Oracle: G1 GC](https://docs.oracle.com/en/java/javase/17/gctuning/garbage-first-garbage-collector.html)

### Migration Strategy
- [ ] **Anti-Corruption Layer (ACL)** - Lớp phòng vệ khi giao tiếp giữa hệ thống mới và cũ.
    - [Microsoft: ACL Pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/anti-corruption-layer)
- [ ] **Strangler Fig Pattern** - Chiến lược thay thế dần dần Monolith.
    - [Microservices.io: Strangler Fig](https://microservices.io/patterns/refactoring/strangler-application.html)

## 10. Event-Driven Security & Streaming (Kafka & Keycloak)
*Hệ thống thần kinh trung ương (Kafka) và Người gác cổng (Keycloak) của Ngân hàng.*

### Apache Kafka (The Backbone)
*Không chỉ là Message Queue, nó là nơi lưu trữ "Sự thật" (Event Sourcing).*

- [ ] **Exactly-Once Semantics (EOS)** - Đảm bảo tin nhắn không bao giờ bị mất hoặc xử lý 2 lần (Chống double-spending).
    - [Confluent: Exactly-Once](https://www.confluent.io/blog/exactly-once-semantics-are-possible-heres-how-apache-kafka-does-it/)
- [ ] **Consumer Groups & Rebalancing** - Cơ chế scale consumer tự động.
    - [Kafka Docs: Consumer Groups](https://kafka.apache.org/documentation/#intro_consumers)
- [ ] **Reliability Configs** - Cấu hình "không được phép mất data" (`acks=all`, `min.insync.replicas=2`, `enable.idempotence=true`).
    - [Kafka Reliability Guide](https://www.confluent.io/blog/hands-free-kafka-replication-a-lesson-in-operational-simplicity/)
- [ ] **Kafka Connect** - Tích hợp DB mà không cần code (CDC - Change Data Capture).
    - [Debezium: CDC with Kafka](https://debezium.io/documentation/reference/stable/architecture.html)
- [ ] **Kafka Streams / ksqlDB** - Xử lý gian lận (Fraud Detection) thời gian thực.
    - [Kafka Streams Intro](https://kafka.apache.org/documentation/streams/)

### Keycloak (Identity & Access Management)
*Chuẩn bảo mật tập trung cho Microservices.*

- [ ] **OpenID Connect (OIDC) & OAuth 2.0** - Phân biệt Authentication (ID Token) và Authorization (Access Token).
    - [Keycloak: OIDC Guide](https://www.keycloak.org/docs/latest/securing_apps/#_oidc)
- [ ] **Keycloak Gatekeeper / Proxy** - Mô hình Sidecar để bảo vệ service mà không cần sửa code.
    - [Louketo (Keycloak Gatekeeper)](https://github.com/louketo/louketo-proxy)
- [ ] **User Federation (LDAP/AD)** - Đồng bộ user từ hệ thống nội bộ ngân hàng (Active Directory).
    - [Keycloak: User Federation](https://www.keycloak.org/docs/latest/server_admin/#_user-storage-federation)
- [ ] **Fine-Grained Authorization** - Quản lý quyền sâu tới từng resource (tài khoản A chỉ xem được sổ tiết kiệm B).
    - [Keycloak: Authorization Services](https://www.keycloak.org/docs/latest/authorization_services/)

### 🛡️ The "Killer Combo": Kafka + Keycloak Integration
*Đây là câu hỏi "ăn điểm" Senior: Làm sao bảo vệ Kafka?*

- [ ] **Kafka SASL/OAUTHBEARER**
