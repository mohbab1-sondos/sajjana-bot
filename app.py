import os
import json
import random
import re
import uuid
from datetime import date 

import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

from backup import main as run_backup_job

# =========================================================
# الإعدادات
# =========================================================
ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "sajjana123")
ADMIN_KEY = os.environ.get("SAJJANA_ADMIN_KEY", "sajjana_admin_2026")
OWNER_WHATSAPP_NUMBER = os.environ.get("OWNER_WHATSAPP_NUMBER", "")

GRAPH_API_URL = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"

BASE_DIR = os.path.dirname(__file__)
TRADERS_FILE = os.path.join(BASE_DIR, "traders.json")
CATEGORIES_FILE = os.path.join(BASE_DIR, "categories.json")
COUNTERS_FILE = os.path.join(BASE_DIR, "counters.json")
SHOWN_FILE = os.path.join(BASE_DIR, "shown_history.json")
USERS_FILE = os.path.join(BASE_DIR, "users.json")
STATS_FILE = os.path.join(BASE_DIR, "message_stats.json")
ADS_FILE = os.path.join(BASE_DIR, "ads.json")
ADS_STATS_FILE = os.path.join(BASE_DIR, "ads_stats.json")
ADS_UPLOAD_DIR = os.path.join(BASE_DIR, "static", "ads")
UNMATCHED_FILE = os.path.join(BASE_DIR, "unmatched_queries.json")
SITE_BASE_URL = "https://mohbab.pythonanywhere.com"
PHONE_NUMBER_DISPLAY = "201554042773"

REGISTER_URL = "https://mohbab.pythonanywhere.com/register"

TRADER_DAILY_LIMIT = 15
SHOPPER_DAILY_LIMIT = 15
MAX_TRADERS_PER_REPLY = 4
PRIORITY_SLOTS = 2

JOIN_ROW_ID = "cat_join_trader"

WELCOME_TEXT = "🏗️ أهلاً بيكم في واتساب السجانة! اختار التخصص اللي بتفتش عليهو من القائمة تحت:"
NOT_FOUND_MESSAGE = (
    "ما لقيناهو دا للأسف 🤔\n"
    "اكتب اسم التخصص، أو اكتب كلمة \"قائمة\" عشان تشوف كل الخيارات."
)
EMPTY_CATEGORY_MESSAGE = "للأسف لسه ما عندنا تجار مسجلين في التخصص دا، جرّب تاني قريب 🙏"
LIMIT_REACHED_MESSAGE = (
    "وصلت لأقصى عدد رسائل مسموح به اليوم  🙏\n"
    "جرّب تاني بكرة، أو لو الموضوع مستعجل كلّمنا مباشرة."
)
JOIN_REPLY_TEXT = (
    f"يسعدنا انضمامك لواتساب السجانة! 🎉\n"
    f"سجّل بياناتك من الرابط دا (بياخد دقيقة بس):\n{REGISTER_URL}"
)
EXISTING_TRADER_REPLY_TEXT = (
    "أهلا بيك تاني! 👋 لاحظنا إن رقمك مسجل عندنا خلاص.\n\n"
    f"تأكد من بياناتك أو صحّحها من هنا:\n{SITE_BASE_URL}/check\n\n"
    f"أو لو عايز تسجل محل جديد:\n{REGISTER_URL}"
)
ASK_PRODUCT_TEXT = "تمام 👍 اكتب اسم الصنف ال بتفتش عليه، أو كلمة \"قائمة\" عشان تشوف كل التخصصات."
TRADER_THANK_YOU_TEXT = (
    "شكراً ليك على تسجيلك في واتساب السجانة! 🎉\n"
    "طلبك الان قيد المراجعة، وح نبلّغك بالواتساب فور ما يتم اعتماده.\n\n"
    "لو داير تساعدنا، شارك رابط التسجيل مع تجار تعرفهم في السوق:\n"
    f"{REGISTER_URL}"
)
ROLE_TRADER_ID = "role_trader"
ROLE_CUSTOMER_ID = "role_customer"


# =========================================================
# تخزين بسيط في ملفات JSON
# =========================================================
def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =========================================================
# البيانات الأولية (تتحمل مرة واحدة بس لو الملفات مش موجودة)
# =========================================================
DEFAULT_CATEGORIES = [
    {"id": "cat_decor", "title": "ديكورات", "match": ["ديكور", "ديكورات", "تشطيب", "جبس"]},
    {"id": "cat_ceramic", "title": "سيراميك", "match": ["سيراميك", "بلاط", "بورسلين"]},
    {"id": "cat_cement", "title": "اسمنت", "match": ["اسمنت", "سمنت"]},
    {"id": "cat_electric", "title": "كهرباء", "match": ["كهرباء", "اسلاك", "لمبات"]},
    {"id": "cat_plumbing", "title": "سباكة", "match": ["سباكة", "مواسير", "انابيب", "حنفيات"]},
    {"id": "cat_iron", "title": "حديد", "match": ["حديد", "حديد تسليح"]},
    {"id": "cat_other", "title": "أخرى", "match": []},
]

DEFAULT_TRADERS = [
    {"id": "t1", "name": "ديزاين لاين", "whatsapp": "249912351105", "category_id": "cat_decor",
     "location": "شارع النص", "details": "", "status": "approved", "visibility": "normal"},
    {"id": "t2", "name": "حسين", "whatsapp": "966562762669", "category_id": "cat_ceramic",
     "location": "شارع سوداتل", "details": "", "status": "approved", "visibility": "normal"},
    {"id": "t3", "name": "سامي", "whatsapp": "249918213703", "category_id": "cat_cement",
     "location": "شارع الحرية", "details": "", "status": "approved", "visibility": "normal"},
    {"id": "t4", "name": "شوقي", "whatsapp": "249927382171", "category_id": "cat_electric",
     "location": "شارع البوسنة", "details": "", "status": "approved", "visibility": "normal"},
    {"id": "t5", "name": "محمد", "whatsapp": "249123091999", "category_id": "cat_plumbing",
     "location": "الملجة", "details": "", "status": "approved", "visibility": "normal"},
]


def get_categories():
    return load_json(CATEGORIES_FILE, DEFAULT_CATEGORIES)


def get_category_by_id(cat_id):
    for c in get_categories():
        if c["id"] == cat_id:
            return c
    return None


def get_traders():
    return load_json(TRADERS_FILE, DEFAULT_TRADERS)


def save_traders(traders):
    save_json(TRADERS_FILE, traders)


# نتأكد إن الملفات الأساسية موجودة من أول تشغيل
if not os.path.exists(CATEGORIES_FILE):
    save_json(CATEGORIES_FILE, DEFAULT_CATEGORIES)
if not os.path.exists(TRADERS_FILE):
    save_json(TRADERS_FILE, DEFAULT_TRADERS)
os.makedirs(ADS_UPLOAD_DIR, exist_ok=True)


def is_new_user(phone_number):
    users = load_json(USERS_FILE, {})
    return phone_number not in users


def get_user_role(phone_number):
    users = load_json(USERS_FILE, {})
    return users.get(phone_number, {}).get("role")


def set_user_role(phone_number, role):
    users = load_json(USERS_FILE, {})
    users.setdefault(phone_number, {"first_seen": str(date.today())})
    users[phone_number]["role"] = role
    save_json(USERS_FILE, users)


def register_new_user(phone_number):
    users = load_json(USERS_FILE, {})
    if phone_number not in users:
        users[phone_number] = {"first_seen": str(date.today()), "role": None}
        save_json(USERS_FILE, users)


def increment_message_stats():
    stats = load_json(STATS_FILE, {"total": 0, "by_date": {}})
    today = str(date.today())
    stats["total"] = stats.get("total", 0) + 1
    stats.setdefault("by_date", {})
    stats["by_date"][today] = stats["by_date"].get(today, 0) + 1
    # سيب بس آخر ٣٠ يوم في الإحصائيات التفصيلية عشان الملف يفضل صغير
    if len(stats["by_date"]) > 30:
        trimmed = dict(sorted(stats["by_date"].items())[-30:])
        stats["by_date"] = trimmed
    save_json(STATS_FILE, stats)
    return stats


def get_message_stats():
    stats = load_json(STATS_FILE, {"total": 0, "by_date": {}})
    today = str(date.today())
    return {
        "total": stats.get("total", 0),
        "today": stats.get("by_date", {}).get(today, 0),
    }


# =========================================================
# نظام الإعلانات
# =========================================================
def get_ads():
    return load_json(ADS_FILE, [])


def save_ads(ads):
    save_json(ADS_FILE, ads)


def get_ad_shown_count_today(ad_id):
    stats = load_json(ADS_STATS_FILE, {})
    today = str(date.today())
    return stats.get(today, {}).get(ad_id, 0)


def increment_ad_shown(ad_id):
    stats = load_json(ADS_STATS_FILE, {})
    today = str(date.today())
    stats.setdefault(today, {})
    stats[today][ad_id] = stats[today].get(ad_id, 0) + 1
    stats = {k: v for k, v in sorted(stats.items())[-14:]}
    save_json(ADS_STATS_FILE, stats)


def get_active_ad_for_category(category_id):
    today = date.today()
    for ad in get_ads():
        if not ad.get("enabled"):
            continue
        if ad.get("scope") == "category" and ad.get("category_id") != category_id:
            continue
        try:
            start = date.fromisoformat(ad["start_date"])
            end = date.fromisoformat(ad["end_date"]) if ad.get("end_date") else None
        except (KeyError, ValueError):
            continue
        if today < start:
            continue
        if end and today > end:
            continue
        if get_ad_shown_count_today(ad["id"]) >= ad.get("daily_limit", 0):
            continue
        return ad
    return None


def send_ad(to_number, ad):
    if ad.get("type") == "text":
        send_text_message(to_number, "📢 " + ad.get("text", ""))
    elif ad.get("type") == "image":
        image_url = SITE_BASE_URL + ad.get("image_path", "")
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "image",
            "image": {"link": image_url, "caption": ad.get("text", "") or None},
        }
        response = requests.post(GRAPH_API_URL, headers=headers, json=payload)
        print("Send ad image status:", response.status_code, response.text)
    increment_ad_shown(ad["id"])


def specialty_to_category_id(specialty_text):
    text = (specialty_text or "").strip()
    for cat in get_categories():
        if cat["title"] == text:
            return cat["id"]
    return "cat_other"


# =========================================================
# حدود الرسائل اليومية
# =========================================================
def all_known_phones():
    return {t["whatsapp"] for t in get_traders() if t.get("status") == "approved"}


def is_registered_trader(phone_number):
    return phone_number in all_known_phones()


def check_and_increment_limit(phone_number):
    counters = load_json(COUNTERS_FILE, {})
    today = str(date.today())
    day_counts = counters.get(today, {})

    limit = TRADER_DAILY_LIMIT if is_registered_trader(phone_number) else SHOPPER_DAILY_LIMIT
    current = day_counts.get(phone_number, 0)

    if current >= limit:
        return False

    day_counts[phone_number] = current + 1
    counters[today] = day_counts
    counters = {k: v for k, v in sorted(counters.items())[-2:]}
    save_json(COUNTERS_FILE, counters)
    return True


# =========================================================
# اختيار التجار للرد: أولوية + عشوائي + منع التكرار في نفس اليوم
# =========================================================
def get_category_traders(cat_id):
    return [
        t for t in get_traders()
        if t.get("category_id") == cat_id
        and t.get("status") == "approved"
        and not t.get("is_correction")
        and t.get("visibility") != "frozen"
    ]


def get_shown_ids(phone, cat_id):
    history = load_json(SHOWN_FILE, {})
    today = str(date.today())
    return history.get(today, {}).get(phone, {}).get(cat_id, [])


def save_shown_ids(phone, cat_id, trader_ids, reset=False):
    history = load_json(SHOWN_FILE, {})
    today = str(date.today())
    history.setdefault(today, {}).setdefault(phone, {})
    if reset:
        history[today][phone][cat_id] = trader_ids
    else:
        existing = history[today][phone].get(cat_id, [])
        history[today][phone][cat_id] = existing + trader_ids
    # سيب بس آخر يومين عشان الملف يفضل صغير
    history = {k: v for k, v in sorted(history.items())[-2:]}
    save_json(SHOWN_FILE, history)


def select_traders_for_reply(cat_id, phone):
    all_cat_traders = get_category_traders(cat_id)
    if not all_cat_traders:
        return [], 0

    shown = set(get_shown_ids(phone, cat_id))
    pool = [t for t in all_cat_traders if t["id"] not in shown]
    reset = False
    if not pool:
        pool = all_cat_traders
        reset = True

    priority_pool = [t for t in pool if t.get("visibility") == "priority"]
    normal_pool = [t for t in pool if t.get("visibility") != "priority"]

    chosen = []
    pri_take = min(PRIORITY_SLOTS, len(priority_pool))
    if pri_take:
        chosen += random.sample(priority_pool, pri_take)

    remaining = MAX_TRADERS_PER_REPLY - len(chosen)
    norm_take = min(remaining, len(normal_pool))
    if norm_take:
        chosen += random.sample(normal_pool, norm_take)

    remaining = MAX_TRADERS_PER_REPLY - len(chosen)
    if remaining > 0:
        leftover_priority = [t for t in priority_pool if t not in chosen]
        extra = min(remaining, len(leftover_priority))
        if extra:
            chosen += random.sample(leftover_priority, extra)

    save_shown_ids(phone, cat_id, [t["id"] for t in chosen], reset=reset)
    return chosen, len(all_cat_traders)


def format_traders_reply(cat_id, chosen, total):
    if not chosen:
        return EMPTY_CATEGORY_MESSAGE
    title = get_category_by_id(cat_id)["title"] if get_category_by_id(cat_id) else ""
    blocks = [
        f"🔹 *{title}*: {t['name']}\n📍 {t['location']}\n📞 {t['whatsapp']}"
        for t in chosen
    ]
    text = "\n\n".join(blocks)
    if total > len(chosen):
        text += "\n\n(في تجار تانيين متاحين — اسأل تاني عن نفس التخصص عشان تشوف أسماء تانية)"
    return text


def build_category_reply(cat_id, phone):
    chosen, total = select_traders_for_reply(cat_id, phone)
    return format_traders_reply(cat_id, chosen, total)


def build_keywords(trader):
    words = []
    details = trader.get("details", "")
    for part in details.replace("،", ",").split(","):
        part = part.strip()
        if part:
            words.append(part.lower())
    return words


def find_category_from_text(text):
    for cat in get_categories():
        for kw in cat.get("match", []):
            if kw in text:
                return cat["id"]
    for t in get_traders():
        if t.get("status") != "approved":
            continue
        for kw in build_keywords(t):
            if kw in text:
                return t.get("category_id")
    return None


def find_text_action(user_text):
    text = user_text.strip().lower()

    if text in ("قائمة", "list", "الخيارات"):
        return ("list", None)

    confirm_words = ["تأكيد", "تاكيد", "راجع بياناتي", "بياناتي"]
    if any(w in text for w in confirm_words):
        return ("confirm", None)

    join_words = ["انضمام", "انضم", "تسجيل", "أنا تاجر", "عايز انضم", "تصحيح"]
    if any(w in text for w in join_words):
        return ("join", None)

    greetings = ["السلام", "سلام", "اهلا", "أهلا", "هاي", "hi", "hello"]
    if any(g in text for g in greetings) and len(text) < 20:
        return ("list", None)

    cat_id = find_category_from_text(text)
    if cat_id:
        return ("category", cat_id)

    return ("none", None)


# =========================================================
# إرسال الرسائل عبر واتساب
# =========================================================
def normalize_phone(raw):
    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits.startswith("00"):
        digits = digits[2:]
    return digits


def send_text_message(to_number, message):
    to_number = normalize_phone(to_number)
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": message},
    }
    response = requests.post(GRAPH_API_URL, headers=headers, json=payload)
    print("Send text status:", response.status_code, response.text)
    return response


def send_template_message(to_number, template_name, language_code, body_params):
    """يبعت رسالة عبر قالب معتمد من Meta - الطريقة الوحيدة المسموحة
    لبدء محادثة مع رقم ما كلمناك خلال آخر ٢٤ ساعة."""
    to_number = normalize_phone(to_number)
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": p} for p in body_params],
                }
            ],
        },
    }
    response = requests.post(GRAPH_API_URL, headers=headers, json=payload)
    print("Send template status:", response.status_code, response.text)
    return response


def send_role_question(to_number):
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "🏗️ أهلاً بيك في واتساب السجانة! قبل ما نبدأ، عرفنا بنفسك "},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": ROLE_TRADER_ID, "title": "🔧 أنا تاجر"}},
                    {"type": "reply", "reply": {"id": ROLE_CUSTOMER_ID, "title": "🛒أنا زبون "}},
                ]
            },
        },
    }
    response = requests.post(GRAPH_API_URL, headers=headers, json=payload)
    print("Send role question status:", response.status_code, response.text)
    return response


def send_list_message(to_number):
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    rows = [{"id": c["id"], "title": c["title"]} for c in get_categories()][:9]
    rows.append({"id": JOIN_ROW_ID, "title": "🔧 أنا تاجر، عايز أنضم"})

    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "واتساب السجانة"},
            "body": {"text": WELCOME_TEXT},
            "footer": {"text": "اختار من القائمة تحت"},
            "action": {
                "button": "عرض التخصصات",
                "sections": [{"title": "التخصصات المتاحة", "rows": rows}],
            },
        },
    }
    response = requests.post(GRAPH_API_URL, headers=headers, json=payload)
    print("Send list status:", response.status_code, response.text)
    return response


def trader_join_reply(phone_number):
    for t in get_traders():
        if t.get("whatsapp") == phone_number:
            return EXISTING_TRADER_REPLY_TEXT
    return JOIN_REPLY_TEXT


def maybe_send_ad(to_number, category_id):
    ad = get_active_ad_for_category(category_id)
    if ad:
        try:
            send_ad(to_number, ad)
        except Exception as e:
            print("Ad send failed (non-fatal):", e)


def notify_owner_new_trader(trader):
    if not OWNER_WHATSAPP_NUMBER:
        print("OWNER_WHATSAPP_NUMBER not set, skipping owner notification.")
        return
    cat_title = {c["id"]: c["title"] for c in get_categories()}
    text = (
        "🔔 تسجيل تاجر جديد في واتساب السجانة\n\n"
        f"الاسم: {trader.get('name')}\n"
        f"التخصص: {cat_title.get(trader.get('category_id'), '')}\n"
        f"الرقم: {trader.get('whatsapp')}\n"
        f"الموقع: {trader.get('location')}\n\n"
        f"راجعه من هنا:\n{SITE_BASE_URL}/admin?key={ADMIN_KEY}"
    )
    try:
        send_text_message(OWNER_WHATSAPP_NUMBER, text)
    except Exception as e:
        print("Owner notification failed (non-fatal):", e)


def log_unmatched_query(phone_number, user_text):
    entries = load_json(UNMATCHED_FILE, [])
    entries.append({
        "date": str(date.today()),
        "phone": phone_number,
        "text": user_text[:200],
    })
    # سيب بس آخر ١٠٠ طلب عشان الملف يفضل صغير
    entries = entries[-100:]
    save_json(UNMATCHED_FILE, entries)


# =========================================================
# استقبال الرسائل (Webhook)
# =========================================================
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = req

@app.route('/run-backup')
def run_backup():
    key = request.args.get('key', '')
    admin_key = os.environ.get('SAJJANA_ADMIN_KEY', '')
    if not admin_key or key != admin_key:
        return jsonify({'status': 'error', 'message': 'unauthorized'}), 403
    try:
        run_backup_job()
        return jsonify({'status': 'ok', 'message': 'backup finished'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
