import os
import requests
from flask import Flask, request, jsonify

app = Flask(name)

ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "sajjana123")

GRAPH_API_URL = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"

TRADERS = [
    {"specialty": "ديكورات", "keywords": ["ديكور", "ديكورات", "تشطيب", "جبس", "دهانات ديكور"],
     "reply": "🔹 *ديكورات*: ديزاين لاين\n📍 شارع النص\n📞 249912351105"},
    {"specialty": "سيراميك", "keywords": ["سيراميك", "بلاط", "سيراميك حمام", "سيراميك مطبخ", "بورسلين"],
     "reply": "🔹 *سيراميك*: هنادي\n📍 شارع سوداتل\n📞 00966 56 276 2669"},
    {"specialty": "اسمنت", "keywords": ["اسمنت", "سمنت", "اسمنت ابيض", "اسمنت اسود"],
     "reply": "🔹 *اسمنت*: سحر\n📍 شارع الحرية\n📞 00249 91 821 3703"},
    {"specialty": "كهرباء", "keywords": ["كهرباء", "ادوات كهربائية", "اسلاك", "لمبات", "مفاتيح كهرباء"],
     "reply": "🔹 *كهرباء*: شروق\n📍 شارع البوسنة\n📞 00249 92 738 2171"},
    {"specialty": "سباكة", "keywords": ["سباكة", "مواسير", "انابيب", "حنفيات", "ادوات صحية"],
     "reply": "🔹 *سباكة*: محمد\n📍 الملجة\n📞 249123091999"},
]

WELCOME_MESSAGE = ("🏗️ أهلاً بيك في دليل سوق السجانة!\n\n"
    "اكتب اسم اللي بتدور عليه وهنوصلك فوراً بأقرب تاجر متخصص:\n\n"
    "🔹 ديكورات\n🔹 سيراميك\n🔹 اسمنت\n🔹 كهرباء\n🔹 سباكة")

NOT_FOUND_MESSAGE = ("ما لقيتش تخصص مطابق 🤔\n"
    "جرب تكتب واحدة من الكلمات دي: ديكورات، سيراميك، اسمنت، كهرباء، سباكة")


def find_reply(user_text: str) -> str:
    text = user_text.strip().lower()
    greetings = ["السلام", "سلام", "اهلا", "أهلا", "هاي", "hi", "hello"]
    if any(g in text for g in greetings) and len(text) < 20:
        return WELCOME_MESSAGE
    for trader in TRADERS:
        for kw in trader["keywords"]:
            if kw in text:
                return trader["reply"]
    return NOT_FOUND_MESSAGE


def send_whatsapp_message(to_number: str, message: str):
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to_number, "type": "text", "text": {"body": message}}
    response = requests.post(GRAPH_API_URL, headers=headers, json=payload)
    print("Send status:", response.status_code, response.text)
    return response


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
        if "messages" in value:
            message = value["messages"][0]
            from_number = message["from"]
            msg_type = message.get("type")
            if msg_type == "text":
                user_text = message["text"]["body"]
                reply = find_reply(user_text)
                send_whatsapp_message(from_number, reply)
    except (KeyError, IndexError) as e:
        print("No message content to process:", e)
    return jsonify({"status": "ok"}), 200


@app.route("/", methods=["GET"])
def home():
    return "بوت دليل سوق السجانة شغال ✅"


if name == "main":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
