import os
import json
import random
import uuid
from datetime import date

import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

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

REGISTER_URL = "https://mohbab.pythonanywhere.com/register"

TRADER_DAILY_LIMIT = 15
SHOPPER_DAILY_LIMIT = 15
MAX_TRADERS_PER_REPLY = 4
PRIORITY_SLOTS = 2

JOIN_ROW_ID = "cat_join_trader"

WELCOME_TEXT = "🏗️ أهلاً بيكم في واتساب السجانة! اختار التخصص اللي بتدوّر عليهو من القايمة تحت:"
NOT_FOUND_MESSAGE = (
    "ما لقيناهو دا للأسف 🤔\n"
    "اكتب اسم التخصص، أو اكتب \"قائمة\" عشان تشوف كل الخيارات."
)
EMPTY_CATEGORY_MESSAGE = "للأسف لسه ما عندنا تجار مسجلين في التخصص دا، جرّب تاني قريب 🙏"
LIMIT_REACHED_MESSAGE = (
    "وصلت لأقصى عدد رسائل مسموح بيهو النهاردة 🙏\n"
    "جرّب تاني بكرة، أو لو الموضوع مستعجل كلّمنا مباشرة."
)
JOIN_REPLY_TEXT = (
    f"يسعدنا انضمامك لواتساب السجانة! 🎉\n"
    f"سجّل بياناتك من الرابط دا (بياخد دقيقة بس):\n{REGISTER_URL}"
)
EXISTING_TRADER_REPLY_TEXT = (
    "أهلين بيك تاني! 👋 لاحظنا إن رقمك مسجل عندنا خلاص.\n\n"
    f"تأكد من بياناتك أو صحّحها من هنا:\n{SITE_BASE_URL}/check\n\n"
    f"أو لو عايز تسجل محل جديد:\n{REGISTER_URL}"
)
ASK_PRODUCT_TEXT = "تمام 👍 اكتب اسم الصنف الما داير، أو ابعت \"قائمة\" عشان تشوف كل التخصصات."
TRADER_THANK_YOU_TEXT = (
    "شكراً ليك على تسجيلك في واتساب السجانة! 🎉\n"
    "طلبك دلوقتي قيد المراجعة، وح نبلّغك بالواتساب فور ما يتم اعتماده.\n\n"
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
    لبدء محادثة مع رقم ما كلمناش خلال آخر ٢٤ ساعة."""
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
            "body": {"text": "🏗️ أهلاً بيك في واتساب السجانة! قبل ما نبدأ، منو حضرتك؟"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": ROLE_TRADER_ID, "title": "🔧 أنا تاجر"}},
                    {"type": "reply", "reply": {"id": ROLE_CUSTOMER_ID, "title": "🛒 أنا عميل"}},
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
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403


@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json()
    print("Incoming:", data)

    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "messages" not in value:
            return jsonify({"status": "ok"}), 200

        message = value["messages"][0]
        from_number = message["from"]
        msg_type = message.get("type")

        increment_message_stats()

        if not check_and_increment_limit(from_number):
            send_text_message(from_number, LIMIT_REACHED_MESSAGE)
            return jsonify({"status": "ok"}), 200

        # أول رسالة من رقم جديد تماماً: نسأله تاجر ولا عميل قبل أي حاجة تانية
        if is_new_user(from_number):
            register_new_user(from_number)
            send_role_question(from_number)
            return jsonify({"status": "ok"}), 200

        if msg_type == "text":
            user_text = message["text"]["body"]
            kind, value_ = find_text_action(user_text)
            if kind == "list":
                send_list_message(from_number)
            elif kind == "join":
                send_text_message(from_number, trader_join_reply(from_number))
            elif kind == "confirm":
                trader = next((t for t in get_traders() if t.get("whatsapp") == from_number), None)
                if trader:
                    send_text_message(from_number, build_check_message(trader))
                else:
                    send_text_message(from_number, JOIN_REPLY_TEXT)
            elif kind == "category":
                reply = build_category_reply(value_, from_number)
                send_text_message(from_number, reply)
                maybe_send_ad(from_number, value_)
            else:
                send_text_message(from_number, NOT_FOUND_MESSAGE)
                log_unmatched_query(from_number, user_text)

        elif msg_type == "interactive":
            interactive = message.get("interactive", {})
            selected_id = None

            if interactive.get("type") == "list_reply":
                selected_id = interactive["list_reply"]["id"]
            elif interactive.get("type") == "button_reply":
                selected_id = interactive["button_reply"]["id"]

            if selected_id == ROLE_TRADER_ID:
                set_user_role(from_number, "trader")
                send_text_message(from_number, trader_join_reply(from_number))
            elif selected_id == ROLE_CUSTOMER_ID:
                set_user_role(from_number, "customer")
                send_text_message(from_number, ASK_PRODUCT_TEXT)
            elif selected_id == JOIN_ROW_ID:
                send_text_message(from_number, trader_join_reply(from_number))
            elif selected_id and get_category_by_id(selected_id):
                reply = build_category_reply(selected_id, from_number)
                send_text_message(from_number, reply)
                maybe_send_ad(from_number, selected_id)
            elif selected_id:
                send_text_message(from_number, NOT_FOUND_MESSAGE)

    except (KeyError, IndexError) as e:
        print("No message content to process:", e)

    return jsonify({"status": "ok"}), 200


# =========================================================
# صفحات الموقع
# =========================================================
@app.route("/", methods=["GET"])
def home():
    with open(os.path.join(BASE_DIR, "templates", "index.html"), encoding="utf-8") as f:
        return f.read()


@app.route("/register", methods=["GET"])
def register_page():
    with open(os.path.join(BASE_DIR, "templates", "register.html"), encoding="utf-8") as f:
        html = f.read()
    options = "\n".join(
        f'<option value="{c["title"]}">{c["title"]}</option>' for c in get_categories()
    )
    html = html.replace("<!--CATEGORY_OPTIONS-->", options)
    return html


@app.route("/check", methods=["GET"])
def check_page():
    with open(os.path.join(BASE_DIR, "templates", "check.html"), encoding="utf-8") as f:
        return f.read()


def normalize_phone(raw):
    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits.startswith("00"):
        digits = digits[2:]
    return digits


ABOUT_APP_INTRO = (
    "🏗️ *واتساب السجانة*\n"
    "خدمة مجانية بتربط تجار سوق السجانة بالخرطوم مباشرة بالزباين عبر واتساب — "
    "الزول بيكتب اسم الصنف الداير يشتريه، وبنوصله بيك على طول من غير ما يلف السوق كله.\n\n"
    "فايدتك من الانضمام: زباين جداد بيوصلوك من غير أي مجهود أو تكلفة منك.\n"
)

# اسم القالب المعتمد من Meta - لازم يتسجل بنفس الاسم بالظبط في WhatsApp Manager
CONFIRM_DATA_TEMPLATE_NAME = "confirm_trader_data"
CONFIRM_DATA_TEMPLATE_LANG = "ar"


def send_confirmation_via_template(trader):
    """يبعت رسالة تأكيد بيانات عبر قالب معتمد - بتشتغل حتى مع أرقام
    ما كلمناش خلال آخر ٢٤ ساعة (عكس الرسائل النصية العادية)."""
    from urllib.parse import quote

    cat_title = {c["id"]: c["title"] for c in get_categories()}
    status = trader.get("status", "pending")
    name = trader.get("name", "") or "تاجرنا العزيز"
    category = cat_title.get(trader.get("category_id"), "") or "-"
    location = trader.get("location", "") or "-"
    details = trader.get("details", "") or "-"
    whatsapp = trader.get("whatsapp", "")

    if status == "approved":
        correction_link = (
            f"{REGISTER_URL}?correction=1"
            f"&name={quote(name)}&whatsapp={quote(whatsapp)}"
            f"&specialty={quote(category)}&details={quote(trader.get('details',''))}"
            f"&location={quote(location)}"
        )
        params = [name, category, location, details, correction_link]
    elif status == "pending":
        params = [name, "قيد المراجعة", "-", "طلبك لسه ما اتوافقش عليه", REGISTER_URL]
    else:
        params = [name, "-", "-", "الطلب ما اتقبلش سابقاً، سجل من جديد", REGISTER_URL]

    return send_template_message(
        trader.get("whatsapp", ""),
        CONFIRM_DATA_TEMPLATE_NAME,
        CONFIRM_DATA_TEMPLATE_LANG,
        params,
    )


def build_check_message(trader, include_intro=True):
    from urllib.parse import quote

    cat_title = {c["id"]: c["title"] for c in get_categories()}
    status = trader.get("status", "pending")
    name = trader.get("name", "")
    category = cat_title.get(trader.get("category_id"), "")
    location = trader.get("location", "")
    details = trader.get("details", "") or "-"
    whatsapp = trader.get("whatsapp", "")

    intro = ABOUT_APP_INTRO if include_intro else ""

    if status == "approved":
        correction_link = (
            f"{REGISTER_URL}?correction=1"
            f"&name={quote(name)}&whatsapp={quote(whatsapp)}"
            f"&specialty={quote(category)}&details={quote(trader.get('details',''))}"
            f"&location={quote(location)}"
        )
        return (
            f"{intro}\n"
            "بنراجع بيانات التجار المسجلين معانا — دي بياناتك الحالية عندنا:\n\n"
            f"الاسم: {name}\n"
            f"التخصص: {category}\n"
            f"الموقع: {location}\n"
            f"التفاصيل: {details}\n\n"
            f"البيانات غلط أو ناقصة؟ صحّحها من هنا:\n{correction_link}"
        )
    elif status == "pending":
        return (
            f"{intro}\n"
            f"طلب انضمامك باسم \"{name}\" لسه قيد المراجعة.\n"
            "هنبلغك على واتساب فور ما يتم الاعتماد."
        )
    else:
        return (
            f"{intro}\n"
            f"طلب باسم \"{name}\" ({whatsapp}) ما اتقبلش سابقاً.\n"
            f"تقدر تسجل من جديد من هنا:\n{REGISTER_URL}"
        )


CHECK_GENERIC_RESPONSE = (
    "لو الرقم أو الاسم دا مسجل عندنا، وصلته رسالة واتساب دلوقتي فيها كل التفاصيل. "
    "تأكد من فتح واتساب على نفس الرقم اللي كتبته."
)


@app.route("/api/check-trader", methods=["GET"])
def api_check_trader():
    phone_raw = request.args.get("whatsapp", "").strip()
    name_query = request.args.get("name", "").strip().lower()

    if not phone_raw and not name_query:
        return jsonify({"message": CHECK_GENERIC_RESPONSE})

    traders = get_traders()
    matches = []

    if phone_raw:
        phone_norm = normalize_phone(phone_raw)
        suffix = phone_norm[-9:] if len(phone_norm) >= 9 else phone_norm
        for t in traders:
            t_phone = normalize_phone(t.get("whatsapp", ""))
            if t_phone == phone_norm or (suffix and t_phone.endswith(suffix)):
                matches.append(t)
    elif name_query:
        for t in traders:
            if name_query in t.get("name", "").lower():
                matches.append(t)

    # نرسل التفاصيل على واتساب بتاع كل تسجيل مطابق بس - أبداً ما بنعرضها هنا
    # عشان محدش يقدر يشوف بيانات شخص تاني من غير ما يملك رقمه فعلاً
    for t in matches:
        try:
            send_confirmation_via_template(t)
        except Exception as e:
            print("Check-trader message send failed (non-fatal):", e)

    # نفس الرد بالظبط في كل الحالات (موجود/مش موجود) عشان محدش يقدر
    # يكتشف مين مسجل عندنا ومين لأ من خلال فرق في الرد
    return jsonify({"message": CHECK_GENERIC_RESPONSE})


@app.route("/submit-trader", methods=["POST"])
def submit_trader():
    try:
        payload = request.get_json()
        required = ["name", "whatsapp", "specialty", "details", "location"]
        if not payload or any(not payload.get(field) for field in required):
            return jsonify({"status": "error", "message": "بيانات ناقصة"}), 400

        traders = get_traders()
        new_trader = {
            "id": "t" + uuid.uuid4().hex[:8],
            "name": payload["name"],
            "whatsapp": payload["whatsapp"],
            "category_id": specialty_to_category_id(payload["specialty"]),
            "location": payload["location"],
            "details": payload.get("details", ""),
            "notes": payload.get("notes", ""),
            "status": "pending",
            "visibility": "normal",
            "submitted_at": str(date.today()),
        }
        traders.append(new_trader)
        save_traders(traders)

        try:
            send_text_message(new_trader["whatsapp"], TRADER_THANK_YOU_TEXT)
        except Exception as send_err:
            print("Thank-you message failed (non-fatal):", send_err)

        notify_owner_new_trader(new_trader)

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print("Submit error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


# =========================================================
# صفحة الإدارة
# mohbab.pythonanywhere.com/admin?key=...
# =========================================================
ADMIN_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>إدارة واتساب السجانة</title>
<link rel="icon" type="image/png" href="/static/favicon-32.png">
<style>
  body{{font-family:Arial,sans-serif; background:#EAE4D9; color:#24272B; padding:24px;}}
  h1{{font-size:1.4rem;}} h2{{font-size:1.1rem; margin-top:36px;}}
  table{{width:100%; border-collapse:collapse; background:#F5F1E8; margin-top:10px;}}
  th,td{{border:1px solid #ccc; padding:8px; text-align:right; font-size:0.85rem;}}
  th{{background:#24272B; color:#fff;}}
  form.inline{{display:inline;}}
  button{{padding:5px 10px; border:none; border-radius:4px; cursor:pointer; font-size:0.8rem; margin:2px;}}
  .approve{{background:#3f7a4d; color:#fff;}}
  .reject{{background:#a6502f; color:#fff;}}
  .priority{{background:#c9932f; color:#fff;}}
  .normal{{background:#5c6b6e; color:#fff;}}
  .frozen{{background:#8a8a8a; color:#fff;}}
  .delete{{background:#7e3a20; color:#fff;}}
  .add-form{{background:#F5F1E8; padding:16px; margin-top:10px; max-width:400px;}}
  .add-form input{{width:100%; padding:8px; margin-bottom:10px;}}
  .empty{{color:#666;}}
  .btn-link{{display:inline-block; padding:5px 10px; border-radius:4px; font-size:0.8rem; margin:2px;
    background:#24272B; color:#fff; text-decoration:none;}}
  .btn-link:hover{{background:#A6502F;}}
  .cat-chip{{display:inline-flex; align-items:center; gap:6px; background:#F5F1E8; border:1px solid #ccc;
    border-radius:100px; padding:4px 6px 4px 12px; margin:3px; font-size:0.85rem;}}
  .edit-form{{background:#F5F1E8; padding:24px; max-width:480px; border-radius:6px;}}
  .edit-form label{{display:block; font-weight:bold; margin:14px 0 4px; font-size:0.85rem;}}
  .edit-form input, .edit-form select{{width:100%; padding:8px; font-size:0.95rem;}}
  .save-btn{{background:#3f7a4d; color:#fff; margin-top:18px; padding:10px 18px;}}
  .badge{{padding:2px 8px; border-radius:100px; font-size:0.75rem;}}
  .b-priority{{background:#f1dfa8;}} .b-normal{{background:#dfe3e2;}} .b-frozen{{background:#ddd;}}
  .stats-bar{{display:flex; gap:16px; margin:14px 0 24px; flex-wrap:wrap;}}
  .stat-box{{background:#24272B; color:#fff; padding:12px 20px; border-radius:6px; font-size:0.9rem;}}
  .stat-box b{{display:block; font-size:1.4rem; color:#e8b98a;}}
  .search-box{{margin:14px 0; display:flex; gap:8px; max-width:420px;}}
  .search-box input{{flex:1; padding:10px; border:1px solid #ccc; border-radius:4px; font-size:0.95rem;}}
  .search-box button{{background:#24272B; color:#fff; padding:10px 16px;}}
  .bulk-bar{{margin:10px 0; padding:8px; background:#dfe3e2; border-radius:4px;}}
  .tabs-nav{{display:flex; gap:4px; margin:20px 0 0; border-bottom:2px solid #24272B; flex-wrap:wrap;}}
  .tab-btn{{padding:10px 18px; background:#dfe3e2; border:none; border-radius:6px 6px 0 0;
    cursor:pointer; font-size:0.9rem; font-weight:bold; color:#454B50;}}
  .tab-btn.active{{background:#24272B; color:#fff;}}
  .tab-panel{{display:none; padding-top:20px;}}
  .tab-panel.active{{display:block;}}
</style>
<script>
function toggleAll(cls, check){{
  document.querySelectorAll('.' + cls).forEach(function(cb){{ cb.checked = check; }});
}}
function submitBulk(cls, hiddenId, action){{
  var ids = [];
  document.querySelectorAll('.' + cls + ':checked').forEach(function(cb){{ ids.push(cb.value); }});
  if(ids.length === 0){{ alert('اختار عنصر واحد على الأقل'); return false; }}
  document.getElementById(hiddenId).value = ids.join(',');
  var form = document.getElementById(hiddenId).closest('form');
  var actionInput = document.createElement('input');
  actionInput.type = 'hidden'; actionInput.name = 'bulk_action'; actionInput.value = action;
  form.appendChild(actionInput);
  return true;
}}
function showTab(name){{
  document.querySelectorAll('.tab-panel').forEach(function(p){{ p.classList.remove('active'); }});
  document.querySelectorAll('.tab-btn').forEach(function(b){{ b.classList.remove('active'); }});
  document.getElementById('tab-' + name).classList.add('active');
  document.getElementById('btn-' + name).classList.add('active');
  window.location.hash = name;
}}
window.addEventListener('DOMContentLoaded', function(){{
  var initial = window.location.hash ? window.location.hash.substring(1) : 'pending';
  if(!document.getElementById('tab-' + initial)){{ initial = 'pending'; }}
  showTab(initial);
}});
</script>
</head>
<body>
<div class="logo-header" style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
  <img src="/static/logo.png" alt="شعار" style="height:52px;width:52px;object-fit:contain;">
  <h1 style="margin:0;">لوحة إدارة واتساب السجانة</h1>
</div>

<div class="stats-bar">
  <div class="stat-box">رسائل اليوم<b>{msgs_today}</b></div>
  <div class="stat-box">إجمالي الرسائل<b>{msgs_total}</b></div>
</div>

<div class="tabs-nav">
  <button type="button" class="tab-btn" id="btn-pending" onclick="showTab('pending')">قيد المراجعة ({total_pending_count})</button>
  <button type="button" class="tab-btn" id="btn-traders" onclick="showTab('traders')">التجار المعتمدين ({total_approved_count})</button>
  <button type="button" class="tab-btn" id="btn-stats" onclick="showTab('stats')">الإحصائيات</button>
  <button type="button" class="tab-btn" id="btn-categories" onclick="showTab('categories')">التخصصات</button>
  <button type="button" class="tab-btn" id="btn-ads" onclick="showTab('ads')">الإعلانات</button>
</div>

<form class="search-box" method="GET" action="/admin">
  <input type="hidden" name="key" value="{key}">
  <input type="text" name="q" placeholder="ابحث بالاسم، الرقم، التخصص، أو التفاصيل" value="{search_query}">
  <button type="submit">بحث</button>
  {clear_search_link}
</form>

<div class="tab-panel" id="tab-pending">
  <h2>تسجيلات قيد المراجعة (معروض {pending_count} من {total_pending_count})</h2>
  {pending_table}
</div>

<div class="tab-panel" id="tab-traders">
  <h2>كل التجار المعتمدين (معروض {approved_count} من {total_approved_count})</h2>
  {approved_table}
</div>

<div class="tab-panel" id="tab-stats">
  <h2>إحصائيات التجار حسب التخصص</h2>
  {category_stats_table}

  <h2>طلبات ما لقيناش ليها رد (آخر ٣٠)</h2>
  <p style="color:#454B50;font-size:0.85rem;">دي منتجات الزباين بتسأل عنها ومحتاجة تجار جدد أو تخصصات جديدة.</p>
  {unmatched_table}

  <form method="GET" action="/admin/trigger-report" target="_blank" style="margin-top:16px;">
    <input type="hidden" name="key" value="{key}">
    <button class="approve" type="submit">ابعت تقرير أسبوعي دلوقتي</button>
  </form>
  <p style="color:#454B50;font-size:0.8rem;margin-top:6px;">
    عشان يترسل تلقائياً كل أسبوع، اربط الرابط ده بخدمة مجانية زي cron-job.org:<br>
    <code>{site_base}/admin/trigger-report?key={key}</code>
  </p>
</div>

<div class="tab-panel" id="tab-categories">
  <h2>إضافة تخصص جديد</h2>
  <form class="add-form" method="POST" action="/admin/add-category">
    <input type="hidden" name="key" value="{key}">
    <input type="text" name="title" placeholder="اسم التخصص الجديد" required>
    <button class="approve" type="submit">إضافة التخصص</button>
  </form>

  <h2>التخصصات الحالية</h2>
  <p>{categories_list}</p>
</div>

<div class="tab-panel" id="tab-ads">
<h2>الإعلانات</h2>
{ads_table}

<h3>إضافة إعلان جديد</h3>
<form class="add-form" method="POST" action="/admin/add-ad" enctype="multipart/form-data" style="max-width:480px;">
  <input type="hidden" name="key" value="{key}">

  <label style="display:block;margin:10px 0 4px;font-size:0.85rem;font-weight:bold;">نطاق الظهور</label>
  <select name="scope" style="width:100%;padding:8px;margin-bottom:10px;">
    <option value="category">مع تخصص محدد بس</option>
    <option value="global">مع كل رد (عام)</option>
  </select>

  <label style="display:block;margin:10px 0 4px;font-size:0.85rem;font-weight:bold;">التخصص (لو الإعلان مخصص لتخصص)</label>
  <select name="category_id" style="width:100%;padding:8px;margin-bottom:10px;">
    {category_select_options}
  </select>

  <label style="display:block;margin:10px 0 4px;font-size:0.85rem;font-weight:bold;">نوع الإعلان</label>
  <select name="ad_type" id="adTypeSelect" onchange="toggleAdFields()" style="width:100%;padding:8px;margin-bottom:10px;">
    <option value="text">نص قصير (٧٠ حرف)</option>
    <option value="image">صورة (بوستر)</option>
  </select>

  <div id="adTextField">
    <input type="text" name="text" maxlength="300" placeholder="نص الإعلان (حتى 300 حرف)">
  </div>
  <div id="adImageField" style="display:none;">
    <input type="file" name="image" accept="image/*">
    <input type="text" name="text" maxlength="300" placeholder="تعليق مختصر تحت الصورة (اختياري)">
  </div>

  <label style="display:block;margin:10px 0 4px;font-size:0.85rem;font-weight:bold;">أقصى عدد ظهور يومياً</label>
  <input type="number" name="daily_limit" value="20" min="1" style="margin-bottom:10px;">

  <label style="display:block;margin:10px 0 4px;font-size:0.85rem;font-weight:bold;">مدة الحملة (بالأيام)</label>
  <input type="number" name="duration_days" value="7" min="1" style="margin-bottom:14px;">

  <button class="approve" type="submit">إضافة الإعلان</button>
</form>
</div>

<script>
function toggleAdFields(){{
  var type = document.getElementById('adTypeSelect').value;
  document.getElementById('adTextField').style.display = (type === 'text') ? 'block' : 'none';
  document.getElementById('adImageField').style.display = (type === 'image') ? 'block' : 'none';
}}
</script>

</body>
</html>
"""


def visibility_badge(v):
    label = {"priority": "أولوية", "normal": "عادي", "frozen": "مجمّد"}.get(v, v)
    cls = {"priority": "b-priority", "normal": "b-normal", "frozen": "b-frozen"}.get(v, "")
    return f'<span class="badge {cls}">{label}</span>'


@app.route("/admin", methods=["GET"])
def admin_page():
    key = request.args.get("key", "")
    if key != ADMIN_KEY:
        return "غير مصرح — مفتاح الدخول غلط", 403

    search_query = request.args.get("q", "").strip().lower()

    traders = get_traders()
    categories = get_categories()
    cat_title = {c["id"]: c["title"] for c in categories}

    def matches_search(t):
        if not search_query:
            return True
        haystack = " ".join([
            t.get("name", ""), t.get("whatsapp", ""),
            cat_title.get(t.get("category_id"), ""), t.get("details", ""),
        ]).lower()
        return search_query in haystack

    pending = [t for t in traders if t.get("status") == "pending" and matches_search(t)]
    approved = [t for t in traders if t.get("status") == "approved" and matches_search(t)]

    # العدادات فوق التبويبات لازم توضح العدد الكلي الحقيقي دايماً،
    # مش عدد نتائج البحث - عشان محدش يفتكر إن البيانات اتمسحت لو البحث رجّع صفر نتيجة
    total_pending_count = sum(1 for t in traders if t.get("status") == "pending")
    total_approved_count = sum(1 for t in traders if t.get("status") == "approved")

    if not pending:
        pending_table = '<p class="empty">مفيش تسجيلات جديدة قيد المراجعة.</p>'
    else:
        rows = ""
        for t in pending:
            rows += f"""
            <tr>
              <td><input type="checkbox" class="row-check pending-check" value="{t['id']}"></td>
              <td>{t.get('name','')}</td><td>{t.get('whatsapp','')}</td>
              <td>{t.get('category_id','')} ({cat_title.get(t.get('category_id'),'')})</td>
              <td>{t.get('details','')}</td><td>{t.get('location','')}</td>
              <td>
                <a class="btn-link" href="/admin/edit-trader?key={key}&id={t['id']}">تعديل</a>
                <form class="inline" method="POST" action="/admin/trader-action">
                  <input type="hidden" name="key" value="{key}">
                  <input type="hidden" name="id" value="{t['id']}">
                  <input type="hidden" name="action" value="approve">
                  <button class="approve" type="submit">موافقة</button>
                </form>
                <form class="inline" method="POST" action="/admin/trader-action">
                  <input type="hidden" name="key" value="{key}">
                  <input type="hidden" name="id" value="{t['id']}">
                  <input type="hidden" name="action" value="reject">
                  <button class="reject" type="submit">رفض</button>
                </form>
              </td>
            </tr>"""
        pending_table = f"""
        <div class="bulk-bar">
          <button type="button" class="btn-link" onclick="toggleAll('pending-check', true)">تحديد الكل</button>
          <button type="button" class="btn-link" onclick="toggleAll('pending-check', false)">إلغاء التحديد</button>
          <form class="inline" method="POST" action="/admin/bulk-action" id="bulkPendingForm">
            <input type="hidden" name="key" value="{key}">
            <input type="hidden" name="ids" id="bulkPendingIds">
            <button type="submit" class="approve" onclick="return submitBulk('pending-check','bulkPendingIds','approve')">موافقة على المحدد</button>
            <button type="submit" class="reject" onclick="return submitBulk('pending-check','bulkPendingIds','reject')">رفض المحدد</button>
          </form>
        </div>
        <table><tr>
          <th></th><th>الاسم</th><th>واتساب</th><th>التخصص</th><th>التفاصيل</th><th>الموقع</th><th>إجراء</th>
        </tr>{rows}</table>"""

    if not approved:
        approved_table = '<p class="empty">مفيش تجار معتمدين لسه.</p>'
    else:
        rows = ""
        for t in approved:
            vis = t.get("visibility", "normal")
            rows += f"""
            <tr>
              <td><input type="checkbox" class="row-check approved-check" value="{t['id']}"></td>
              <td>{t.get('name','')}</td><td>{t.get('whatsapp','')}</td>
              <td>{cat_title.get(t.get('category_id'),'')}</td>
              <td>{visibility_badge(vis)}</td>
              <td>
                <a class="btn-link" href="/admin/edit-trader?key={key}&id={t['id']}">تعديل</a>
                <form class="inline" method="POST" action="/admin/set-visibility">
                  <input type="hidden" name="key" value="{key}">
                  <input type="hidden" name="id" value="{t['id']}">
                  <input type="hidden" name="visibility" value="priority">
                  <button class="priority" type="submit">أولوية</button>
                </form>
                <form class="inline" method="POST" action="/admin/set-visibility">
                  <input type="hidden" name="key" value="{key}">
                  <input type="hidden" name="id" value="{t['id']}">
                  <input type="hidden" name="visibility" value="normal">
                  <button class="normal" type="submit">عادي</button>
                </form>
                <form class="inline" method="POST" action="/admin/set-visibility">
                  <input type="hidden" name="key" value="{key}">
                  <input type="hidden" name="id" value="{t['id']}">
                  <input type="hidden" name="visibility" value="frozen">
                  <button class="frozen" type="submit">تجميد</button>
                </form>
                <form class="inline" method="POST" action="/admin/send-confirmation">
                  <input type="hidden" name="key" value="{key}">
                  <input type="hidden" name="id" value="{t['id']}">
                  <button class="approve" type="submit">ابعت تأكيد بيانات</button>
                </form>
                <form class="inline" method="POST" action="/admin/trader-action"
                      onsubmit="return confirm('متأكد من الحذف النهائي؟');">
                  <input type="hidden" name="key" value="{key}">
                  <input type="hidden" name="id" value="{t['id']}">
                  <input type="hidden" name="action" value="delete">
                  <button class="delete" type="submit">حذف نهائي</button>
                </form>
              </td>
            </tr>"""
        approved_table = f"""
        <div class="bulk-bar">
          <button type="button" class="btn-link" onclick="toggleAll('approved-check', true)">تحديد الكل</button>
          <button type="button" class="btn-link" onclick="toggleAll('approved-check', false)">إلغاء التحديد</button>
          <form class="inline" method="POST" action="/admin/bulk-action" id="bulkApprovedForm">
            <input type="hidden" name="key" value="{key}">
            <input type="hidden" name="ids" id="bulkApprovedIds">
            <button type="submit" class="approve" onclick="return submitBulk('approved-check','bulkApprovedIds','confirm')">ابعت تأكيد بيانات للمحدد</button>
            <button type="submit" class="priority" onclick="return submitBulk('approved-check','bulkApprovedIds','priority')">أولوية للمحدد</button>
            <button type="submit" class="normal" onclick="return submitBulk('approved-check','bulkApprovedIds','normal')">عادي للمحدد</button>
            <button type="submit" class="frozen" onclick="return submitBulk('approved-check','bulkApprovedIds','frozen')">تجميد المحدد</button>
            <button type="submit" class="delete" onclick="return confirm('متأكد من حذف كل العناصر المحددة؟') && submitBulk('approved-check','bulkApprovedIds','delete')">حذف المحدد</button>
          </form>
        </div>
        <table><tr>
          <th></th><th>الاسم</th><th>واتساب</th><th>التخصص</th><th>الحالة</th><th>إجراء</th>
        </tr>{rows}</table>"""

    categories_list = "".join(
        f'<span class="cat-chip">{c["title"]} '
        f'<a class="btn-link" href="/admin/edit-category?key={key}&id={c["id"]}">تعديل</a></span>'
        for c in categories
    )

    # جدول إحصائيات التجار حسب التخصص
    approved_all = [t for t in traders if t.get("status") == "approved"]
    stats_rows = ""
    for c in categories:
        count = sum(1 for t in approved_all if t.get("category_id") == c["id"])
        stats_rows += f"<tr><td>{c['title']}</td><td>{count}</td></tr>"
    category_stats_table = f"""<table><tr><th>التخصص</th><th>عدد التجار</th></tr>{stats_rows}</table>"""

    stats = get_message_stats()

    category_select_options = "".join(
        f'<option value="{c["id"]}">{c["title"]}</option>' for c in categories
    )

    unmatched = load_json(UNMATCHED_FILE, [])
    if not unmatched:
        unmatched_table = '<p class="empty">مفيش طلبات غير ملباة مسجلة لسه.</p>'
    else:
        rows = "".join(
            f"<tr><td>{u['date']}</td><td>{u['text']}</td></tr>"
            for u in reversed(unmatched[-30:])
        )
        unmatched_table = f"<table><tr><th>التاريخ</th><th>النص</th></tr>{rows}</table>"

    ads = get_ads()
    if not ads:
        ads_table = '<p class="empty">مفيش إعلانات مضافة لسه.</p>'
    else:
        rows = ""
        for ad in ads:
            scope_label = "عام (كل التخصصات)" if ad.get("scope") == "global" else cat_title.get(ad.get("category_id"), "-")
            preview = ad.get("text", "") if ad.get("type") == "text" else f'<img src="{ad.get("image_path","")}" style="max-height:50px;">'
            status_label = "مفعّل ✅" if ad.get("enabled") else "متوقف ⏸"
            shown_today = get_ad_shown_count_today(ad["id"])
            rows += f"""
            <tr>
              <td>{scope_label}</td>
              <td>{preview}</td>
              <td>{shown_today} / {ad.get('daily_limit','-')}</td>
              <td>{ad.get('start_date','')} → {ad.get('end_date','')}</td>
              <td>{status_label}</td>
              <td>
                <form class="inline" method="POST" action="/admin/toggle-ad">
                  <input type="hidden" name="key" value="{key}">
                  <input type="hidden" name="id" value="{ad['id']}">
                  <button class="normal" type="submit">تفعيل/إيقاف</button>
                </form>
                <form class="inline" method="POST" action="/admin/delete-ad"
                      onsubmit="return confirm('متأكد من حذف الإعلان؟');">
                  <input type="hidden" name="key" value="{key}">
                  <input type="hidden" name="id" value="{ad['id']}">
                  <button class="delete" type="submit">حذف</button>
                </form>
              </td>
            </tr>"""
        ads_table = f"""<table><tr>
          <th>النطاق</th><th>المحتوى</th><th>الظهور اليوم</th><th>المدة</th><th>الحالة</th><th>إجراء</th>
        </tr>{rows}</table>"""

    return ADMIN_PAGE.format(
        pending_count=len(pending),
        pending_table=pending_table,
        approved_count=len(approved),
        approved_table=approved_table,
        total_pending_count=total_pending_count,
        total_approved_count=total_approved_count,
        key=key,
        categories_list=categories_list,
        msgs_today=stats["today"],
        msgs_total=stats["total"],
        search_query=search_query,
        clear_search_link=(f'<a class="btn-link" href="/admin?key={key}">إلغاء البحث وعرض الكل</a>' if search_query else ''),
        category_stats_table=category_stats_table,
        ads_table=ads_table,
        category_select_options=category_select_options,
        unmatched_table=unmatched_table,
        site_base=SITE_BASE_URL,
    )


@app.route("/admin/trader-action", methods=["POST"])
def admin_trader_action():
    key = request.form.get("key", "")
    if key != ADMIN_KEY:
        return "غير مصرح", 403

    trader_id = request.form.get("id")
    action = request.form.get("action")

    traders = get_traders()
    if action == "delete":
        traders = [t for t in traders if t["id"] != trader_id]
    else:
        for t in traders:
            if t["id"] == trader_id:
                if action == "approve":
                    t["status"] = "approved"
                elif action == "reject":
                    t["status"] = "rejected"
    save_traders(traders)
    return f'<meta http-equiv="refresh" content="0;url=/admin?key={key}">'


@app.route("/admin/bulk-action", methods=["POST"])
def admin_bulk_action():
    key = request.form.get("key", "")
    if key != ADMIN_KEY:
        return "غير مصرح", 403

    ids_raw = request.form.get("ids", "")
    ids = set(i for i in ids_raw.split(",") if i)
    bulk_action = request.form.get("bulk_action")

    if not ids or not bulk_action:
        return f'<meta http-equiv="refresh" content="0;url=/admin?key={key}">'

    traders = get_traders()

    if bulk_action == "delete":
        traders = [t for t in traders if t["id"] not in ids]
    elif bulk_action in ("approve", "reject"):
        new_status = "approved" if bulk_action == "approve" else "rejected"
        for t in traders:
            if t["id"] in ids:
                t["status"] = new_status
    elif bulk_action in ("priority", "normal", "frozen"):
        for t in traders:
            if t["id"] in ids:
                t["visibility"] = bulk_action
    elif bulk_action == "confirm":
        sent_count = 0
        for t in traders:
            if t["id"] in ids:
                try:
                    send_confirmation_via_template(t)
                    sent_count += 1
                except Exception as e:
                    print("Bulk confirm send failed (non-fatal):", e)
        print(f"Bulk confirmation sent to {sent_count} traders")

    save_traders(traders)
    return f'<meta http-equiv="refresh" content="0;url=/admin?key={key}">'


@app.route("/admin/send-confirmation", methods=["POST"])
def admin_send_confirmation():
    key = request.form.get("key", "")
    if key != ADMIN_KEY:
        return "غير مصرح", 403

    trader_id = request.form.get("id")
    traders = get_traders()
    trader = next((t for t in traders if t["id"] == trader_id), None)
    if trader:
        try:
            send_confirmation_via_template(trader)
        except Exception as e:
            print("Send confirmation failed (non-fatal):", e)

    return f'<meta http-equiv="refresh" content="0;url=/admin?key={key}">'


@app.route("/admin/set-visibility", methods=["POST"])
def admin_set_visibility():
    key = request.form.get("key", "")
    if key != ADMIN_KEY:
        return "غير مصرح", 403

    trader_id = request.form.get("id")
    visibility = request.form.get("visibility")
    if visibility not in ("priority", "normal", "frozen"):
        return "قيمة غير صالحة", 400

    traders = get_traders()
    for t in traders:
        if t["id"] == trader_id:
            t["visibility"] = visibility
    save_traders(traders)
    return f'<meta http-equiv="refresh" content="0;url=/admin?key={key}">'


@app.route("/admin/add-category", methods=["POST"])
def admin_add_category():
    key = request.form.get("key", "")
    if key != ADMIN_KEY:
        return "غير مصرح", 403

    title = request.form.get("title", "").strip()
    if not title:
        return f'<meta http-equiv="refresh" content="0;url=/admin?key={key}">'

    categories = get_categories()
    new_id = "cat_c" + uuid.uuid4().hex[:6]
    categories.append({"id": new_id, "title": title, "match": [title]})
    save_json(CATEGORIES_FILE, categories)
    return f'<meta http-equiv="refresh" content="0;url=/admin?key={key}">'


@app.route("/admin/trigger-report", methods=["GET"])
def admin_trigger_report():
    key = request.args.get("key", "")
    if key != ADMIN_KEY:
        return "غير مصرح", 403

    if not OWNER_WHATSAPP_NUMBER:
        return "لازم تحدد OWNER_WHATSAPP_NUMBER في إعدادات السيرفر الأول عشان التقرير يوصلك.", 400

    stats = load_json(STATS_FILE, {"total": 0, "by_date": {}})
    by_date = stats.get("by_date", {})
    last_7_dates = sorted(by_date.keys())[-7:]
    week_total = sum(by_date.get(d, 0) for d in last_7_dates)

    traders = get_traders()
    approved = [t for t in traders if t.get("status") == "approved"]
    pending = [t for t in traders if t.get("status") == "pending"]
    new_this_week = [
        t for t in traders
        if t.get("submitted_at", "") in last_7_dates and t.get("status") == "approved"
    ]

    categories = get_categories()
    cat_title = {c["id"]: c["title"] for c in categories}
    counts_by_cat = {}
    for t in approved:
        cid = t.get("category_id")
        counts_by_cat[cid] = counts_by_cat.get(cid, 0) + 1
    top_category = max(counts_by_cat, key=counts_by_cat.get) if counts_by_cat else None
    top_category_label = cat_title.get(top_category, "-") if top_category else "-"

    unmatched = load_json(UNMATCHED_FILE, [])
    unmatched_this_week = [u for u in unmatched if u.get("date") in last_7_dates]

    report = (
        "📊 تقرير واتساب السجانة الأسبوعي\n\n"
        f"📩 رسائل الأسبوع دا: {week_total}\n"
        f"✅ تجار معتمدين (الإجمالي): {len(approved)}\n"
        f"🆕 تجار اتوافق عليهم الأسبوع دا: {len(new_this_week)}\n"
        f"⏳ تسجيلات لسه قيد المراجعة: {len(pending)}\n"
        f"🏆 أكتر تخصص عدد تجار: {top_category_label}\n"
        f"❓ طلبات ما لقيناش ليها رد الأسبوع دا: {len(unmatched_this_week)}\n\n"
        f"راجع كل التفاصيل من هنا:\n{SITE_BASE_URL}/admin?key={ADMIN_KEY}"
    )

    try:
        send_text_message(OWNER_WHATSAPP_NUMBER, report)
    except Exception as e:
        return f"فشل إرسال التقرير: {e}", 500

    return "تم إرسال التقرير بنجاح ✅ تقدر تقفل الصفحة دي."


ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


@app.route("/admin/add-ad", methods=["POST"])
def admin_add_ad():
    key = request.form.get("key", "")
    if key != ADMIN_KEY:
        return "غير مصرح", 403

    scope = request.form.get("scope", "category")
    category_id = request.form.get("category_id") if scope == "category" else None
    ad_type = request.form.get("ad_type", "text")
    text = request.form.get("text", "").strip()[:300]

    try:
        daily_limit = max(1, int(request.form.get("daily_limit", 20)))
        duration_days = max(1, int(request.form.get("duration_days", 7)))
    except ValueError:
        daily_limit, duration_days = 20, 7

    ad = {
        "id": "ad_" + uuid.uuid4().hex[:8],
        "scope": scope,
        "category_id": category_id,
        "type": ad_type,
        "text": text,
        "image_path": "",
        "enabled": True,
        "daily_limit": daily_limit,
        "start_date": str(date.today()),
        "end_date": str(date.fromordinal(date.today().toordinal() + duration_days)),
    }

    if ad_type == "image":
        file = request.files.get("image")
        if file and file.filename:
            ext = file.filename.rsplit(".", 1)[-1].lower()
            if ext not in ALLOWED_IMAGE_EXTENSIONS:
                return "امتداد الصورة غير مدعوم (استخدم png أو jpg أو webp)", 400
            filename = "ad_" + uuid.uuid4().hex[:10] + "." + ext
            file.save(os.path.join(ADS_UPLOAD_DIR, filename))
            ad["image_path"] = f"/static/ads/{filename}"
        else:
            return "لازم ترفع صورة لإعلان من نوع صورة", 400

    ads = get_ads()
    ads.append(ad)
    save_ads(ads)
    return f'<meta http-equiv="refresh" content="0;url=/admin?key={key}">'


@app.route("/admin/toggle-ad", methods=["POST"])
def admin_toggle_ad():
    key = request.form.get("key", "")
    if key != ADMIN_KEY:
        return "غير مصرح", 403

    ad_id = request.form.get("id")
    ads = get_ads()
    for ad in ads:
        if ad["id"] == ad_id:
            ad["enabled"] = not ad.get("enabled", True)
    save_ads(ads)
    return f'<meta http-equiv="refresh" content="0;url=/admin?key={key}">'


@app.route("/admin/delete-ad", methods=["POST"])
def admin_delete_ad():
    key = request.form.get("key", "")
    if key != ADMIN_KEY:
        return "غير مصرح", 403

    ad_id = request.form.get("id")
    ads = get_ads()
    ad_to_delete = next((a for a in ads if a["id"] == ad_id), None)
    if ad_to_delete and ad_to_delete.get("image_path"):
        image_file = os.path.join(BASE_DIR, ad_to_delete["image_path"].lstrip("/"))
        if os.path.exists(image_file):
            try:
                os.remove(image_file)
            except OSError:
                pass
    ads = [a for a in ads if a["id"] != ad_id]
    save_ads(ads)
    return f'<meta http-equiv="refresh" content="0;url=/admin?key={key}">'


EDIT_TRADER_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>تعديل بيانات تاجر</title>
<style>
  body{{font-family:Arial,sans-serif; background:#EAE4D9; color:#24272B; padding:24px;}}
  .edit-form{{background:#F5F1E8; padding:24px; max-width:480px; border-radius:6px;}}
  .edit-form label{{display:block; font-weight:bold; margin:14px 0 4px; font-size:0.85rem;}}
  .edit-form input, .edit-form select{{width:100%; padding:8px; font-size:0.95rem;}}
  button{{padding:10px 18px; border:none; border-radius:4px; cursor:pointer; margin-top:18px;}}
  .save-btn{{background:#3f7a4d; color:#fff;}}
  a.back{{display:inline-block; margin-bottom:16px; color:#454B50;}}
</style>
</head>
<body>
<a class="back" href="/admin?key={key}">← رجوع للوحة الإدارة</a>
<h2>تعديل بيانات: {name}</h2>
<form class="edit-form" method="POST" action="/admin/update-trader">
  <input type="hidden" name="key" value="{key}">
  <input type="hidden" name="id" value="{id}">

  <label>اسم التاجر / المحل</label>
  <input type="text" name="name" value="{name}" required>

  <label>رقم الواتساب</label>
  <input type="text" name="whatsapp" value="{whatsapp}" required>

  <label>التخصص</label>
  <select name="category_id">
    {category_options}
  </select>

  <label>كل المنتجات اللي بيبيعها (تفاصيل)</label>
  <input type="text" name="details" value="{details}">

  <label>موقع المحل في السوق</label>
  <input type="text" name="location" value="{location}" required>

  <label>ملاحظات</label>
  <input type="text" name="notes" value="{notes}">

  <button class="save-btn" type="submit">حفظ التعديلات</button>
</form>
</body>
</html>
"""


@app.route("/admin/edit-trader", methods=["GET"])
def edit_trader_page():
    key = request.args.get("key", "")
    if key != ADMIN_KEY:
        return "غير مصرح", 403

    trader_id = request.args.get("id", "")
    traders = get_traders()
    trader = next((t for t in traders if t["id"] == trader_id), None)
    if not trader:
        return "التاجر غير موجود", 404

    categories = get_categories()
    options = "".join(
        f'<option value="{c["id"]}"'
        f'{" selected" if c["id"] == trader.get("category_id") else ""}>'
        f'{c["title"]}</option>'
        for c in categories
    )

    return EDIT_TRADER_PAGE.format(
        key=key,
        id=trader["id"],
        name=trader.get("name", ""),
        whatsapp=trader.get("whatsapp", ""),
        details=trader.get("details", ""),
        location=trader.get("location", ""),
        notes=trader.get("notes", ""),
        category_options=options,
    )


@app.route("/admin/update-trader", methods=["POST"])
def update_trader():
    key = request.form.get("key", "")
    if key != ADMIN_KEY:
        return "غير مصرح", 403

    trader_id = request.form.get("id")
    traders = get_traders()
    for t in traders:
        if t["id"] == trader_id:
            t["name"] = request.form.get("name", t.get("name", ""))
            t["whatsapp"] = request.form.get("whatsapp", t.get("whatsapp", ""))
            t["category_id"] = request.form.get("category_id", t.get("category_id", ""))
            t["details"] = request.form.get("details", t.get("details", ""))
            t["location"] = request.form.get("location", t.get("location", ""))
            t["notes"] = request.form.get("notes", t.get("notes", ""))
    save_traders(traders)
    return f'<meta http-equiv="refresh" content="0;url=/admin?key={key}">'


EDIT_CATEGORY_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>تعديل تخصص</title>
<style>
  body{{font-family:Arial,sans-serif; background:#EAE4D9; color:#24272B; padding:24px;}}
  .edit-form{{background:#F5F1E8; padding:24px; max-width:480px; border-radius:6px;}}
  .edit-form label{{display:block; font-weight:bold; margin:14px 0 4px; font-size:0.85rem;}}
  .edit-form input{{width:100%; padding:8px; font-size:0.95rem;}}
  button{{padding:10px 18px; border:none; border-radius:4px; cursor:pointer; margin-top:18px;}}
  .save-btn{{background:#3f7a4d; color:#fff;}}
  a.back{{display:inline-block; margin-bottom:16px; color:#454B50;}}
</style>
</head>
<body>
<a class="back" href="/admin?key={key}">← رجوع للوحة الإدارة</a>
<h2>تعديل اسم التخصص</h2>
<form class="edit-form" method="POST" action="/admin/update-category">
  <input type="hidden" name="key" value="{key}">
  <input type="hidden" name="id" value="{id}">
  <label>اسم التخصص</label>
  <input type="text" name="title" value="{title}" required>
  <button class="save-btn" type="submit">حفظ التعديل</button>
</form>
</body>
</html>
"""


@app.route("/admin/edit-category", methods=["GET"])
def edit_category_page():
    key = request.args.get("key", "")
    if key != ADMIN_KEY:
        return "غير مصرح", 403

    cat_id = request.args.get("id", "")
    cat = get_category_by_id(cat_id)
    if not cat:
        return "التخصص غير موجود", 404

    return EDIT_CATEGORY_PAGE.format(key=key, id=cat["id"], title=cat["title"])


@app.route("/admin/update-category", methods=["POST"])
def update_category():
    key = request.form.get("key", "")
    if key != ADMIN_KEY:
        return "غير مصرح", 403

    cat_id = request.form.get("id")
    new_title = request.form.get("title", "").strip()
    if not new_title:
        return f'<meta http-equiv="refresh" content="0;url=/admin?key={key}">'

    categories = get_categories()
    for c in categories:
        if c["id"] == cat_id:
            c["title"] = new_title
            if new_title not in c.get("match", []):
                c.setdefault("match", []).append(new_title)
    save_json(CATEGORIES_FILE, categories)
    return f'<meta http-equiv="refresh" content="0;url=/admin?key={key}">'


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
