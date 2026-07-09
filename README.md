# E0V 版本释放机器人

飞书群聊协作模式，自动化 E0V 版本释放流程：收集 SDK / APK / 健康检测的 MR 和 Build 链接，上传 Release Note 和测试报告，一键编译发送版本释放邮件。

## 架构

```
飞书群聊 (@机器人)
    ↓ /feishu/event (HTTPS)
cloudflared 隧道
    ↓ localhost:8899
Flask + Gunicorn
    ├── bot.py     核心逻辑
    ├── emailer.py SMTP 邮件
    └── data/      状态存储
```

📐 [系统架构图](docs/architecture-diagram.html) | 🔗 [交互链路图](docs/flow-diagram.html)

## 部署

```bash
# 服务器: 43.159.43.36
cd /root/e0v-release-bot
bash start.sh
```

## 使用

群聊里 @机器人：

```
@机器人 SDK MR: https://...  Build: https://...
@机器人 APK MR: https://...
@机器人 [上传 Release Note]
@机器人 [上传测试报告]
@机器人 发版        # 预览
发送               # 确认发送
```

## 命令

| 命令 | 作用 |
|------|------|
| `@机器人 <链接>` | 提交 MR/Build 链接 |
| `@机器人 [文件]` | 上传 Release Note/测试报告 |
| `@机器人 发版` | 预览邮件 |
| `发送` | 确认发送 |
| `预览` | 查看完整邮件 |
| `进度` | 查看收集状态 |
| `加收件人 x` | 添加收件人 |
| `重置` | 清空重新开始 |

## License

MIT
