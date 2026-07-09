#!/usr/bin/env python3
"""E0V Release Bot - Flask Service"""

import json, os, re, base64, logging
from flask import Flask, request, jsonify
from bot import Bot
from emailer import Emailer

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

app = Flask(__name__)
bot = Bot("cli_aac52571b2f81cfa", os.environ.get("FEISHU_APP_SECRET", ""))
emailer = Emailer()
BOT_OPEN_ID = ""


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})


def _is_mentioned(mentions_list, text):
    global BOT_OPEN_ID
    if not mentions_list:
        return False
    for m in mentions_list:
        oid = m.get('id', {}).get('open_id', '') if isinstance(m.get('id'), dict) else ''
        if oid and oid == BOT_OPEN_ID:
            return True
    return '<at ' in text.lower()


def _split_modules(text):
    parts = re.split(r'((?:sdk|apk|health|健康检测)\s*[:：])', text, flags=re.IGNORECASE)
    if len(parts) <= 2:
        return [('', text)]
    result = []
    for i in range(1, len(parts), 2):
        label = parts[i].strip().rstrip(':：')
        body = parts[i + 1] if i + 1 < len(parts) else ''
        result.append((label, (label + ':' + body).strip()))
    return result


@app.route('/feishu/event', methods=['POST'])
def feishu_event():
    global BOT_OPEN_ID
    body = request.get_json(force=True)
    log.info(f"Event: {json.dumps(body, ensure_ascii=False)[:500]}")

    if body.get('type') == 'url_verification':
        return jsonify({"challenge": body.get('challenge', '')})

    header = body.get('header', {})
    if header.get('event_type') != 'im.message.receive_v1':
        return jsonify({"code": 0})

    event = body.get('event', {})
    message = event.get('message', {})
    msg_type = message.get('message_type', '')
    chat_id = message.get('chat_id', '')
    content_str = message.get('content', '{}')
    message_id = message.get('message_id', '')
    mentions = message.get('mentions', [])

    try:
        content = json.loads(content_str)
    except json.JSONDecodeError:
        content = {}

    text = content.get('text', '')

    if not BOT_OPEN_ID:
        for m in mentions:
            oid = m.get('id', {}).get('open_id', '')
            if oid:
                BOT_OPEN_ID = oid
                break

    log.info(f"Msg: chat={chat_id} type={msg_type} bot_id={BOT_OPEN_ID} text={text[:150]}")

    # Text messages - require @mention
    if msg_type == 'text' and text:
        if not _is_mentioned(mentions, text):
            return jsonify({"code": 0})
        sections = _split_modules(text)
        if len(sections) > 1:
            for _, section_text in sections:
                bot.handle_text_message(chat_id, section_text.strip())
            bot.send_message(chat_id, "📋 当前进度:\n" + bot.get_progress(chat_id))
        else:
            _handle_text(chat_id, text)

    # File messages
    elif msg_type in ('file', 'media'):
        file_key = content.get('file_key', '')
        file_name = content.get('file_name', 'file')
        try:
            content_bytes = bot.download_file(message_id, file_key)
        except Exception as e:
            log.error(f"Download error: {e}")
            content_bytes = None

        if content_bytes:
            fname_lower = file_name.lower()
            if any(k in fname_lower for k in ['release', 'note', '发版', 'release note', '版本']):
                bot.add_release_note(chat_id, file_name, content_bytes)
                bot.send_message(chat_id, "✅ 已接收 Release Note: " + file_name + "\n📋 当前进度:\n" + bot.get_progress(chat_id))
            elif any(k in fname_lower for k in ['test', 'report', '测试', '报告']):
                bot.add_test_report(chat_id, file_name, content_bytes)
                bot.send_message(chat_id, "✅ 已接收测试报告: " + file_name + "\n📋 当前进度:\n" + bot.get_progress(chat_id))
            else:
                bot.add_release_note(chat_id, file_name, content_bytes)
                bot.send_message(chat_id, "✅ 已接收文件（作为 Release Note）: " + file_name + "\n📋 当前进度:\n" + bot.get_progress(chat_id))
        else:
            bot.send_message(chat_id, "⚠️ 文件下载失败: " + file_name)

    return jsonify({"code": 0})


def _handle_text(chat_id, text):
    clean = re.sub(r'@\S+', '', text).strip().lower()
    if clean in ['发送', '确认发送', 'send', 'confirm']:
        do_send(chat_id)
    else:
        resp = bot.handle_text_message(chat_id, text)
        if resp:
            bot.send_message(chat_id, resp)


def do_send(chat_id):
    state = bot._load_state(chat_id)
    lines = []
    lines.append("To: " + ", ".join(state['recipients']))
    lines.append("Subject: E0V 版本释放通知")
    lines.append("")
    lines.append("=" * 40)
    lines.append("")

    names = {'sdk': 'SDK', 'apk': 'APK', 'health': '健康检测'}
    lines.append("1. 版本释放链接")
    for mod in ['sdk', 'apk', 'health']:
        data = state['modules'].get(mod, {})
        mr = data.get('mr', [])
        build = data.get('build', [])
        if mr or build:
            lines.append(f"   【{names[mod]}】")
            for u in mr:
                lines.append(f"      MR: {u}")
            for u in build:
                lines.append(f"      Build: {u}")
        else:
            lines.append(f"   【{names[mod]}】本次不发")
    lines.append("")

    lines.append("2. Release Note")
    if state['release_note']:
        lines.append(f"   附件: {state['release_note']['name']}")
    else:
        lines.append("   (无)")
    lines.append("")

    lines.append("3. 测试报告")
    if state['test_report']:
        lines.append(f"   附件: {state['test_report']['name']}")
    else:
        lines.append("   (无)")

    lines.append("")
    lines.append("此邮件由 E0V 版本释放机器人自动生成")

    body = '\n'.join(lines)
    recipients = state['recipients']
    attachments = []
    if state['release_note']:
        attachments.append((state['release_note']['name'], base64.b64decode(state['release_note']['content_b64'])))
    if state['test_report']:
        attachments.append((state['test_report']['name'], base64.b64decode(state['test_report']['content_b64'])))

    success = emailer.send(recipients, "E0V 版本释放通知", body, attachments)
    if success:
        bot.send_message(chat_id, "📧 邮件已发送！\n\n" + body)
    else:
        bot.send_message(chat_id, "📋 邮件内容如下（SMTP 未配置，请复制发送）：\n\n" + body)

    bot.reset(chat_id)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8899))
    app.run(host='0.0.0.0', port=port, debug=False)