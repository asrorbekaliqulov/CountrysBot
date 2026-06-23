# Ko'p tillilik qo'llanmasi (Multilingual Guide)

## 📋 Umumiy ma'lumot

CountrysBot loyihasi endi **3 tilda** ishlaydi:
- 🇺🇿 **O'zbek** (uz) - Asosiy til
- 🇷🇺 **Русский** (ru) - Rus tili
- 🇬🇧 **English** (en) - Ingliz tili

## 🎯 Qanday ishlaydi?

### 1. Backend (Python/Django/Telegram Bot)

#### Markazlashtirilgan tarjima tizimi

Barcha tarjimalar `apps/Bot/translations.py` faylida joylashgan:

```python
from apps.Bot.translations import t

# Foydalanish
text = t("welcome", lang="uz")  # O'zbek tilida
text = t("welcome", lang="ru")  # Rus tilida
text = t("welcome", lang="en")  # Ingliz tilida

# Format bilan
text = t("profile_title", lang="uz", 
    patient_id="MED-123456",
    bonus_points=100
)
```

#### Foydalanuvchi tili

Har bir foydalanuvchi o'z tilini tanlaydi:
- Birinchi marta /start bosganida til tanlash oynasi chiqadi
- Til `TelegramUser.lang` maydonida saqlanadi
- Barcha xabarlar foydalanuvchi tilida yuboriladi

### 2. Frontend (HTML/JavaScript)

#### WebApp (app.html)

WebApp da `nmed-i18n.js` fayli orqali tarjimalar amalga oshiriladi:

```javascript
// HTML da
<h1 data-i18n="welcome_title">Xush kelibsiz</h1>
<button data-i18n="order_btn">Buyurtma berish</button>

// JavaScript
NMED.setLanguage('ru');  // Tilni o'zgartirish
```

#### Kuryer Panel (courier_panel.html)

Kuryer panelida tillar JavaScript o'zgaruvchilari orqali boshqariladi.

#### Admin Panel (admin_panel.html)

Admin panelda tillar URL parametr orqali uzatiladi:
`/api/admin-panel?tg_id=123&lang=uz`

## 📁 Fayl tuzilmasi

```
CountrysBot/
├── apps/Bot/
│   ├── translations.py          # Markazlashtirilgan tarjimalar
│   ├── BotHandler/
│   │   ├── BotStats.py          # ✅ Ko'p tillilik qo'shildi
│   │   ├── SendMessage.py       # ✅ Ko'p tillilik qo'shildi
│   │   ├── Feedback.py          # ✅ Ko'p tillilik qo'shildi
│   │   ├── Guide.py             # ✅ Ko'p tillilik qo'shildi
│   │   ├── Support.py           # ✅ Ko'p tillilik qo'shildi
│   │   └── profile.py           # ✅ Ko'p tillilik qo'shildi
│   ├── BotCommands/
│   │   └── StartCommand.py      # ✅ Til tanlash mexanizmi
│   └── BotAdmin/
│       └── AddAdmin.py          # ✅ Ko'p tillilik qo'shildi
└── assets/
    ├── templates/
    │   ├── webapp/app.html      # WebApp template
    │   ├── courier_panel.html   # Kuryer panel
    │   └── admin/admin_panel.html
    └── static/js/
        └── nmed-i18n.js         # Frontend tarjimalar
```

## 🔧 Yangi tarjima qo'shish

### Backend uchun

`apps/Bot/translations.py` fayliga qo'shing:

```python
TRANSLATIONS = {
    "yangi_kalit": {
        "uz": "O'zbek tilidagi matn",
        "ru": "Текст на русском",
        "en": "Text in English"
    },
}
```

### Frontend uchun

`assets/static/js/nmed-i18n.js` fayliga qo'shing:

```javascript
const TRANSLATIONS = {
    uz: {
        "yangi_kalit": "O'zbek tilidagi matn"
    },
    ru: {
        "yangi_kalit": "Текст на русском"
    },
    en: {
        "yangi_kalit": "Text in English"
    }
};
```

## ✅ Bajarilgan ishlar

1. ✅ Markazlashtirilgan tarjima tizimi yaratildi
2. ✅ Barcha bot handlerlar ko'p tillilikka o'tkazildi
3. ✅ Admin funksiyalari tarjima qilindi
4. ✅ Profil va natijalar 3 tilda
5. ✅ Feedback va Support 3 tilda
6. ✅ Til tanlash mexanizmi ishlaydi

## 📝 Eslatmalar

- Barcha yangi xabarlar `translations.py` ga qo'shilishi kerak
- Frontend tillarni URL parametr orqali oladi: `?lang=uz`
- Database da Guide va boshqa content lar har bir tilda alohida yaratilishi kerak
- Telegram bot avtomatik ravishda foydalanuvchi tilini aniqlaydi

## 🐛 Ma'lum muammolar va yechimlar

### Muammo: Til saqlanmayapti
**Yechim**: `/start` commandasini qayta ishga tushiring

### Muammo: Frontend tilni o'zgartirmayapti
**Yechim**: URL da `lang` parametrini tekshiring

### Muammo: Yangi tarjima ko'rinmayapti
**Yechim**: Serverni qayta ishga tushiring (Telegram bot restart)

## 🚀 Keyingi qadamlar

1. Frontend i18n.js fayllarini to'ldirish
2. Barcha HTML templatelarni tekshirish
3. Test yozish har bir til uchun
4. Django admin panel uchun gettext() qo'shish

## 📞 Yordam

Savollar bo'lsa:
- Telegram: @support
- GitHub: Repository Issues bo'limi
