# 🚀 E0V 版本释放机器人

<p align="center">
  <img src="docs/product-hero.png" alt="E0V 发版机器人" width="900">
</p>

> **发版，一句话的事。**  
> 飞书群聊协作，@机器人丢链接 → 预览 → 发送，3 步完成版本释放邮件。

---

## 😫 以前 vs 😎 现在

| 😫 以前 | 😎 现在 |
|---------|---------|
| 群聊里来回 @人催链接 | 各负责人群里丢链接即可 |
| 手动复制粘贴整理邮件 | 机器人自动收集、汇总 |
| 容易漏模块、漏链接 | 进度一目了然，缺啥看得到 |
| 文件传来传去版本混乱 | 文件拖进群自动识别分类 |
| 发完还得手动归档 | 说「发版」→「发送」，完事 |

---

## 📋 就 3 步

```mermaid
flowchart LR
    subgraph S1["<b>STEP 1</b><br/>群里丢链接"]
        A1["@机器人 SDK MR: ...<br/>@机器人 APK Build: ...<br/>@机器人 [上传文件]"]
    end
    subgraph S2["<b>STEP 2</b><br/>预览确认"]
        A2["@机器人 发版<br/>查看邮件预览<br/>管理收件人"]
    end
    subgraph S3["<b>STEP 3</b><br/>发送"]
        A3["回复「发送」<br/>📧 邮件发出<br/>自动清空"]
    end
    
    S1 --> S2 --> S3
    
    S1 -.->|任意时刻| C1["📊 进度"]
    S1 -.->|任意时刻| C2["➕ 加收件人"]
    S2 -.->|反悔了| C3["🔄 重置"]
    
    style S1 fill:#eef2ff,stroke:#6366f1,color:#1e293b
    style S2 fill:#fef3c7,stroke:#a855f7,color:#1e293b
    style S3 fill:#f0fdf4,stroke:#22c55e,color:#1e293b
    style C1 fill:#f8fafc,stroke:#cbd5e1,color:#64748b
    style C2 fill:#f8fafc,stroke:#cbd5e1,color:#64748b
    style C3 fill:#f8fafc,stroke:#cbd5e1,color:#64748b
```

多人并行提交，发起人最后确认发送，跟群接龙一样简单。

---

## ✨ 为什么好用

### 🧠 智能模块识别

发「健康检测：」自动归到健康检测模块，不会被 URL 里的 Domain 干扰。SDK / APK 同样自动识别。**两阶段检测**：先看人写的前缀（去 URL），再全文兜底。

### 👥 多人并行协作

SDK 负责人、APK 负责人、测试负责人各发各的，互不干扰。进度实时可见，谁没交一眼就知道。

### 📎 文件自动分类

拖个文件进群，机器人自动判断是 Release Note 还是测试报告，不需要手动标注。

### 📋 进度实时可见

随时发「进度」查看收集状态：

```
📋 当前进度:
  ✅ SDK
  ⬜ APK
  ✅ 健康检测
  ⬜ Release Note
  ✅ 测试报告
```

差啥补啥，清清楚楚。

### 📧 标准化邮件模板

三段式结构：版本链接 + Release Note + 测试报告。模块不发则自动标注「本次不发」，附件 Base64 打包。

```
To: sunaoyu@senseauto.com
Subject: E0V 版本释放通知

1. 版本释放链接
   【SDK】MR: xxx  Build: xxx
   【APK】本次不发
   【健康检测】MR: xxx

2. Release Note — 附件: RN.pdf
3. 测试报告 — 附件: 测试报告.pdf
```

### 🔄 即用即走

发送后自动清空状态，下一轮接着用。收件人列表可精细管理，增删随时生效。

---

## 📖 命令速查

| 命令 | 做什么 |
|------|--------|
| `@机器人 SDK MR: https://...` | 提交 SDK 模块的 MR 和 Build 链接 |
| `@机器人 APK MR: https://...` | 提交 APK 模块的 MR 和 Build 链接 |
| `@机器人 健康检测 MR: https://...` | 提交健康检测模块链接 |
| `@机器人 [上传文件]` | 上传 Release Note 或测试报告 |
| `@机器人 发版` | 预览版本释放邮件 |
| `发送` | 确认发送邮件 |
| `预览` | 查看完整邮件详情 |
| `进度` | 查看各模块收集状态 |
| `加收件人 xxx@email` | 添加邮件收件人 |
| `删收件人 xxx@email` | 删除收件人 |
| `收件人` | 查看收件人列表 |
| `重置` | 清空全部重新开始 |
| `帮助` | 显示使用说明 |

---

## 🏗️ 系统架构

```mermaid
graph TB
    A["💬 飞书群聊<br/>@机器人 提交链接/文件"] -->|"HTTPS /feishu/event"| B["🔒 cloudflared 隧道"]
    B -->|":8899"| C["⚙️ Flask + Gunicorn<br/>app.py"]
    
    C --> D["🧠 bot.py · 消息引擎"]
    C --> E["📧 emailer.py · 邮件"]
    C --> F["🔄 飞书 OpenAPI"]
    
    D --> G[("💾 data/{chat_id}.json")]
    E --> H[("📨 SMTP 腾讯企业邮箱")]
    
    style A fill:#e3f2fd,stroke:#1a73e8,color:#1a1a2e
    style B fill:#fff3e0,stroke:#e65100,color:#1a1a2e
    style C fill:#e8f5e9,stroke:#2e7d32,color:#1a1a2e
    style D fill:#e8f5e9,stroke:#2e7d32,color:#1a1a2e
    style E fill:#fce4ec,stroke:#c62828,color:#1a1a2e
    style F fill:#e3f2fd,stroke:#1a73e8,color:#1a1a2e
    style G fill:#f3e5f5,stroke:#7b1fa2,color:#1a1a2e
    style H fill:#fce4ec,stroke:#c62828,color:#1a1a2e
```

### 技术栈

| 层 | 技术 |
|----|------|
| Web 框架 | Flask + Gunicorn (Python) |
| HTTPS 隧道 | cloudflared (免费) |
| 消息平台 | 飞书开放平台 (tenant_access_token) |
| 邮件 | SMTP STARTTLS (腾讯企业邮箱) |
| 存储 | JSON 文件 (按 chat_id 隔离) |

### 核心文件

| 文件 | 职责 |
|------|------|
| `app.py` | Flask 入口，事件路由，@提及检测，多模块拆分 |
| `bot.py` | 消息解析、两阶段模块识别、状态管理、命令处理 |
| `emailer.py` | SMTP 邮件发送，多收件人 + 附件打包 |
| `start.sh` | 部署启动脚本，gunicorn 后台运行 |

---

## 🔄 完整交互时序

```mermaid
sequenceDiagram
    actor 成员A as 👤 SDK 负责人
    actor 成员B as 👤 APK 负责人
    actor 发起人 as 👤 发起人
    participant 飞书 as 飞书平台
    participant Bot as 🤖 E0V Bot
    
    Note over 成员A,Bot: 📥 收集阶段 — 多人并行提交
    
    成员A->>飞书: @机器人 SDK MR: ... Build: ...
    飞书->>Bot: 事件推送
    Bot->>Bot: 识别模块 → 'sdk'
    Bot->>Bot: 提取 MR/Build 链接
    Bot->>飞书: ✅ 已记录 SDK | 📋 进度
    
    成员B->>飞书: @机器人 APK MR: ...
    飞书->>Bot: 事件推送
    Bot->>飞书: ✅ 已记录 APK | 📋 进度
    
    发起人->>飞书: @机器人 [上传] ReleaseNote.pdf
    飞书->>Bot: 文件事件
    Bot->>飞书: 下载文件 (API)
    Bot->>飞书: ✅ 已接收 Release Note | 📋 进度
    
    Note over 成员A,Bot: 📧 发版阶段 — 发起人确认
    
    发起人->>飞书: @机器人 发版
    飞书->>Bot: 文本消息
    Bot->>Bot: 读取状态 → 组装预览
    Bot->>飞书: 📧 邮件预览 + 操作提示
    
    发起人->>飞书: 发送
    飞书->>Bot: 确认发送
    Bot->>Bot: 组装邮件 → SMTP 发出
    Bot->>Bot: 清空状态
    Bot->>飞书: 📧 邮件已发送！
```

---

## 🚢 部署

```bash
# 服务器: 43.159.43.36
# 路径: /root/e0v-release-bot/

cd /root/e0v-release-bot && bash start.sh

# HTTPS 隧道（飞书事件订阅强制 HTTPS）
cloudflared tunnel --url http://localhost:8899
# → 更新飞书后台「事件订阅」→「请求网址」
```

| 环境变量 | 说明 |
|----------|------|
| `FEISHU_APP_SECRET` | 飞书应用 Secret |
| `SMTP_HOST` | SMTP 服务器 (默认 smtp.exmail.qq.com) |
| `SMTP_PORT` | SMTP 端口 (默认 587) |
| `SMTP_USER` | 发件邮箱 |
| `SMTP_PASS` | 发件邮箱密码 |

---

MIT · [macjacobs96/e0v-release-bot](https://github.com/macjacobs96/e0v-release-bot)
