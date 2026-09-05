#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import zipfile
import smtplib
from datetime import datetime, date
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

try:
    from backup_config import SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASS, BACKUP_EMAIL
except ImportError:
    SMTP_SERVER = os.environ.get('BACKUP_SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('BACKUP_SMTP_PORT', '587'))
    SMTP_USER = os.environ.get('BACKUP_SMTP_USER', '')
    SMTP_PASS = os.environ.get('BACKUP_SMTP_PASS', '')
    BACKUP_EMAIL = os.environ.get('BACKUP_EMAIL', '')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
os.makedirs(BACKUP_DIR, exist_ok=True)

BACKUP_ITEMS = [
    'traders.json',
    'categories.json',
    'counters.json',
    'shown_history.json',
    'users.json',
    'message_stats.json',
    'ads.json',
    'ads_stats.json',
    'unmatched_queries.json',
    'traders_submissions.json',
    'static',
    'templates',
]

def log(msg):
    now = datetime.now().strftime('%H:%M:%S')
    print(f'[{now}] {msg}')
    with open(os.path.join(BACKUP_DIR, 'backup.log'), 'a', encoding='utf-8') as f:
        f.write(f'{datetime.now()} | {msg}\n')

def create_backup():
    log('بدء إنشاء النسخة الاحتياطية...')
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    name = f'sajjana_backup_{ts}.zip'
    path = os.path.join(BACKUP_DIR, name)
    count = 0
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for item in BACKUP_ITEMS:
            item_path = os.path.join(BASE_DIR, item)
            if os.path.isfile(item_path):
                zf.write(item_path, arcname=item)
                count += 1
                log(f'  + ملف: {item}')
            elif os.path.isdir(item_path):
                for root, dirs, files in os.walk(item_path):
                    for f in files:
                        full = os.path.join(root, f)
                        arc = os.path.relpath(full, BASE_DIR)
                        zf.write(full, arcname=arc)
                        count += 1
                log(f'  + مجلد: {item}')
            else:
                log(f'  ! غير موجود: {item}')
    size = os.path.getsize(path) / 1024
    log(f'تم إنشاء: {name} ({count} عنصر, {size:.1f} KB)')
    return path

def send_email(path):
    if not all([SMTP_USER, SMTP_PASS, BACKUP_EMAIL]):
        log('! إعدادات البريد ناقصة - النسخة محفوظة محلياً فقط')
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = BACKUP_EMAIL
        msg['Subject'] = f'نسخة السجانة - {date.today().isoformat()}'
        body = (f'السلام عليكم،\nهذي نسخة واتساب السجانة اليومية.\n\n'
                f'التاريخ: {date.today().isoformat()}\n'
                f'الملف: {os.path.basename(path)}\n'
                f'الحجم: {os.path.getsize(path)/1024:.1f} KB\n')
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        with open(path, 'rb') as f:
            part = MIMEBase('application', 'zip')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(path)}')
            msg.attach(part)
        s = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
        s.quit()
        log(f'تم الإرسال: {BACKUP_EMAIL}')
        return True
    except Exception as e:
        log(f'فشل الإرسال: {e}')
        return False

def cleanup(keep=7):
    log('تنظيف النسخ القديمة...')
    removed = 0
    for f in os.listdir(BACKUP_DIR):
        if f.startswith('sajjana_backup_') and f.endswith('.zip'):
            p = os.path.join(BACKUP_DIR, f)
            days = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(p))).days
            if days > keep:
                os.remove(p)
                removed += 1
    log(f'تم مسح {removed} نسخة قديمة')

def main():
    log('=' * 50)
    log('بدء النسخ الاحتياطي')
    archive = create_backup()
    send_email(archive)
    cleanup()
    log('انتهى النسخ الاحتياطي')
    log('=' * 50)

if __name__ == '__main__':
    main()
