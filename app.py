import os
import json
from datetime import date

import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "sajjana123")

GRAPH_API_URL = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"

BASE_DIR = os.path.dirname(__file__)
SUBMISSIONS_FILE = os.path.join(BASE_DIR, "traders_submissions.json")
COUNTERS_FILE = os.path.join(BASE_DIR, "counters.json")

REGISTER_URL = "https://mohbab.pythonanywhere.com/register"

TRADER_DAILY_LIMIT = 15
SHOPPER_DAILY_LIMIT = 5

TRADERS = [
    {
        "id": "cat_decor",
        "specialty": "ديكورات",
        "keywords": ["ديكور", "ديكورات", "تشطيب", "جبس", "دهانات ديكور"],
        "reply": "🔹 *ديكورات*: ديزاين لاين\n📍 شارع النص\n📞 249912351105",
        "phone": "249912351105",
    },
    {
        "id": "cat_ceramic",
        "specialty": "سيراميك",
        "keywords": ["سيراميك", "بلاط", "سيراميك حمام", "سيراميك مطبخ", "بورسلين"],
        "reply": "🔹 *سيراميك*: هنادي\n📍 شارع سوداتل\n📞 00966 56 276 2669",
        "phone": "966562762669",
    },
    {
        "id": "cat_cement",
        "specialty": "اسمنت",
        "keywords": ["اسمنت", "سمنت", "اسمنت ابيض", "اسمنت اسود"],
        "reply": "🔹 *اسمنت*: سحر\n📍 شارع الحرية\n📞 00249 91 821 3703",
        "phone": "249918213703",
    },
    {
        "id": "cat_electric",
        "specialty": "كهرباء",
        "keywords": ["كهرباء", "ادوات كهربائية", "اسلاك", "لمبات", "مفاتيح كهرباء"],
        "reply": "🔹 *كهرباء*: شروق\n📍 شارع البوسنة\n📞 00249 92 738 2171",
        "phone": "249927382171",
    },
    {
        "id": "cat_plumbing",
        "specialty": "سباكة",
        "keywords": ["سباكة", "مواسير", "انابيب", "حنفيات", "ادوات صحية"],
        "reply": "🔹 *سباكة*: محمد\n📍 الملجة\n📞 249123091999",
        "phone": "249123091999",
    },
]

JOIN_ROW_ID = "cat_join_trader"

WELCOME_TEXT = "🏗️ أهلاً بيك في دليل سوق السجانة! اختار التخصص اللي بتدور عليه من القائمة تحت:"
NOT_FOUND_MESSAGE = (
    "ما لقيتش تخصص مطابق 🤔\n"
    "اكتب اسم واحد من دول: ديكورات، سيراميك، اسمنت، كهرباء، سباكة — أو اكتب \"قائمة\" عشان تشوف كل الخيارات."
)
LIMIT_REACHED_MESSAGE = (
    "وصلت للحد الأقصى من الرسائل المسموحة النهاردة 🙏\n"
    "جرب تاني بكرة، أو لو الموضوع مستعجل تواصل معانا مباشرة."
)
JOIN_REPLY_TEXT = (
    f"يسعدنا انضمامك لدليل السجانة! 🎉\n"
    f"سجّل بياناتك من الرابط ده (يستغرق دقيقة بس):\n{REGISTER_URL}"
)


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


def is_registered_trader(phone_number):
    known = {t["phone"] for t in TRADERS}
    return phone_number in known


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


def find_text_reply(user_text):
    text = user_text.strip().lower()

    if text in ("قائمة", "list", "الخيارات"):
        return ("list", None)

    join_words = ["انضمام", "انضم", "تسجيل", "أنا تاجر", "عايز انضم"]
    if any(w in text for w in join_words):
        return ("text", JOIN_REPLY_TEXT)

    greetings = ["السلام", "سلام", "اهلا", "أهلا", "هاي", "hi", "hello"]
    if any(g in text for g in greetings) and len(text) < 20:
        return ("list", None)

    for trader in TRADERS:
        for kw in trader["keywords"]:
            if kw in text:
                return ("text", trader["reply"])

    return ("text", NOT_FOUND_MESSAGE)


def send_text_message(to_number, message):
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


def send_list_message(to_number):
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    rows = [{"id": t["id"], "title": t["specialty"]} for t in TRADERS]
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


def reply_for_list_selection(selected_id):
    if selected_id == JOIN_ROW_ID:
        return JOIN_REPLY_TEXT
    for trader in TRADERS:
        if trader["id"] == selected_id:
            return trader["reply"]
    return NOT_FOUND_MESSAGE


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

        if not check_and_increment_limit(from_number):
            send_text_message(from_number, LIMIT_REACHED_MESSAGE)
            return jsonify({"status": "ok"}), 200

        if msg_type == "text":
            user_text = message["text"]["body"]
            kind, content = find_text_reply(user_text)
            if kind == "list":
                send_list_message(from_number)
            else:
                send_text_message(from_number, content)

        elif msg_type == "interactive":
            interactive = message.get("interactive", {})
            if interactive.get("type") == "list_reply":
                selected_id = interactive["list_reply"]["id"]
                reply = reply_for_list_selection(selected_id)
                send_text_message(from_number, reply)

    except (KeyError, IndexError) as e:
        print("No message content to process:", e)

    return jsonify({"status": "ok"}), 200


@app.route("/", methods=["GET"])
def home():
    with open(os.path.join(BASE_DIR, "templates", "index.html"), encoding="utf-8") as f:
        return f.read()


@app.route("/register", methods=["GET"])
def register_page():
    with open(os.path.join(BASE_DIR, "templates", "register.html"), encoding="utf-8") as f:
        return f.read()


@app.route("/submit-trader", methods=["POST"])
def submit_trader():
    try:
        payload = request.get_json()
        required = ["name", "whatsapp", "specialty", "details", "location"]
        if not payload or any(not payload.get(field) for field in required):
            return jsonify({"status": "error", "message": "بيانات ناقصة"}), 400

        submissions = load_json(SUBMISSIONS_FILE, [])
        payload["submitted_at"] = str(date.today())
        submissions.append(payload)
        save_json(SUBMISSIONS_FILE, submissions)

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print("Submit error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
