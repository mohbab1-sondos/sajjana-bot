"""
سكريبت لاستيراد التجار المجمّعين من السوشيال ميديا كتسجيلات "قيد المراجعة"
شغّله مرة واحدة بس من الكونسول: python3 import_collected_traders.py
"""
import uuid
from datetime import date

from app import get_traders, save_traders, specialty_to_category_id

COLLECTED = [
    {
        "name": "شركة جبوري الهندسية",
        "whatsapp": "249910800025",
        "specialty": "أخرى",
        "location": "مقابل بنك النيل، السجانة",
        "details": "مواد بناء عامة",
        "notes": "المصدر: تليجرام السجانة دوت كوم — يحتاج اتصال للتأكيد",
    },
    {
        "name": "تاجر مواد بناء (يحتاج تأكيد الاسم)",
        "whatsapp": "249923916431",
        "specialty": "أخرى",
        "location": "السجانة",
        "details": "مواد بناء",
        "notes": "اسم التاجر غير واضح من المصدر — أكّد قبل الموافقة",
    },
    {
        "name": "تاجر مواد بناء (يحتاج تأكيد الاسم)",
        "whatsapp": "249127679999",
        "specialty": "أخرى",
        "location": "السجانة",
        "details": "مواد بناء",
        "notes": "اسم التاجر غير واضح من المصدر — أكّد قبل الموافقة",
    },
    {
        "name": "وكيل: أحمد عبد القيوم",
        "whatsapp": "249912376621",
        "specialty": "اسمنت",
        "location": "شارع السيخ الرئيسي، السجانة",
        "details": "اسمنت",
        "notes": "رقم إضافي (مكتب): 0117770086",
    },
    {
        "name": "تاجر حجر تجليد (يحتاج تأكيد الاسم)",
        "whatsapp": "249912335793",
        "specialty": "اسمنت",
        "location": "السجانة",
        "details": "اسمنت، حجر تجليد",
        "notes": "اسم التاجر غير واضح — أكّد قبل الموافقة",
    },
    {
        "name": "مكتب الحلفايا (طوب حراري)",
        "whatsapp": "249912334246",
        "specialty": "أخرى",
        "location": "بحري / أمدرمان",
        "details": "طوب حراري",
        "notes": "فرع بحري وأمدرمان — ممكن تعمل تخصص \"طوب\" منفصل لاحقاً",
    },
    {
        "name": "مكتب الخرطوم (طوب حراري)",
        "whatsapp": "249901232445",
        "specialty": "أخرى",
        "location": "الخرطوم",
        "details": "طوب حراري",
        "notes": "أرقام إضافية: 0912324460 / 0901232446",
    },
    {
        "name": "تاجر اسمنت وحديد (يحتاج تأكيد الاسم)",
        "whatsapp": "249119999923",
        "specialty": "اسمنت",
        "location": "السجانة",
        "details": "اسمنت، حديد",
        "notes": "أرقام إضافية: 0114299999 / 0909993688",
    },
    {
        "name": "تاجر كيبلات كهرباء (يحتاج تأكيد الاسم)",
        "whatsapp": "249900516321",
        "specialty": "كهرباء",
        "location": "السجانة، الخرطوم",
        "details": "كيبلات كهرباء",
        "notes": "المصدر: فيسبوك — أسعار مواد البناء",
    },
    {
        "name": "محمد - معرض الفاخر",
        "whatsapp": "249921037650",
        "specialty": "أخرى",
        "location": "السجانة",
        "details": "غير محدد — يحتاج تأكيد التخصص عند الاتصال",
        "notes": "",
    },
    {
        "name": "تاجر اسمنت ورملة وسقالة (يحتاج تأكيد الاسم)",
        "whatsapp": "249111111080",
        "specialty": "اسمنت",
        "location": "السجانة",
        "details": "اسمنت، رملة، سقالة",
        "notes": "",
    },
    {
        "name": "بيراميدز - أدوات سيراميك",
        "whatsapp": "249112101229",
        "specialty": "سيراميك",
        "location": "السجانة، شمال سوق الخضار",
        "details": "أدوات تركيب سيراميك",
        "notes": "رقم إضافي: 0918554069 — المصدر: تيك توك",
    },
    {
        "name": "شركة كهرباء وسباكة (م.أحمد، م.منير، م.يسرا، م.سوزان)",
        "whatsapp": "249912983234",
        "specialty": "كهرباء",
        "location": "السوق العربي، شارع البرلمان، عمارة كشة 2",
        "details": "كهرباء، سباكة",
        "notes": "مكتب كامل بعدة موظفين متخصصين — أرقام إضافية: 0123561111/1122/1133/1155",
    },
    {
        "name": "تاجر طبلونات وتمديدات كهرباء (يحتاج تأكيد الاسم)",
        "whatsapp": "249125299999",
        "specialty": "كهرباء",
        "location": "غرب بنك أمدرمان الوطني، جوار ميدان المولد",
        "details": "طبلونات، تمديدات كهرباء",
        "notes": "أرقام إضافية: 0118929999 / 0118939999",
    },
]


def main():
    traders = get_traders()
    added = 0
    for entry in COLLECTED:
        new_trader = {
            "id": "t" + uuid.uuid4().hex[:8],
            "name": entry["name"],
            "whatsapp": entry["whatsapp"],
            "category_id": specialty_to_category_id(entry["specialty"]),
            "location": entry["location"],
            "details": entry["details"],
            "notes": entry["notes"],
            "status": "pending",
            "visibility": "normal",
            "submitted_at": str(date.today()),
        }
        traders.append(new_trader)
        added += 1
    save_traders(traders)
    print(f"تم إضافة {added} تاجر كتسجيلات قيد المراجعة.")
    print("راجعهم من: mohbab.pythonanywhere.com/admin?key=YOUR_KEY")


if __name__ == "__main__":
    main()
