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
from apps.Bot.translations import t

logger = logging.getLogger(__name__)

# ── Tarjimalar ────────────────────────────────────────────────────────────────

# Eski TEXTS va STATUS_LABELS o'rniga translations.py dan foydalanamiz
# Lekin t() funksiyasiga o'tishda biroz vaqt kerak, shuning uchun avval ularni saqlab qolamiz

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

    return t("profile_title", lang,
        patient_id=user.patient_id,
        first_name=user.first_name or '—',
        date_joined=date_str,
        bonus_points=user.bonus_points,
        count=count,
        completed=completed,
        bar=bar,
        next_free=next_free
    )


# ── Handlerlar ────────────────────────────────────────────────────────────────

async def handle_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """👤 Profil ma'lumotlari."""
    user_id = update.effective_user.id
    user = await get_db_user(user_id)
    
    if not user:
        await update.effective_message.reply_text(t("profile_no_user", "uz"))
        return

    lang = user.lang or "uz"
    orders = await get_user_orders(user_id)
    text   = build_profile_text(user, orders, lang)

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t("btn_results", lang), callback_data="my_results"),
            InlineKeyboardButton(t("btn_order_status", lang), callback_data="order_status"),
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
        await update.effective_message.reply_text(t("profile_no_results", lang), parse_mode="HTML")
        return

    await update.effective_message.reply_text(
        t("profile_results_header", lang, count=len(results[:5])),
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
        await update.effective_message.reply_text(t("profile_no_orders", lang), parse_mode="HTML")
        return

    sep   = "━━━━━━━━━━━━━━━━━━"
    lines = [t("profile_orders_header", lang, count=len(orders[:5]))]

    for o in orders[:5]:
        label = t(f"status_{o['status']}", lang)
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