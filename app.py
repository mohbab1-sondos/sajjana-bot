import json
import os
import random
import re
import uuid
from datetime import date

import requests
from flask import Flask, jsonify, request

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

WELCOME_TEXT = "🏗️ أهلاً بيكم في واتساب السجانة! اختار التخصص اللي بتفتش عليهو من القائمة تحت:"
NOT_FOUND_MESSAGE = (
    "ما لقيناهو دا للأسف 🤔\n"
    'اكتب اسم التخصص، أو اكتب كلمة "قائمة" عشان تشوف كل الخيارات.'
)
EMPTY_CATEGORY_MESSAGE = (
    "للأسف لسه ما عندنا تجار مسجلين في التخصص دا، جرّب تاني قريب 🙏"
)
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
ASK_PRODUCT_TEXT = (
    'تمام 👍 اكتب اسم الصنف ال بتفتش عليه، أو كلمة "قائمة" عشان تشوف كل التخصصات.'
)
TRADER_THANK_YOU_TEXT = (
    "شكراً ليك على تسجيلك في واتساب السجانة! 🎉\n"
    "طلبك الان قيد المراجعة، وح نبلّغك بالواتساب فور ما يتم اعتماده.\n\n"
    "لو داير تساعدنا، شارك رابط التسجيل مع تجار تعرفهم في السوق:\n"
    f"{REGISTER_URL}"
)
NOT_REGISTERED_TRADER_MESSAGE = (
    "عذراً، هذا الرقم غير مسجل لدينا كتاجر في دليل السجانة 🙏\n"
    "إذا كنت تاجراً وترغب في الانضمام، يمكنك تسجيل محلك من الرابط التالي:\n"
    f"{REGISTER_URL}\n\n"
    "أو تأكد من كتابة الرقم بشكل صحيح إذا كنت مسجلاً مسبقاً."
)
CUSTOMER_CONFIRM_GUIDE_TEXT = (
    "هذا الخيار مخصص للتجار لمراجعة بيانات محالهم المسجلة 🏗️\n\n"
    "إذا كنت تبحث عن تاجر مواد بناء، اكتب **اسم الصنف** الذي تحتاجه (مثل:"
    " سيراميك، اسمنت، حديد) وسنرسل لك بيانات التاجر فوراً."
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
    {
        "id": "cat_decor",
        "title": "ديكورات",
        "match": ["ديكور", "ديكورات", "تشطيب", "جبس"],
    },
    {
        "id": "cat_ceramic",
        "title": "سيراميك",
        "match": ["سيراميك", "بلاط", "بورسلين"],
    },
    {"id": "cat_cement", "title": "اسمنت", "match": ["اسمنت", "سمنت"]},
    {
        "id": "cat_electric",
        "title": "كهرباء",
        "match": ["كهرباء", "اسلاك", "لمبات"],
    },
    {
        "id": "cat_plumbing",
        "title": "سباكة",
        "match": ["سباكة", "مواسير", "انابيب", "حنفيات"],
    },
    {"id": "cat_iron", "title": "حديد", "match": ["حديد", "حديد تسليح"]},
    {"id": "cat_other", "title": "أخرى", "match": []},
]

DEFAULT_TRADERS = [
    {
        "id": "t1",
        "name": "ديزاين لاين",
        "whatsapp": "249912351105",
        "category_id": "cat_decor",
        "location": "شارع النص",
        "details": "",
        "status": "approved",
        "visibility": "normal",
    },
    {
        "id": "t2",
        "name": "حسين",
        "whatsapp": "966562762669",
        "category_id": "cat_ceramic",
        "location": "شارع سوداتل",
        "details": "",
        "status": "approved",
        "visibility": "normal",
    },
    {
        "id": "t3",
        "name": "سامي",
        "whatsapp": "249918213703",
        "category_id": "cat_cement",
        "location": "شارع الحرية",
        "details": "",
        "status": "approved",
        "visibility": "normal",
    },
    {
        "id": "t4",
        "name": "شوقي",
        "whatsapp": "249927382171",
        "category_id": "cat_electric",
        "location": "شارع البوسنة",
        "details": "",
        "status": "approved",
        "visibility": "normal",
    },
    {
        "id": "t5",
        "name": "محمد",
        "whatsapp": "249123091999",
        "category_id": "cat_plumbing",
        "location": "الملجة",
        "details": "",
        "status": "approved",
        "visibility": "normal",
    },
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
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
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
  return {
      t["whatsapp"] for t in get_traders() if t.get("status") == "approved"
  }


def is_registered_trader(phone_number):
  return phone_number in all_known_phones()


def check_and_increment_limit(phone_number):
  counters = load_json(COUNTERS_FILE, {})
  today = str(date.today())
  day_counts = counters.get(today, {})

  limit = (
      TRADER_DAILY_LIMIT
      if is_registered_trader(phone_number)
      else SHOPPER_DAILY_LIMIT
  )
  current = day_counts.get(phone_number, 0)

  if current >= limit:
    return False

  day_counts[phone_number] = current + 1
  counters[today] = day_counts
  counters = {k: v for k, v in sorted(counters.items())[-2:]}
  save_json(COUNTERS_FILE, counters)
  return True


# =========================================================
# اختيار التجار للرد
# =========================================================
def get_category_traders(cat_id):
  return [
      t
      for t in get_traders()
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
  title = (
      get_category_by_id(cat_id)["title"] if get_category_by_id(cat_id) else ""
  )
  blocks = [
      f"🔹 *{title}*: {t['name']}\n📍 {t['location']}\n📞 {t['whatsapp']}"
      for t in chosen
  ]
  text = "\n\n".join(blocks)
  if total > len(chosen):
    text += (
        "\n\n(في تجار تانيين متاحين — اسأل تاني عن نفس التخصص عشان تشوف أسماء"
        " تانية)"
    )
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
  headers = {
      "Authorization": f"Bearer {ACCESS_TOKEN}",
      "Content-Type": "application/json",
  }
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
  to_number = normalize_phone(to_number)
  headers = {
      "Authorization": f"Bearer {ACCESS_TOKEN}",
      "Content-Type": "application/json",
  }
  payload = {
      "messaging_product": "whatsapp",
      "to": to_number,
      "type": "template",
      "template": {
          "name": template_name,
          "language": {"code": language_code},
          "components": [{
              "type": "body",
              "parameters": [{"type": "text", "text": p} for p in body_params],
          }],
      },
  }
  response = requests.post(GRAPH_API_URL, headers=headers, json=payload)
  print("Send template status:", response.status_code, response.text)
  return response


def send_role_question(to_number):
  headers = {
      "Authorization": f"Bearer {ACCESS_TOKEN}",
      "Content-Type": "application/json",
  }
  payload = {
      "messaging_product": "whatsapp",
      "to": to_number,
      "type": "interactive",
      "interactive": {
          "type": "button",
          "body": {
              "text": (
                  "🏗️ أهلاً بيك في واتساب السجانة! قبل ما نبدأ، عرفنا بنفسك "
              )
          },
          "action": {
              "buttons": [
                  {
                      "type": "reply",
                      "reply": {"id": ROLE_TRADER_ID, "title": "🔧 أنا تاجر"},
                  },
                  {
                      "type": "reply",
                      "reply": {"id": ROLE_CUSTOMER_ID, "title": "🛒أنا زبون "},
                  },
              ]
          },
      },
  }
  response = requests.post(GRAPH_API_URL, headers=headers, json=payload)
  print("Send role question status:", response.status_code, response.text)
  return response


def send_list_message(to_number):
  headers = {
      "Authorization": f"Bearer {ACCESS_TOKEN}",
      "Content-Type": "application/json",
  }
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
        trader = next(
            (
                t
                for t in get_traders()
                if t.get("whatsapp") == from_number
                and t.get("status") == "approved"
            ),
            None,
        )
        if trader:
          send_confirmation_via_template(trader)
        else:
          send_text_message(from_number, CUSTOMER_CONFIRM_GUIDE_TEXT)
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
  with open(
      os.path.join(BASE_DIR, "templates", "index.html"), encoding="utf-8"
  ) as f:
    return f.read()


@app.route("/register", methods=["GET"])
def register_page():
  with open(
      os.path.join(BASE_DIR, "templates", "register.html"), encoding="utf-8"
  ) as f:
    html = f.read()
  options = "\n".join(
      f'<option value="{c["title"]}">{c["title"]}</option>'
      for c in get_categories()
  )
  html = html.replace("<!--CATEGORY_OPTIONS-->", options)

  prefill_script = ""
  raw_trader_id = request.args.get("id", "")
  trader_id_match = re.match(r"^[A-Za-z0-9_-]+", raw_trader_id.strip())
  trader_id = trader_id_match.group(0) if trader_id_match else ""
  if trader_id:
    trader = next((t for t in get_traders() if t.get("id") == trader_id), None)
    if trader:
      cat_title = {c["id"]: c["title"] for c in get_categories()}
      data = {
          "name": trader.get("name", ""),
          "whatsapp": trader.get("whatsapp", ""),
          "specialty": cat_title.get(trader.get("category_id"), ""),
          "details": trader.get("details", ""),
          "location": trader.get("location", ""),
      }
      prefill_script = (
          "<script>window.__prefillData = "
          + json.dumps(data, ensure_ascii=False)
          + ";</script>"
      )
  html = html.replace("<!--PREFILL_SCRIPT-->", prefill_script)

  return html


@app.route("/check", methods=["GET"])
def check_page():
  with open(
      os.path.join(BASE_DIR, "templates", "check.html"), encoding="utf-8"
  ) as f:
    return f.read()


def normalize_phone(raw):
  digits = "".join(ch for ch in raw if ch.isdigit())
  if digits.startswith("00"):
    digits = digits[2:]
  return digits


ABOUT_APP_INTRO = (
    "🏗️ *واتساب السجانة*\n"
    "خدمة مجانية بتربط تجار سوق السجانة بالخرطوم مباشرة بالمشترين من المقاولين"
    " والزبائن عبر الواتساب — الزبون بيكتب اسم الصنف الداير يشتريه، وبنوصله بيك"
    " مباشرة من غير ما يلف السوق كله.\n\n"
    "فايدتك من الانضمام: زباين جدد بيوصلوك من غير أي مجهود منك.\n"
)

CONFIRM_DATA_TEMPLATE_NAME = "confirm_trader_data"
CONFIRM_DATA_TEMPLATE_LANG = "ar"


def build_correction_link(trader):
  return f"{REGISTER_URL}?correction=1&id={trader.get('id', '')}"


def send_confirmation_via_template(trader):
  cat_title = {c["id"]: c["title"] for c in get_categories()}
  status = trader.get("status", "pending")
  name = trader.get("name", "") or "تاجرنا العزيز"
  category = cat_title.get(trader.get("category_id"), "") or "-"
  location = trader.get("location", "") or "-"
  details = trader.get("details", "") or "-"

  if status == "approved":
    params = [name, category, location, details, build_correction_link(trader)]
  elif status == "pending":
    params = [
        name,
        "قيد المراجعة",
        "-",
        "طلبك لسه ما تمت الموافقة عليه",
        REGISTER_URL,
    ]
  else:
    params = [
        name,
        "-",
        "-",
        "الطلب ما اتقبل سابقاً، سجل من جديد",
        REGISTER_URL,
    ]

  return send_template_message(
      trader.get("whatsapp", ""),
      CONFIRM_DATA_TEMPLATE_NAME,
      CONFIRM_DATA_TEMPLATE_LANG,
      params,
  )


def build_check_message(trader, include_intro=True):
  cat_title = {c["id"]: c["title"] for c in get_categories()}
  status = trader.get("status", "pending")
  name = trader.get("name", "")
  category = cat_title.get(trader.get("category_id"), "")
  location = trader.get("location", "")
  details = trader.get("details", "") or "-"
  whatsapp = trader.get("whatsapp", "")

  intro = ABOUT_APP_INTRO if include_intro else ""

  if status == "approved":
    return (
        f"{intro}\n"
        "بنراجع بيانات التجار المسجلين معانا — دي بياناتك الحالية عندنا:\n\n"
        f"الاسم: {name}\n"
        f"التخصص: {category}\n"
        f"الموقع: {location}\n"
        f"التفاصيل: {details}\n\n"
        f"البيانات غلط أو ناقصة؟ صحّحها من"
        f" هنا:\n{build_correction_link(trader)}"
    )
  elif status == "pending":
    return (
        f"{intro}\n"
        f'طلب انضمامك باسم "{name}" لسه قيد المراجعة.\n'
        "هنبلغك على واتساب فور ما يتم الاعتماد."
    )
  else:
    return (
        f"{intro}\n"
        f'طلب باسم "{name}" ({whatsapp}) ما اتقبل سابقاً.\n'
        f"تقدر تسجل من جديد من هنا:\n{REGISTER_URL}"
    )


@app.route("/api/check-trader", methods=["GET"])
def api_check_trader():
  phone_raw = request.args.get("whatsapp", "").strip()
  name_query = request.args.get("name", "").strip().lower()

  if not phone_raw and not name_query:
    return (
        jsonify({
            "status": "error",
            "message": "يرجى كتابة رقم الواتساب أو اسم المحل للتأكد.",
        }),
        400,
    )

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

  # حالة عدم وجود الرقم في قاعدة البيانات
  if not matches:
    if phone_raw:
      try:
        send_text_message(phone_raw, NOT_REGISTERED_TRADER_MESSAGE)
      except Exception as e:
        print("Failed to send not-registered message:", e)
    return jsonify({
        "status": "not_found",
        "message": (
            "هذا الرقم غير مسجل لدينا كتاجر. تم إرسال رسالة توضيحية على الواتساب"
            " للتأكد من الرقم أو التسجيل."
        ),
    })

  # حالة وجود التاجر
  for t in matches:
    try:
      send_confirmation_via_template(t)
    except Exception as e:
      print("Check-trader message send failed (non-fatal):", e)

  return jsonify({
      "status": "success",
      "message": (
          "تم إرسال بيانات التعديل والتأكيد إلى رقم الواتساب المسجل لدينا"
          f" ({matches[0].get('whatsapp')})."
      ),
  })


@app.route("/submit-trader", methods=["POST"])
def submit_trader():
  try:
    payload = request.get_json()
    required = ["name", "whatsapp", "specialty", "details", "location"]
    if not payload or any(not payload.get(field) for field in required):
      return jsonify({"status": "error", "message": "بيانات ناقصة"}), 400

    traders = get_traders()
    correction_for_id = payload.get("correction_for_id", "").strip()
    original = None
    if correction_for_id:
      original = next(
          (
              t
              for t in traders
              if t["id"] == correction_for_id and t.get("status") == "approved"
          ),
          None,
      )

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

    if original:
      new_trader["is_correction"] = True
      new_trader["correction_for_id"] = original["id"]
      original["status"] = "correction_pending"
      original["pending_correction_id"] = new_trader["id"]

    traders.append(new_trader)
    save_traders(traders)

    try:
      if original:
        send_text_message(
            new_trader["whatsapp"],
            "تم استلام طلب تصحيح بياناتك 👍 هنراجعه ونحدّثه قريباً.",
        )
      else:
        send_text_message(new_trader["whatsapp"], TRADER_THANK_YOU_TEXT)
    except Exception as send_err:
      print("Thank-you message failed (non-fatal):", send_err)

    if not original:
      notify_owner_new_trader(new_trader)

    return jsonify({"status": "ok"}), 200
  except Exception as e:
    print("Submit error:", e)
    return jsonify({"status": "error", "message": str(e)}), 500


# =========================================================
# صفحة الإدارة
# =========================================================
ADMIN_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>إدارة واتساب السجانة</title>
<link rel="icon" type="image/png" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==">
<style>
  body { font-family: system-ui, -apple-system, sans-serif; margin: 20px; background-color: #f4f6f8; color: #333; }
  h1, h2 { color: #111; }
  .card { background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
  table { width: 100%; border-collapse: collapse; margin-top: 10px; }
  th, td { border: 1px solid #ddd; padding: 10px; text-align: right; }
  th { background-color: #f0f0f0; }
  .badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
  .badge-approved { background-color: #d4edda; color: #155724; }
  .badge-pending { background-color: #fff3cd; color: #856404; }
  .badge-rejected { background-color: #f8d7da; color: #721c24; }
  button { padding: 6px 12px; margin: 2px; border: none; border-radius: 4px; cursor: pointer; }
  .btn-approve { background-color: #28a745; color: white; }
  .btn-reject { background-color: #dc3545; color: white; }
</style>
</head>
<body>
  <h1>لوحة التحكم - واتساب السجانة</h1>
  <div class="card">
    <h2>الإحصائيات السريعة</h2>
    <p>إجمالي الرسائل: <strong id="total-msg">0</strong> | رسائل اليوم: <strong id="today-msg">0</strong></p>
  </div>
  <div class="card">
    <h2>قائمة التجار</h2>
    <table id="traders-table">
      <thead>
        <tr>
          <th>الاسم</th>
          <th>الواتساب</th>
          <th>التخصص</th>
          <th>الموقع</th>
          <th>الحالة</th>
          <th>الإجراءات</th>
        </tr>
      </thead>
      <tbody></tbody>
    </table>
  </div>
</body>
</html>
"""


@app.route("/admin", methods=["GET"])
def admin_page():
  key = request.args.get("key", "")
  if key != ADMIN_KEY:
    return "حساب غير مصرح له", 403
  return ADMIN_PAGE


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=True)

@app.route("/check", methods=["GET"])
def check_page():
  with open(
      os.path.join(BASE_DIR, "templates", "check.html"), encoding="utf-8"
  ) as f:
    return f.read()
cat << 'EOF' >> /home/mohbab/sajjana-bot/app.py

@app.route("/check", methods=["GET"])
def check_page():
    with open(os.path.join(BASE_DIR, "templates", "check.html"), encoding="utf-8") as f:
        return f.read()
EOF
