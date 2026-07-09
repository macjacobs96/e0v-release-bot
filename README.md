# E0V 版本释放机器人

> 🎨 **产品介绍页**: [macjacobs96.github.io/e0v-release-bot/product-page.html](https://macjacobs96.github.io/e0v-release-bot/product-page.html) — 给领导看的

飞书群聊协作模式，自动化 E0V 版本释放流程：收集 SDK / APK / 健康检测的 MR 和 Build 链接，上传 Release Note 和测试报告，一键编译发送版本释放邮件。

## 一句话说清楚

> 以前发版要在群里来回 @人收集链接、手动整理邮件；现在大家各自把链接扔群里，机器人自动收集，最后说一声「发版」就完事。

```mermaid
flowchart LR
    A["以前 😫<br/>群聊来回催<br/>手动整理邮件<br/>容易漏模块"] -->|"自动化"| B["现在 😎<br/>@机器人丢链接<br/>进度实时可见<br/>一键发版"]
    
    style A fill:#fce4ec,stroke:#c62828,color:#1a1a2e
    style B fill:#e8f5e9,stroke:#2e7d32,color:#1a1a2e
```

## 怎么用（就 3 步）

```mermaid
flowchart TD
    S1["<b>第 1 步：群里丢链接</b><br/>@机器人 SDK MR: https://...<br/>@机器人 APK MR: https://...<br/>@机器人 [上传 Release Note]<br/>@机器人 [上传测试报告]<br/><br/>谁负责哪个模块，谁就发哪个"] -->
    S2["<b>第 2 步：预览确认</b><br/>@机器人 发版<br/><br/>机器人展示邮件内容<br/>SDK ✅ APK ✅ 健康检测 ✅<br/>收件人：xxx@email<br/><br/>不放心就发「预览」看详情"] -->
    S3["<b>第 3 步：发送</b><br/>回复「发送」<br/><br/>📧 邮件发出！<br/>自动清空，下一轮接着用"]
    
    S1 -.->|"任意时候"| C1["查看进度"]
    S1 -.->|"任意时候"| C2["加/删收件人"]
    S2 -.->|"反悔了"| C3["重置重来"]
    
    style S1 fill:#e3f2fd,stroke:#1a73e8,color:#1a1a2e
    style S2 fill:#fff3e0,stroke:#e65100,color:#1a1a2e
    style S3 fill:#e8f5e9,stroke:#2e7d32,color:#1a1a2e
    style C1 fill:#f5f5f5,stroke:#999,color:#666
    style C2 fill:#f5f5f5,stroke:#999,color:#666
    style C3 fill:#f5f5f5,stroke:#999,color:#666
```

| 命令 | 作用 |
|------|------|
| `@机器人 <链接>` | 提交 MR/Build 链接，自动识别是 SDK/APK/健康检测 |
| `@机器人 [上传文件]` | 上传 Release Note 或测试报告 |
| `@机器人 发版` | 预览邮件 |
| `发送` | 确认发出版本释放邮件 |
| `进度` | 看看还差哪些没交 |
| `重置` | 全部清空重新来 |

## 系统架构

```mermaid
graph TB
    A["💬 飞书群聊<br/>@机器人 提交链接/文件"] -->|"HTTPS POST<br/>/feishu/event"| B["🔒 cloudflared 隧道<br/>trycloudflare.com"]
    B -->|":8899"| C["⚙️ Gunicorn + Flask<br/>app.py"]
    
    C --> D["🧠 bot.py<br/>消息解析 · 模块识别<br/>状态管理 · 邮件编译"]
    C --> E["📧 emailer.py<br/>SMTP 邮件发送"]
    C --> F["🔄 飞书 OpenAPI<br/>发送消息 · 下载文件"]
    
    D --> G[("💾 data/{chat_id}.json<br/>模块 MR/Build<br/>附件 Base64")]
    E --> H[("📨 SMTP<br/>腾讯企业邮箱 :587")]
    
    style A fill:#e3f2fd,stroke:#1a73e8,color:#1a1a2e
    style B fill:#fff3e0,stroke:#e65100,color:#1a1a2e
    style C fill:#e8f5e9,stroke:#2e7d32,color:#1a1a2e
    style D fill:#e8f5e9,stroke:#2e7d32,color:#1a1a2e
    style E fill:#fce4ec,stroke:#c62828,color:#1a1a2e
    style F fill:#e3f2fd,stroke:#1a73e8,color:#1a1a2e
    style G fill:#f3e5f5,stroke:#7b1fa2,color:#1a1a2e
    style H fill:#fce4ec,stroke:#c62828,color:#1a1a2e
```

### 核心组件

| 文件 | 职责 |
|------|------|
| `app.py` | Flask 服务入口，事件路由 (POST /feishu/event)，@提及检测，多模块拆分 |
| `bot.py` | 核心逻辑：消息解析、两阶段模块识别、状态读写、命令处理 |
| `emailer.py` | SMTP 邮件发送，支持多收件人 + 附件打包 |
| `start.sh` | 部署启动脚本，设置环境变量，gunicorn 后台运行 |

### 模块识别 (两阶段检测)

```
1. Phase 1 — 去 URL 看「人写的文字」前缀 (高优先级)
   健康检测 > SDK > APK

2. Phase 2 — 全文回退兜底 (低优先级)
   避免 URL 中 Domain 等关键词误触
```

## 交互流程

```mermaid
sequenceDiagram
    actor 群成员A as 👤 群成员 A
    actor 群成员B as 👤 群成员 B
    participant 飞书 as 飞书开放平台
    participant Bot as 🤖 E0V Bot
    participant 存储 as 💾 JSON
    
    Note over 群成员A,存储: Phase 1 — 收集链接
    群成员A->>飞书: @机器人 SDK MR: https://... Build: https://...
    飞书->>Bot: POST /feishu/event
    Bot->>Bot: _detect_module() → 'sdk'
    Bot->>Bot: _extract_links() → MR ×1, Build ×1
    Bot->>存储: save → modules.sdk = {mr:[...], build:[...]}
    Bot->>飞书: 回复: ✅ 已记录 SDK | 📋 进度
    
    群成员B->>飞书: @机器人 APK MR: https://...
    飞书->>Bot: POST /feishu/event
    Bot->>存储: save → modules.apk
    Bot->>飞书: 回复: ✅ 已记录 APK | 📋 进度
    
    Note over 群成员A,存储: Phase 2 — 上传文件
    群成员A->>飞书: @机器人 [上传] ReleaseNote.pdf
    飞书->>Bot: file_key
    Bot->>飞书: download_file(API)
    飞书-->>Bot: 文件内容 (bytes)
    Bot->>存储: save → release_note (base64)
    Bot->>飞书: 回复: ✅ 已接收 | 📋 进度
    
    Note over 群成员A,存储: Phase 3 — 预览确认
    群成员A->>飞书: @机器人 发版
    飞书->>Bot: 文本消息
    Bot->>存储: 读取全部 state
    Bot->>Bot: _build_preview()
    Bot->>飞书: 回复: 📧 邮件预览 + 收件人 + 操作提示
    
    Note over 群成员A,存储: Phase 4 — 发送
    群成员A->>飞书: 发送
    飞书->>Bot: 确认发送
    Bot->>Bot: do_send() → 组装邮件模板
    Bot->>Bot: Emailer.send(SMTP)
    Bot->>存储: reset() → 清空状态
    Bot->>飞书: 回复: 📧 邮件已发送！
```

## 命令一览

| 命令 | 作用 |
|------|------|
| `@机器人 <链接>` | 提交 MR/Build 链接，自动识别模块 |
| `@机器人 [上传文件]` | 上传 Release Note 或测试报告 |
| `@机器人 发版` | 预览版本释放邮件 |
| `发送` | 确认发送邮件 |
| `预览` | 查看完整邮件内容 |
| `进度` / `状态` | 查看当前收集进度 |
| `加收件人 xxx@email` | 添加收件人 |
| `删收件人 xxx@email` | 删除收件人 |
| `收件人` | 查看收件人列表 |
| `重置` / `清空` | 清空重新开始 |
| `帮助` | 显示使用说明 |

## 邮件模板

```
To: sunaoyu@senseauto.com, ...
Subject: E0V 版本释放通知

1. 版本释放链接
   【SDK】MR: xxx  Build: xxx
   【APK】MR: xxx  Build: xxx
   【健康检测】MR: xxx  Build: xxx

2. Release Note
   附件: ReleaseNote.pdf

3. 测试报告
   附件: 测试报告.pdf

此邮件由 E0V 版本释放机器人自动生成
```

## 部署

```bash
# 服务器: 43.159.43.36
# 路径: /root/e0v-release-bot/

# 启动
cd /root/e0v-release-bot && bash start.sh

# HTTPS 隧道 (飞书事件订阅需要)
cloudflared tunnel --url http://localhost:8899
# → 更新飞书后台「事件订阅」→「请求网址」
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `FEISHU_APP_SECRET` | 飞书应用 Secret (`start.sh`) |
| `SMTP_HOST` | SMTP 服务器 (默认 `smtp.exmail.qq.com`) |
| `SMTP_PORT` | SMTP 端口 (默认 `587`) |
| `SMTP_USER` | 发件邮箱地址 |
| `SMTP_PASS` | 发件邮箱密码 |

## License

MIT
