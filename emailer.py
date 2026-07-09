#!/usr/bin/env python3
"""E0V 版本释放机器人 - 邮件发送"""

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

log = logging.getLogger(__name__)


class Emailer:
    def __init__(self):
        self.smtp_host = os.environ.get('SMTP_HOST', 'smtp.exmail.qq.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.smtp_user = os.environ.get('SMTP_USER', '')
        self.smtp_pass = os.environ.get('SMTP_PASS', '')

    def send(self, to_list, subject, body, attachments=None):
        """发送邮件。
        to_list: list of email strings
        subject: str
        body: str (plain text or HTML)
        attachments: list of (filename, content_bytes)
        """
        if not self.smtp_user:
            log.warning("SMTP not configured, would send: %s", subject)
            return False

        msg = MIMEMultipart()
        msg['From'] = self.smtp_user
        msg['To'] = ', '.join(to_list)
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        if attachments:
            for fname, content in attachments:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(content)
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{fname}"')
                msg.attach(part)

        try:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
            server.starttls()
            server.login(self.smtp_user, self.smtp_pass)
            server.sendmail(self.smtp_user, to_list, msg.as_string())
            server.quit()
            log.info(f"Email sent to {to_list}: {subject}")
            return True
        except Exception as e:
            log.error(f"Email send failed: {e}")
            return False