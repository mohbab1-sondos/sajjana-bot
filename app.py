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

GRAPH_API_URL = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"

BASE_DIR = os.path.dirname(__file__)
TRADERS_FILE = os.path.join(BASE_DIR, "traders.json")
CATEGORIES_FILE = os.path.join(BASE_DIR, "categories.json")
COUNTERS_FILE = os.path.join(BASE_DIR, "counters.json")
SHOWN_FILE = os.path.join(BASE_DIR, "shown_history.json")
USERS_FILE = os.path.join(BASE_DIR, "users.json")
STATS_FILE = os.path.join(BASE_DIR, "message_stats.json")

REGISTER_URL = "https://mohbab.pythonanywhere.com/register"

TRADER_DAILY_LIMIT = 15
SHOPPER_DAILY_LIMIT = 5
MAX_TRADERS_PER_REPLY = 4
PRIORITY_SLOTS = 2

JOIN_ROW_ID = "cat_join_trader"

WELCOME_TEXT = "🏗️ أهلاً بيك في دليل سوق السجانة! اختار التخصص اللي بتدور عليه من القائمة تحت:"
NOT_FOUND_MESSAGE = (
    "ما لقيتش تخصص مطابق 🤔\n"
    "اكتب اسم التخصص، أو اكتب \"قائمة\" عشان تشوف كل الخيارات."
)
EMPTY_CATEGORY_MESSAGE = "لسه مفيش تجار مسجلين في التخصص ده، جرب تاني قريب 🙏"
LIMIT_REACHED_MESSAGE = (
    "وصلت للحد الأقصى من الرسائل المسموحة النهاردة 🙏\n"
    "جرب تاني بكرة، أو لو الموضوع مستعجل تواصل معانا مباشرة."
)
JOIN_REPLY_TEXT = (
    f"يسعدنا انضمامك لدليل السجانة! 🎉\n"
    f"سجّل بياناتك من الرابط ده (يستغرق دقيقة بس):\n{REGISTER_URL}"
)
ASK_PRODUCT_TEXT = "تمام 👍 اكتب اسم الصنف اللي بتدور عليه، أو ابعت \"قائمة\" عشان تشوف كل التخصصات."
TRADER_THANK_YOU_TEXT = (
    "شكراً لتسجيلك في دليل السجانة! 🎉\n"
    "طلبك دلوقتي قيد المراجعة، وهنبلغك بالواتساب فور ما يتم اعتماده.\n\n"
    "لو حابب تساعدنا، شارك رابط التسجيل مع تجار تعرفهم في السوق:\n"
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
    {"id": "t2", "name": "هنادي", "whatsapp": "966562762669", "category_id": "cat_ceramic",
     "location": "شارع سوداتل", "details": "", "status": "approved", "visibility": "normal"},
    {"id": "t3", "name": "سحر", "whatsapp": "249918213703", "category_id": "cat_cement",
     "location": "شارع الحرية", "details": "", "status": "approved", "visibility": "normal"},
    {"id": "t4", "name": "شروق", "whatsapp": "249927382171", "category_id": "cat_electric",
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

    join_words = ["انضمام", "انضم", "تسجيل", "أنا تاجر", "عايز انضم"]
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


def send_role_question(to_number):
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "🏗️ أهلاً بيك في واتساب السجانة! قبل ما نبدأ، مين حضرتك؟"},
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
            "header": {"type": "text", "text": "دليل السجانة"},
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
                send_text_message(from_number, JOIN_REPLY_TEXT)
            elif kind == "category":
                reply = build_category_reply(value_, from_number)
                send_text_message(from_number, reply)
            else:
                send_text_message(from_number, NOT_FOUND_MESSAGE)

        elif msg_type == "interactive":
            interactive = message.get("interactive", {})
            selected_id = None

            if interactive.get("type") == "list_reply":
                selected_id = interactive["list_reply"]["id"]
            elif interactive.get("type") == "button_reply":
                selected_id = interactive["button_reply"]["id"]

            if selected_id == ROLE_TRADER_ID:
                set_user_role(from_number, "trader")
                send_text_message(from_number, JOIN_REPLY_TEXT)
            elif selected_id == ROLE_CUSTOMER_ID:
                set_user_role(from_number, "customer")
                send_text_message(from_number, ASK_PRODUCT_TEXT)
            elif selected_id == JOIN_ROW_ID:
                send_text_message(from_number, JOIN_REPLY_TEXT)
            elif selected_id and get_category_by_id(selected_id):
                reply = build_category_reply(selected_id, from_number)
                send_text_message(from_number, reply)
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
<title>إدارة دليل السجانة</title>
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
</style>
</head>
<body>
<div class="logo-header" style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
  <img src="/static/logo.png" alt="شعار" style="height:36px;width:36px;object-fit:contain;">
  <h1 style="margin:0;">لوحة إدارة دليل السجانة</h1>
</div>

<div class="stats-bar">
  <div class="stat-box">رسائل اليوم<b>{msgs_today}</b></div>
  <div class="stat-box">إجمالي الرسائل<b>{msgs_total}</b></div>
</div>

<h2>تسجيلات قيد المراجعة ({pending_count})</h2>
{pending_table}

<h2>كل التجار المعتمدين ({approved_count})</h2>
{approved_table}

<h2>إضافة تخصص جديد</h2>
<form class="add-form" method="POST" action="/admin/add-category">
  <input type="hidden" name="key" value="{key}">
  <input type="text" name="title" placeholder="اسم التخصص الجديد" required>
  <button class="approve" type="submit">إضافة التخصص</button>
</form>

<h2>التخصصات الحالية</h2>
<p>{categories_list}</p>

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

    traders = get_traders()
    categories = get_categories()
    cat_title = {c["id"]: c["title"] for c in categories}

    pending = [t for t in traders if t.get("status") == "pending"]
    approved = [t for t in traders if t.get("status") == "approved"]

    if not pending:
        pending_table = '<p class="empty">مفيش تسجيلات جديدة قيد المراجعة.</p>'
    else:
        rows = ""
        for t in pending:
            rows += f"""
            <tr>
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
        pending_table = f"""<table><tr>
          <th>الاسم</th><th>واتساب</th><th>التخصص</th><th>التفاصيل</th><th>الموقع</th><th>إجراء</th>
        </tr>{rows}</table>"""

    if not approved:
        approved_table = '<p class="empty">مفيش تجار معتمدين لسه.</p>'
    else:
        rows = ""
        for t in approved:
            vis = t.get("visibility", "normal")
            rows += f"""
            <tr>
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
                <form class="inline" method="POST" action="/admin/trader-action"
                      onsubmit="return confirm('متأكد من الحذف النهائي؟');">
                  <input type="hidden" name="key" value="{key}">
                  <input type="hidden" name="id" value="{t['id']}">
                  <input type="hidden" name="action" value="delete">
                  <button class="delete" type="submit">حذف نهائي</button>
                </form>
              </td>
            </tr>"""
        approved_table = f"""<table><tr>
          <th>الاسم</th><th>واتساب</th><th>التخصص</th><th>الحالة</th><th>إجراء</th>
        </tr>{rows}</table>"""

    categories_list = "".join(
        f'<span class="cat-chip">{c["title"]} '
        f'<a class="btn-link" href="/admin/edit-category?key={key}&id={c["id"]}">تعديل</a></span>'
        for c in categories
    )

    stats = get_message_stats()

    return ADMIN_PAGE.format(
        pending_count=len(pending),
        pending_table=pending_table,
        approved_count=len(approved),
        approved_table=approved_table,
        key=key,
        categories_list=categories_list,
        msgs_today=stats["today"],
        msgs_total=stats["total"],
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
