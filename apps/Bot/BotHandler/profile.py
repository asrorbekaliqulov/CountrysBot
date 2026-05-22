"""
handlers/profile.py
────────────────────
👤 Profil  |  📊 Natijalar  |  🚚 Buyurtma holati
Django ORM + python-telegram-bot v20+
"""

import logging
from asgiref.sync import sync_to_async

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from apps.Bot.models.TelegramBot import TelegramUser
from apps.Bot.models.orders import Order, TestResult  # Yangi model qo'shildi

logger = logging.getLogger(__name__)

# ── Tarjimalar ────────────────────────────────────────────────────────────────

TEXTS = {
    "no_results": {
        "uz": "📭 Hozircha natijalar mavjud emas.\nTahlil buyurtma bering va natijangiz bu yerda chiqadi.",
        "ru": "📭 Результатов пока нет.\nОформите заказ — результаты появятся здесь.",
        "en": "📭 No results yet.\nPlace an order and your results will appear here.",
    },
    "no_orders": {
        "uz": "📭 Hozircha buyurtmalar yo'q.\nBirinchi buyurtmangizni bering! 🎉",
        "ru": "📭 Заказов пока нет.\nОформите первый заказ! 🎉",
        "en": "📭 No orders yet.\nPlace your first order! 🎉",
    },
    "btn_results": {"uz": "📊 Natijalarim",   "ru": "📊 Мои результаты", "en": "📊 My results"},
    "btn_status":  {"uz": "🚚 Buyurtma holati","ru": "🚚 Статус заказа",  "en": "🚚 Order status"},
    "results_header": {
        "uz": "📊 <b>Tahlil natijalari</b>\n\nSo'nggi {count} ta natija:",
        "ru": "📊 <b>Результаты анализов</b>\n\nПоследние {count} результатов:",
        "en": "📊 <b>Analysis Results</b>\n\nLatest {count} results:",
    },
    "status_header": {
        "uz": "🚚 <b>Buyurtmalar holati</b>\n\nSo'nggi {count} ta buyurtma:",
        "ru": "🚚 <b>Статус заказов</b>\n\nПоследние {count} заказов:",
        "en": "🚚 <b>Order Status</b>\n\nLatest {count} orders:",
    },
}

STATUS_LABELS = {
    "pending":    {"uz": "⏳ Kutilmoqda",       "ru": "⏳ Ожидает",         "en": "⏳ Pending"},
    "paid":       {"uz": "💳 To'langan",         "ru": "💳 Оплачен",         "en": "💳 Paid"},
    "delivering": {"uz": "🚚 Kuryer yo'lda",     "ru": "🚚 Курьер едет",     "en": "🚚 On the way"},
    "done":       {"uz": "✅ Yetkazildi",         "ru": "✅ Доставлено",       "en": "✅ Delivered"},
    "canceled":   {"uz": "❌ Bekor qilindi",      "ru": "❌ Отменён",          "en": "❌ Cancelled"},
}


def t(key: str, lang: str, **kwargs) -> str:
    val = TEXTS.get(key, {}).get(lang) or TEXTS.get(key, {}).get("uz", key)
    return val.format(**kwargs) if kwargs else val


def status_label(status: str, lang: str) -> str:
    return STATUS_LABELS.get(status, {}).get(lang, status)


# ── Django ORM ────────────────────────────────────────────────────────────────

@sync_to_async
def get_db_user(tg_id: int) -> TelegramUser | None:
    try:
        return TelegramUser.objects.get(user_id=tg_id)
    except TelegramUser.DoesNotExist:
        return None


@sync_to_async
def get_user_orders(tg_id: int) -> list[dict]:
    """Foydalanuvchining so'nggi 10 ta buyurtmasini TestResult bilan birga oladi."""
    qs = (
        Order.objects
        .filter(user__user_id=tg_id)
        .select_related("service", "payment", "test_result") # test_result ulandi
        .order_by("-created_at")[:10]
    )
    result = []
    for o in qs:
        # TestResult modeli borligini va fayli yuklanganini tekshiramiz
        has_result = hasattr(o, 'test_result') and bool(o.test_result.result_file)
        
        result.append({
            "id":             o.pk,
            "service_name":   o.service.name_uz if o.service else "—",
            "status":         o.status,
            "created_at":     o.created_at.strftime("%Y-%m-%d") if o.created_at else "—",
            "total_price":    float(o.total_price or 0),
            "has_result":     has_result,
            # Fayl obyektini keyinchalik bot orqali jo'natish uchun saqlaymiz
            "result_file":    o.test_result.result_file if has_result else None,
            "doctor_comment": o.test_result.doctor_conclusion if has_result else None,
        })
    return result


# ── Profil matni ──────────────────────────────────────────────────────────────

def build_profile_text(user: TelegramUser, orders: list[dict], lang: str) -> str:
    count     = len(orders)
    completed = sum(1 for o in orders if o["status"] == "done")
    cycle_pos = user.order_count % 6
    next_free = 6 - cycle_pos if cycle_pos != 0 else 6
    bar       = "🟦" * cycle_pos + "⬜" * (6 - cycle_pos)

    date_str = user.date_joined.strftime("%Y-%m-%d") if user.date_joined else "—"

    body = {
        "uz": (
            f"<b>👤 SHAXSIY PROFIL</b>\n\n"
            f"🆔 ID: <code>{user.patient_id}</code>\n"
            f"📛 Ism: {user.first_name or '—'}\n"
            f"📅 Ro'yxatdan o'tgan: {date_str}\n"
            f"⭐️ Bonuslar: {user.bonus_points} ball\n\n"
            f"<b>Buyurtmalar holati:</b>\n"
            f"└ Jami: {count} ta\n"
            f"└ Yakunlangan: {completed} ta\n\n"
            f"<b>🎁 Har 6-chi buyurtma bepul!</b>\n"
            f"{bar}\n"
            f"💡 Yana <b>{next_free} ta</b> buyurtmadan keyin keyingisi bepul."
        ),
        "ru": (
            f"<b>👤 МОЙ ПРОФИЛЬ</b>\n\n"
            f"🆔 ID: <code>{user.patient_id}</code>\n"
            f"📛 Имя: {user.first_name or '—'}\n"
            f"📅 Дата регистрации: {date_str}\n"
            f"⭐️ Бонусы: {user.bonus_points} баллов\n\n"
            f"<b>Статус заказов:</b>\n"
            f"└ Всего: {count}\n"
            f"└ Выполнено: {completed}\n\n"
            f"<b>🎁 Каждый 6-й заказ бесплатно!</b>\n"
            f"{bar}\n"
            f"💡 Ещё <b>{next_free}</b> заказов до бесплатного."
        ),
        "en": (
            f"<b>👤 MY PROFILE</b>\n\n"
            f"🆔 ID: <code>{user.patient_id}</code>\n"
            f"📛 Name: {user.first_name or '—'}\n"
            f"📅 Joined: {date_str}\n"
            f"⭐️ Bonus points: {user.bonus_points}\n\n"
            f"<b>Order stats:</b>\n"
            f"└ Total: {count}\n"
            f"└ Completed: {completed}\n\n"
            f"<b>🎁 Every 6th order is FREE!</b>\n"
            f"{bar}\n"
            f"💡 <b>{next_free}</b> more orders until your free one."
        ),
    }
    return body.get(lang, body["uz"])


# ── Handlerlar ────────────────────────────────────────────────────────────────

async def handle_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """👤 Profil ma'lumotlari."""
    user_id = update.effective_user.id
    user = await get_db_user(user_id)
    
    if not user:
        await update.effective_message.reply_text("❌ Foydalanuvchi topilmadi.")
        return

    lang = user.lang or "uz"
    orders = await get_user_orders(user_id)
    text   = build_profile_text(user, orders, lang)

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t("btn_results", lang), callback_data="my_results"),
            InlineKeyboardButton(t("btn_status",  lang), callback_data="order_status"),
        ]
    ])
    await update.effective_message.reply_text(text, reply_markup=kb, parse_mode="HTML")


async def handle_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📊 Tahlil natijalarini yuboradi (TestResult dagi faylni oladi)."""
    # 1. tg_id va lang ni to'g'ridan-to'g'ri obyektdan olamiz
    tg_id = update.effective_user.id
    user = await get_db_user(tg_id)
    lang = user.lang if user else "uz"

    orders  = await get_user_orders(tg_id)
    # has_result True bo'lganlarini filtrlaymiz
    results = [o for o in orders if o["has_result"]]

    if not results:
        await update.effective_message.reply_text(t("no_results", lang), parse_mode="HTML")
        return

    await update.effective_message.reply_text(
        t("results_header", lang, count=len(results[:5])),
        parse_mode="HTML"
    )

    for o in results[:5]:
        caption = (
            f"📊 <b>Buyurtma:</b> <code>#{o['id']}</code>\n"
            f"🩺 <b>Tahlil:</b> {o['service_name']}\n"
            f"📅 <b>Sana:</b> {o['created_at']}"
        )
        if o["doctor_comment"]:
            caption += f"\n\n👨‍⚕️ <b>Shifokor xulosasi:</b>\n<i>{o['doctor_comment']}</i>"

        try:
            # Fayl turini aniqlaymiz (agar rasm bo'lsa send_photo, aks holda hujjat qilib send_document)
            file_path = o["result_file"].path
            
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                await context.bot.send_photo(
                    chat_id=tg_id,
                    photo=open(file_path, 'rb'),
                    caption=caption,
                    parse_mode="HTML",
                )
            else:
                await context.bot.send_document(
                    chat_id=tg_id,
                    document=open(file_path, 'rb'),
                    caption=caption,
                    parse_mode="HTML",
                )
        except Exception as e:
            logger.error(f"Natija faylini yuborishda xato (order #{o['id']}): {e}")


async def handle_order_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🚚 So'nggi buyurtmalar holati."""
    # 1. tg_id va lang ni to'g'ridan-to'g'ri obyektdan olamiz
    tg_id = update.effective_user.id
    user = await get_db_user(tg_id)
    lang = user.lang if user else "uz"

    orders = await get_user_orders(tg_id)

    if not orders:
        await update.effective_message.reply_text(t("no_orders", lang), parse_mode="HTML")
        return

    sep   = "━━━━━━━━━━━━━━━━━━"
    lines = [t("status_header", lang, count=len(orders[:5]))]

    for o in orders[:5]:
        label = status_label(o["status"], lang)
        price = f"{o['total_price']:,.0f} so'm" if o["total_price"] else "—"
        lines.append(
            f"\n{sep}\n"
            f"🔖 <code>#{o['id']}</code>\n"
            f"🩺 {o['service_name']}\n"
            f"💰 {price}\n"
            f"{label}\n"
            f"📅 {o['created_at']}"
        )

    await update.effective_message.reply_text("\n".join(lines), parse_mode="HTML")