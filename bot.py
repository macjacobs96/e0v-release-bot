#!/usr/bin/env python3
"""E0V 版本释放机器人 - 核心逻辑"""

import json
import re
import os
import time
import logging
import requests
import threading
from datetime import datetime

log = logging.getLogger(__name__)

MODULES = ['sdk', 'apk', 'health', '健康', '健康检测', 'domain', '域控']

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


class Bot:
    def __init__(self, app_id, app_secret):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token = None
        self._token_ts = 0
        os.makedirs(DATA_DIR, exist_ok=True)

    # ── Feishu API ──────────────────────────────────────────

    def _get_token(self):
        if self._token and time.time() - self._token_ts < 3600:
            return self._token
        resp = requests.post(
            'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
            json={'app_id': self.app_id, 'app_secret': self.app_secret},
            timeout=10
        ).json()
        self._token = resp['tenant_access_token']
        self._token_ts = time.time()
        return self._token

    def send_message(self, chat_id, text):
        token = self._get_token()
        content = json.dumps({"text": text})
        resp = requests.post(
            'https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id',
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json={'receive_id': chat_id, 'msg_type': 'text', 'content': content},
            timeout=15
        )
        data = resp.json()
        if data.get('code') != 0:
            log.error(f"Send message failed: {data}")

    def download_file(self, message_id, file_key):
        """Download a file from Feishu IM."""
        token = self._get_token()
        resp = requests.get(
            f'https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/resources/{file_key}?type=file',
            headers={'Authorization': f'Bearer {token}'},
            timeout=30
        )
        if resp.status_code == 200:
            return resp.content
        log.error(f"Download file failed: {resp.status_code} {resp.text[:200]}")
        return None

    def get_message_content(self, message_id):
        """Get full message content including @mentions"""
        token = self._get_token()
        resp = requests.get(
            f'https://open.feishu.cn/open-apis/im/v1/messages/{message_id}',
            headers={'Authorization': f'Bearer {token}'},
            timeout=10
        )
        return resp.json()

    # ── State management ────────────────────────────────────

    def _state_path(self, chat_id):
        return os.path.join(DATA_DIR, f'{chat_id}.json')

    def _load_state(self, chat_id):
        path = self._state_path(chat_id)
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        return {
            'modules': {},       # {sdk: {mr: '', build: ''}, apk: {...}, health: {...}}
            'release_note': None, # {name: '', content_b64: ''}
            'test_report': None,  # {name: '', content_b64: ''}
            'recipients': ['sunaoyu@senseauto.com'],
            'created_at': datetime.now().isoformat(),
        }

    def _save_state(self, chat_id, state):
        path = self._state_path(chat_id)
        state['updated_at'] = datetime.now().isoformat()
        with open(path, 'w') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    # ── Message parsing ─────────────────────────────────────

    def _detect_module(self, text):
        """Detect which module a message refers to.
        Priority: explicit label before URLs > URL keywords."""
        # Strip URLs to check the human-written prefix first
        import re
        prefix = re.sub(r'https?://\S+', '', text).lower()
        t = text.lower()

        # Check explicit labels first (strongest signal)
        # 'health/健康' must come before 'sdk/domain' since health messages
        # often contain 'Domain Build' URLs that would falsely match SDK
        if any(kw in prefix for kw in ['健康检测', '健康', 'health', '体检']):
            return 'health'
        if any(kw in prefix for kw in ['sdk', '域控', '域控制器']):
            return 'sdk'
        if any(kw in prefix for kw in ['apk', '客户端', '安卓', 'app包']):
            return 'apk'

        # Explicit label not found, try URL-based detection
        if any(kw in t for kw in ['健康检测', '健康', 'health', '体检']):
            return 'health'
        if any(kw in t for kw in ['sdk', '域控', '域控制器', 'domain']):
            return 'sdk'
        if any(kw in t for kw in ['apk', 'app', '客户端', '安卓']):
            return 'apk'
        return None

    def _extract_links(self, text):
        """Extract URLs from text, classify as MR or Build"""
        urls = re.findall(r'https?://[^\s]+', text)
        mr_links = []
        build_links = []
        for url in urls:
            url_lower = url.lower()
            if any(kw in url_lower for kw in ['merge_request', 'mr', 'pull', 'pr', 'gitlab', 'github']):
                mr_links.append(url)
            else:
                build_links.append(url)
        return mr_links, build_links

    def _parse_at_mentions(self, text):
        """Remove @mentions from text, return clean text"""
        # Feishu @mentions look like @_user_1 or @username
        # The raw text from Feishu uses @_user_ID format
        return re.sub(r'@\S+', '', text).strip()

    # ── Module actions ──────────────────────────────────────

    def add_module_links(self, chat_id, mod, mr_links, build_links):
        state = self._load_state(chat_id)
        if mod not in state['modules']:
            state['modules'][mod] = {'mr': [], 'build': []}

        mod_data = state['modules'][mod]
        for url in mr_links:
            if url not in mod_data['mr']:
                mod_data['mr'].append(url)
        for url in build_links:
            if url not in mod_data['build']:
                mod_data['build'].append(url)

        self._save_state(chat_id, state)

    def add_release_note(self, chat_id, file_name, file_content):
        import base64
        state = self._load_state(chat_id)
        state['release_note'] = {
            'name': file_name,
            'content_b64': base64.b64encode(file_content).decode(),
        }
        self._save_state(chat_id, state)

    def add_test_report(self, chat_id, file_name, file_content):
        import base64
        state = self._load_state(chat_id)
        state['test_report'] = {
            'name': file_name,
            'content_b64': base64.b64encode(file_content).decode(),
        }
        self._save_state(chat_id, state)

    def add_recipient(self, chat_id, email):
        state = self._load_state(chat_id)
        if email not in state['recipients']:
            state['recipients'].append(email)
            self._save_state(chat_id, state)
            return True
        return False

    def remove_recipient(self, chat_id, email):
        state = self._load_state(chat_id)
        if email in state['recipients']:
            state['recipients'].remove(email)
            self._save_state(chat_id, state)
            return True
        return False

    def reset(self, chat_id):
        state = {
            'modules': {},
            'release_note': None,
            'test_report': None,
            'recipients': ['sunaoyu@senseauto.com'],
            'created_at': datetime.now().isoformat(),
        }
        self._save_state(chat_id, state)

    # ── Progress display ────────────────────────────────────

    def get_progress(self, chat_id):
        state = self._load_state(chat_id)
        lines = []
        for mod in ['sdk', 'apk', 'health']:
            data = state['modules'].get(mod, {})
            has_mr = bool(data.get('mr'))
            has_build = bool(data.get('build'))
            if has_mr or has_build:
                icon = '✅'
            else:
                icon = '⬜'
            names = {'sdk': 'SDK', 'apk': 'APK', 'health': '健康检测'}
            lines.append(f"  {icon} {names[mod]}")
        lines.append(f"  {'✅' if state['release_note'] else '⬜'} Release Note")
        lines.append(f"  {'✅' if state['test_report'] else '⬜'} 测试报告")
        return '\n'.join(lines)

    # ── Text message handler ────────────────────────────────

    def handle_text_message(self, chat_id, text):
        """Returns response text or None"""
        text = self._parse_at_mentions(text).strip()
        if not text:
            return None

        log.info(f"Handling: {text}")

        # ── URL submission ──
        if 'http' in text:
            mod = self._detect_module(text)
            mr_links, build_links = self._extract_links(text)
            if not mod:
                # Try to infer from context of links
                for url in mr_links + build_links:
                    inferred = self._detect_module(url)
                    if inferred:
                        mod = inferred
                        break
            if not mod:
                return "⚠️ 未能识别模块，请注明 SDK / APK / 健康检测\n如: @机器人 SDK MR: https://..."

            self.add_module_links(chat_id, mod, mr_links, build_links)
            names = {'sdk': 'SDK', 'apk': 'APK', 'health': '健康检测'}
            parts = []
            if mr_links:
                parts.append(f"MR: {', '.join(mr_links)}")
            if build_links:
                parts.append(f"Build: {', '.join(build_links)}")
            return f"✅ 已记录 {names[mod]} 模块\n{' | '.join(parts)}\n\n📋 当前进度:\n{self.get_progress(chat_id)}"

        # ── Commands ──
        cmd = text.strip().lower()

        if cmd in ['发版', '发送', 'release', 'send']:
            return self._build_preview(chat_id)

        if cmd in ['进度', '状态', 'status', 'progress']:
            return f"📋 当前进度:\n{self.get_progress(chat_id)}"

        if cmd in ['重置', '清空', 'reset', 'clear']:
            self.reset(chat_id)
            return "🔄 已重置，请重新提交版本信息"

        if cmd in ['预览', 'preview']:
            return self._build_full_preview(chat_id)

        if cmd.startswith('加收件人') or cmd.startswith('+收件人') or cmd.startswith('添加收件人'):
            email_match = re.search(r'[\w.-]+@[\w.-]+', text)
            if email_match:
                email = email_match.group(0)
                if self.add_recipient(chat_id, email):
                    state = self._load_state(chat_id)
                    return f"✅ 已添加收件人: {email}\n当前收件人: {', '.join(state['recipients'])}"
                return "该收件人已存在"
            return "请提供邮箱地址，如: 加收件人 xxx@senseauto.com"

        if cmd.startswith('删收件人') or cmd.startswith('-收件人') or cmd.startswith('删除收件人'):
            email_match = re.search(r'[\w.-]+@[\w.-]+', text)
            if email_match:
                email = email_match.group(0)
                if self.remove_recipient(chat_id, email):
                    state = self._load_state(chat_id)
                    return f"✅ 已删除收件人: {email}\n当前收件人: {', '.join(state['recipients'])}"
                return "未找到该收件人"
            return "请提供邮箱地址，如: 删收件人 xxx@senseauto.com"

        if cmd in ['收件人', 'recipients', '收件人列表']:
            state = self._load_state(chat_id)
            return f"📧 当前收件人: {', '.join(state['recipients'])}"

        if cmd in ['帮助', 'help', '?']:
            return self._help_text()

        return None

    # ── Preview / build ─────────────────────────────────────

    def _build_preview(self, chat_id):
        state = self._load_state(chat_id)
        has_any = any(state['modules'].values()) or state['release_note'] or state['test_report']
        if not has_any:
            return "⚠️ 还没有收集到任何版本信息，请先提交链接或文件"

        lines = ["📧 待发送版本释放邮件", "=" * 33, ""]

        names = {'sdk': 'SDK', 'apk': 'APK', 'health': '健康检测'}
        for mod in ['sdk', 'apk', 'health']:
            data = state['modules'].get(mod, {})
            mr = data.get('mr', [])
            build = data.get('build', [])
            if mr or build:
                lines.append(f"  {names[mod]}:")
                if mr:
                    for u in mr:
                        lines.append(f"    MR: {u}")
                if build:
                    for u in build:
                        lines.append(f"    Build: {u}")
            else:
                lines.append(f"  {names[mod]}: (未提供)")

        lines.append("")
        lines.append(f"  Release Note: {state['release_note']['name'] if state['release_note'] else '(未提供)'}")
        lines.append(f"  测试报告: {state['test_report']['name'] if state['test_report'] else '(未提供)'}")
        lines.append("")
        lines.append(f"📧 收件人: {', '.join(state['recipients'])}")
        lines.append("")
        lines.append("回复「发送」确认 | 「预览」查看完整邮件 | 「重置」清空 | 「+收件人 xxx」添加")

        return '\n'.join(lines)

    def _build_full_preview(self, chat_id):
        """Detailed preview with full MR/build listing"""
        state = self._load_state(chat_id)
        lines = ["📧 完整邮件预览", "=" * 33, ""]

        lines.append(f"To: {', '.join(state['recipients'])}")
        lines.append("Subject: E0V 版本释放通知")
        lines.append("")

        names = {'sdk': 'SDK', 'apk': 'APK', 'health': '健康检测'}
        has_modules = False
        lines.append("1. 版本释放链接")
        for mod in ['sdk', 'apk', 'health']:
            data = state['modules'].get(mod, {})
            mr = data.get('mr', [])
            build = data.get('build', [])
            if mr or build:
                has_modules = True
                lines.append(f"   [{names[mod]}]")
                for u in mr:
                    lines.append(f"      MR: {u}")
                for u in build:
                    lines.append(f"      Build: {u}")

        if not has_modules:
            lines.append("   (无)")

        lines.append("")
        lines.append("2. Release Note")
        lines.append(f"   附件: {state['release_note']['name'] if state['release_note'] else '(无)'}")

        lines.append("")
        lines.append("3. 测试报告")
        lines.append(f"   附件: {state['test_report']['name'] if state['test_report'] else '(无)'}")

        lines.append("")
        lines.append("---")
        lines.append("回复「发送」确认发送")

        return '\n'.join(lines)

    # ── Help ─────────────────────────────────────────────────

    def _help_text(self):
        return """🤖 E0V 版本释放机器人

使用方法:
  提交链接: @机器人 SDK MR: <链接> Build: <链接>
  提交文件: 直接发文件到群里 @机器人 说明类型
  查看进度: @机器人 进度
  发版:     @机器人 发版
  预览邮件: @机器人 预览
  管理收件人: @机器人 加收件人 xxx@email / 删收件人 xxx@email
  重置:     @机器人 重置

支持的模块: SDK / APK / 健康检测"""