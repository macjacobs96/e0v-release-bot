#!/bin/bash
cd /root/e0v-release-bot
export FEISHU_APP_SECRET="z1A5FHFujfeSr5yHwsMxChlMbt0eLCqu"
killall gunicorn 2>/dev/null
sleep 1
nohup ./venv/bin/gunicorn -w 2 -b 0.0.0.0:8899 app:app > /tmp/e0v-bot.log 2>&1 &
echo "Started with PID $!"