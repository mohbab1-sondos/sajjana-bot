"""
سكريبت لتحديث أسماء التجار الأساسيين الموجودين بالفعل في traders.json
شغّله مرة واحدة بس من الكونسول: python3 rename_seed_traders.py
"""
from app import get_traders, save_traders

RENAMES = {
    "966562762669": "حسين",   # كان هنادي (سيراميك)
    "249918213703": "سامي",   # كان سحر (اسمنت)
    "249927382171": "شوقي",   # كان شروق (كهرباء)
}


def main():
    traders = get_traders()
    changed = 0
    for t in traders:
        phone = t.get("whatsapp")
        if phone in RENAMES:
            old_name = t.get("name")
            t["name"] = RENAMES[phone]
            print(f"تم تغيير: {old_name} -> {RENAMES[phone]} ({phone})")
            changed += 1
    save_traders(traders)
    print(f"\nتم تحديث {changed} تاجر بنجاح.")


if __name__ == "__main__":
    main()
