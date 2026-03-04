---
title: "Giới thiệu Headless CMS trên GitHub"
tags: ["cms", "github", "tutorial"]
date: "2026-03-04"
author: "nathan.huynh"
summary: "Hướng dẫn xây dựng hệ thống Headless CMS đơn giản sử dụng GitHub và Python."
---

# Giới thiệu Headless CMS trên GitHub

Headless CMS là hệ thống quản lý nội dung tách biệt phần backend (lưu trữ, xử lý) khỏi phần frontend (hiển thị).

## Tại sao dùng GitHub?

- **Miễn phí**: GitHub cung cấp hosting tĩnh và CI/CD miễn phí.
- **Version control**: Mọi thay đổi đều được theo dõi.
- **Đơn giản**: Chỉ cần push file Markdown là xong.

## Cấu trúc hệ thống

```
content/          # Bài viết Markdown
scripts/          # Script xử lý
public/           # Output JSON
.github/workflows # CI/CD
```

## Luồng hoạt động

1. Viết bài viết dạng Markdown vào `content/`
2. Push lên GitHub
3. GitHub Actions chạy `processor.py`
4. `index.json` được cập nhật tự động
5. Frontend đọc `index.json` và hiển thị
