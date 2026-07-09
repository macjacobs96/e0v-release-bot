# E0V 版本释放机器人 — 部署指南

## 当前部署状态

- 服务器: 43.159.43.36
- 路径: /root/e0v-release-bot/
- 状态: 核心代码已完成，**HTTPS 端点尚未配置**（飞书事件订阅需要 HTTPS URL）

## 文件结构

```
/root/e0v-release-bot/
  app.py              # Flask 服务主文件
  bot.py              # 核心逻辑（消息解析、状态管理、预览生成）
  emailer.py          # SMTP 邮件发送
  requirements.txt    # flask, requests, gunicorn
  venv/               # Python 虚拟环境
  data/               # 群聊状态存储（运行时自动创建）
```

## 启动命令

```bash
cd /root/e0v-release-bot
# 开发模式
./venv/bin/python app.py
# 生产模式
./venv/bin/gunicorn -w 2 -b 0.0.0.0:8899 app:app
```

## HTTPS 配置方案

### 方案 A: ngrok（临时/测试）
```bash
ngrok http 8899
# 得到 https://xxxx.ngrok-free.app
# 飞书开放平台 → 事件订阅 → 请求网址: https://xxxx.ngrok-free.app/feishu/event
```

### 方案 B: Let's Encrypt + 域名
需要有域名指向 43.159.43.36。
```bash
certbot certonly --nginx -d your-domain.com
# 然后配置 nginx 反代到 8899
```

## 飞书开放平台配置

1. 进入 https://open.feishu.cn → 应用 → E0V版本释放机器人
2. 添加应用能力 → 机器人
3. 事件订阅 → 请求网址: `https://<domain>/feishu/event`
4. 订阅事件: `im.message.receive_v1`（接收消息）
5. 权限管理 → 申请权限:
   - `im:message`（获取消息）
   - `im:message:send_as_bot`（发送消息）
   - `im:resource`（获取消息中的资源文件）
6. 发布版本 → 创建版本并发布
7. 将机器人添加到目标群聊

## 代码部署命令

当需要更新代码时：
```bash
# 本地编码后
sshpass -p 'SayIlike23' ssh root@43.159.43.36
# 重启服务
pkill -f gunicorn
cd /root/e0v-release-bot && ./venv/bin/gunicorn -w 2 -b 0.0.0.0:8899 app:app &
```
