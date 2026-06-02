from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import CallbackContext, ConversationHandler, ContextTypes
from ..decorators import admin_required
from apps.Bot.models.TelegramBot import TelegramUser, Channel
from apps.Bot.models.bot import District, Region, BotSetting
from apps.Bot.models.orders import Order, Payment, Service
import os
from asgiref.sync import sync_to_async


WEB_APP_URL = os.getenv("WEB_APP_URL", "https://n-medhomelab.uz/")

def _lang(context: ContextTypes.DEFAULT_TYPE, fallback: str = "uz") -> str:
    try:
        return context.user_data.get("lang", fallback) or fallback
    except Exception:
        return fallback


async def _get_user_lang(tg_id: int) -> str:
    try:
        user = await sync_to_async(TelegramUser.objects.get)(user_id=tg_id)
        return user.lang or "uz"
    except TelegramUser.DoesNotExist:
        return "uz"


@admin_required
async def admin_menyu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """Asosiy admin menyu — WebApp + inline tugmalar."""
    tg_id           = update.effective_user.id
    lang            = await _get_user_lang(tg_id)
    webapp_url      = f"{WEB_APP_URL}api/admin-panel?tg_id={tg_id}&lang={lang}"
    pending_url     = f"{WEB_APP_URL}api/admin-panel?tg_id={tg_id}&lang={lang}&tab=pending"

    # Kutilayotgan buyurtmalar soni (badge uchun)
    pending_count = await sync_to_async(
        Order.objects.filter(status="pending").count
    )()
    pending_label = (
        f"💳 Kutilayotgan to'lovlar ({pending_count})"
        if pending_count else "💳 Kutilayotgan to'lovlar"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛠 Admin panelni ochish",  web_app=WebAppInfo(url=webapp_url))],
        [InlineKeyboardButton(pending_label,             web_app=WebAppInfo(url=pending_url))],
        # [
        #     InlineKeyboardButton("⚙️ Sozlamalar",     callback_data="admin_settings"),
        #     InlineKeyboardButton("👥 Xodimlar",       callback_data="admin_users"),
        # ],
        [
            InlineKeyboardButton("📊 Bot Statistikasi",     callback_data="botstats"),
            InlineKeyboardButton("📣 Xabar yuborish", callback_data="send_messages"),
        ],
        # [
        #     InlineKeyboardButton("📦 Buyurtmalar",    callback_data="admin_orders"),
        #     InlineKeyboardButton("📍 Faol tumanlar",  callback_data="admin_districts"),
        # ],
    ])

    text = "🛠 <b>Admin boshqaruv paneli</b>"
    msg = update.effective_message
    if msg:
        await msg.reply_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await context.bot.send_message(tg_id, text, reply_markup=kb, parse_mode="HTML")



admin_keyboard_list = [
    [
        InlineKeyboardButton(text="📨 Xabar yuborish", callback_data='send_messages'),
        InlineKeyboardButton(text="📊 Bot statistikasi", callback_data='botstats')
    ],
    [
        InlineKeyboardButton(text="👮‍♂️ Admin qo'shish", callback_data='add_admin'),
        InlineKeyboardButton(text="🙅‍♂️ Admin o'chirish", callback_data='delete_admin')
    ],
    [
        InlineKeyboardButton(text="🗒 Adminlar yo'yxati", callback_data="admin_list")
    ],
    [
        InlineKeyboardButton(text="📢 Majburiy Kanal/Guruh qo'shish", callback_data="Add_mandatory"),
        InlineKeyboardButton(text="🔴 Majburiy Kanal/Guruh o'chirish", callback_data="Del_mandatory")
    ],
    [
        InlineKeyboardButton(text="🗒 Kanal/Guruh ro'yxati", callback_data="mandatory_channel")
    ],
    [
        InlineKeyboardButton(text="Qo'llanma", callback_data="AdminGuide"),
        InlineKeyboardButton(text="📞 Murojaatlar", callback_data="AdminAppeal")
    ]
]
Admin_keyboard = InlineKeyboardMarkup(admin_keyboard_list)

# @admin_required
# async def admin_menyu(update: Update, context: CallbackContext):
#     user_id = update.effective_user.id
#     await context.bot.send_message(
#         chat_id=user_id, 
#         text="<b>Salom Admin\nNima qilamiz bugun</b>", 
#         parse_mode="HTML",
#         reply_markup=Admin_keyboard
#         )
#     return ConversationHandler.END


# """
# Admin panel handler — Django ORM versiyasi
# ==========================================
# Fayl: apps/Bot/handlers/admin_panel.py

# Ulash (handlers/__init__.py yoki main bot faylida):
#     from .admin_panel import (
#         send_admin_panel,
#         handle_admin_callback,
#         handle_admin_text,
#         handle_admin_photo,
#         ADMIN_CALLBACK_PATTERN,
#     )

#     app.add_handler(CallbackQueryHandler(handle_admin_callback, pattern=ADMIN_CALLBACK_PATTERN))
#     app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_text))
#     app.add_handler(MessageHandler(filters.PHOTO, handle_admin_photo))
# """

# import os
# from datetime import date, timedelta

# from asgiref.sync import sync_to_async
# from telegram import (
#     InlineKeyboardButton,
#     InlineKeyboardMarkup,
#     KeyboardButton,
#     KeyboardButtonRequestUsers,
#     ReplyKeyboardMarkup,
#     ReplyKeyboardRemove,
#     Update,
#     WebAppInfo,
# )
# from telegram.ext import ContextTypes

# # Django modellari

# # ─── Sozlamalar ───────────────────────────────────────────────────────────────

# # Barcha admin callback_data lar shu pattern bilan tutiladi
# ADMIN_CALLBACK_PATTERN = (
#     r"^(admin_panel|admin_settings|admin_toggle_sub|admin_change_channel|"
#     r"admin_set_price|admin_set_extra|admin_set_card|admin_set_owner|"
#     r"admin_set_click_url|admin_set_instruction|admin_users|admin_add_admin|"
#     r"admin_add_courier|admin_add_doctor|admin_list_couriers|admin_list_doctors|"
#     r"admin_stats|admin_orders|admin_orders_page_\d+|admin_districts|"
#     r"admin_edit_districts|admin_ad|admin_broadcast_text|admin_broadcast_photo|"
#     r"admin_back|admin_approve_\d+|admin_reject_\d+|"
#     r"admin_region_courier_\d+_\d+|admin_remove_staff_\d+)$"
# )


# # ─── Yordamchi: til kodi ─────────────────────────────────────────────────────


# # ─── Admin tekshiruv decorator ───────────────────────────────────────────────
# async def _is_admin(tg_id: int) -> bool:
#     try:
#         user = await sync_to_async(TelegramUser.objects.get)(user_id=tg_id)
#         return user.is_admin or user.role == "admin"
#     except TelegramUser.DoesNotExist:
#         return False


# # ─── BotSetting yordamchi funksiyalari (async) ───────────────────────────────
# async def _get_setting(key: str, default: str = "") -> str:
#     return await sync_to_async(BotSetting.get)(key, default)


# async def _set_setting(key: str, value: str) -> None:
#     await sync_to_async(BotSetting.set)(key, value)


# # ═══════════════════════════════════════════════════════════════════════════════
# #  ASOSIY ADMIN PANEL
# # ═══════════════════════════════════════════════════════════════════════════════

# # ═══════════════════════════════════════════════════════════════════════════════
# #  ASOSIY CALLBACK ROUTER
# # ═══════════════════════════════════════════════════════════════════════════════
# async def handle_admin_callback(
#     update: Update,
#     context: ContextTypes.DEFAULT_TYPE,
# ):
#     query = update.callback_query
#     await query.answer()
#     tg_id = query.from_user.id

#     if not await _is_admin(tg_id):
#         await query.answer("⛔ Ruxsat yo'q!", show_alert=True)
#         return

#     data = query.data
#     lang = await _get_user_lang(tg_id)

#     # ── Sozlamalar ────────────────────────────────────────────────────────────
#     if data == "admin_settings":
#         await _show_settings(query, lang)

#     elif data == "admin_toggle_sub":
#         await _toggle_sub(update, context, query, lang)

#     elif data == "admin_change_channel":
#         context.user_data["admin_step"] = "set_channel"
#         await query.message.reply_text(
#             "📣 Yangi kanal ID ni yozing:\n📌 Masalan: <code>@kanal_nomi</code> yoki <code>-1001234567890</code>",
#             parse_mode="HTML",
#         )

#     elif data == "admin_set_price":
#         context.user_data["admin_step"] = "set_price"
#         cur = await _get_setting("service_price", "0")
#         await query.message.reply_text(
#             f"💰 Joriy narx: <b>{int(cur):,} so'm</b>\n\nYangi xizmat narxini <b>so'mda</b> kiriting:",
#             parse_mode="HTML",
#         )

#     elif data == "admin_set_extra":
#         context.user_data["admin_step"] = "set_extra"
#         cur = await _get_setting("pickup_extra", "0")
#         await query.message.reply_text(
#             f"🚚 Joriy pickup extra: <b>{int(cur):,} so'm</b>\n\nYangi summa kiriting:",
#             parse_mode="HTML",
#         )

#     elif data == "admin_set_card":
#         context.user_data["admin_step"] = "set_card"
#         await query.message.reply_text("💳 Yangi karta raqamini kiriting:")

#     elif data == "admin_set_owner":
#         context.user_data["admin_step"] = "set_owner"
#         await query.message.reply_text("👤 Karta egasining to'liq ismini kiriting:")

#     elif data == "admin_set_click_url":
#         context.user_data["admin_step"] = "set_click_url"
#         await query.message.reply_text(
#             "🔗 Click to'lov URL ni kiriting:\n📌 Masalan: <code>https://my.click.uz/services/pay?service_id=12345</code>",
#             parse_mode="HTML",
#         )

#     elif data == "admin_set_instruction":
#         context.user_data["admin_step"] = "waiting_instruction"
#         await query.message.reply_text("📋 Ko'rsatma faylni yuboring (rasm, video yoki hujjat):")

#     # ── Statistika ────────────────────────────────────────────────────────────
#     elif data == "admin_stats":
#         await _show_stats(query)

#     # ── Buyurtmalar ───────────────────────────────────────────────────────────
#     elif data == "admin_orders" or data.startswith("admin_orders_page_"):
#         page = 0
#         if data.startswith("admin_orders_page_"):
#             page = int(data.split("_")[-1])
#         await _show_orders(query, context, tg_id, lang, page)

#     elif data.startswith("admin_approve_"):
#         order_id = int(data[len("admin_approve_"):])
#         await _approve_order(update, context, query, order_id, lang)

#     elif data.startswith("admin_reject_"):
#         order_id = int(data[len("admin_reject_"):])
#         await _reject_order(update, context, query, order_id, lang)

#     # ── Tumanlar ──────────────────────────────────────────────────────────────
#     elif data == "admin_districts":
#         await _show_districts(query)

#     elif data == "admin_edit_districts":
#         context.user_data["admin_step"] = "set_allowed_regions"
#         # Barcha tumanlar ro'yxatini ham chiqaramiz
#         all_districts = await sync_to_async(
#             lambda: list(District.objects.filter(is_active=True).values_list("id", "name"))
#         )()
#         district_list = "\n".join(f"  <code>{d[0]}</code> — {d[1]}" for d in all_districts[:30])
#         await query.message.reply_text(
#             f"📍 Faol tuman ID larini <b>vergul bilan</b> yozing:\n\n"
#             f"Masalan: <code>1,2,5,8</code>\n\n"
#             f"<b>Mavjud tumanlar (ID — Nomi):</b>\n{district_list}",
#             parse_mode="HTML",
#         )

#     # ── Xodimlar ─────────────────────────────────────────────────────────────
#     elif data == "admin_users":
#         await _show_staff_menu(query)

#     elif data in ("admin_add_admin", "admin_add_courier", "admin_add_doctor"):
#         role_map = {
#             "admin_add_admin":   "admin",
#             "admin_add_courier": "courier",
#             "admin_add_doctor":  "doctor",
#         }
#         await _show_user_selector(update, context, tg_id, role_map[data])

#     elif data == "admin_list_couriers":
#         await _list_staff(query, "courier", "🚗 Kuryerlar")

#     elif data == "admin_list_doctors":
#         await _list_staff(query, "doctor", "👨‍⚕️ Shifokorlar")

#     elif data.startswith("admin_remove_staff_"):
#         uid = int(data[len("admin_remove_staff_"):])
#         await _remove_staff(query, uid)

#     elif data.startswith("admin_region_courier_"):
#         # format: admin_region_courier_{courier_tg_id}_{district_id}
#         parts = data.split("_")
#         district_id = int(parts[-1])
#         courier_tg_id = int(parts[-2])
#         await _assign_courier_district(query, courier_tg_id, district_id, context, tg_id)

#     # ── Xabar yuborish ────────────────────────────────────────────────────────
#     elif data == "admin_ad":
#         await _show_broadcast_menu(query)

#     elif data == "admin_broadcast_text":
#         context.user_data["admin_step"] = "broadcast_text"
#         await query.message.reply_text(
#             "📝 Barcha foydalanuvchilarga yuboriladigan <b>matni</b> kiriting:\n\n"
#             "HTML teglar qo'llab-quvvatlanadi: <code>&lt;b&gt; &lt;i&gt; &lt;code&gt;</code>",
#             parse_mode="HTML",
#         )

#     elif data == "admin_broadcast_photo":
#         context.user_data["admin_step"] = "broadcast_photo"
#         await query.message.reply_text("🖼 Yubormoqchi bo'lgan <b>rasmni</b> yuboring (caption ixtiyoriy):")

#     # ── Orqaga ────────────────────────────────────────────────────────────────
#     elif data == "admin_back":
#         await send_admin_panel(update, context, tg_id)

#     elif data == "admin_panel":
#         await send_admin_panel(update, context, tg_id)


# # ═══════════════════════════════════════════════════════════════════════════════
# #  SOZLAMALAR
# # ═══════════════════════════════════════════════════════════════════════════════
# async def _show_settings(query, lang: str):
#     service_price = await _get_setting("service_price", "0")
#     pickup_extra  = await _get_setting("pickup_extra", "0")
#     payment_card  = await _get_setting("payment_card", "—")
#     payment_owner = await _get_setting("payment_owner", "—")
#     click_url     = await _get_setting("click_payment_url", "—")
#     mandatory_sub = await _get_setting("mandatory_sub", "1")
#     channel_id    = await _get_setting("channel_id", "—")
#     sub_status    = "✅ Yoqilgan" if mandatory_sub == "1" else "❌ O'chirilgan"

#     kb = InlineKeyboardMarkup([
#         [InlineKeyboardButton(f"📢 Majburiy obuna: {sub_status}", callback_data="admin_toggle_sub")],
#         [InlineKeyboardButton("📣 Kanal ID ni o'zgartirish",      callback_data="admin_change_channel")],
#         [InlineKeyboardButton("💰 Xizmat narxini o'zgartirish",   callback_data="admin_set_price")],
#         [InlineKeyboardButton("🚚 Pickup qo'shimcha narx",        callback_data="admin_set_extra")],
#         [InlineKeyboardButton("💳 Karta raqamini o'zgartirish",   callback_data="admin_set_card")],
#         [InlineKeyboardButton("👤 Karta egasini o'zgartirish",    callback_data="admin_set_owner")],
#         [InlineKeyboardButton("🔗 Click URL ni o'zgartirish",     callback_data="admin_set_click_url")],
#         [InlineKeyboardButton("📋 Ko'rsatma fayl yuklash",        callback_data="admin_set_instruction")],
#         [InlineKeyboardButton("⬅️ Orqaga",                        callback_data="admin_back")],
#     ])

#     await query.message.reply_text(
#         f"⚙️ <b>Joriy sozlamalar:</b>\n\n"
#         f"📢 Majburiy obuna: <b>{sub_status}</b>\n"
#         f"📣 Kanal ID: <code>{channel_id}</code>\n"
#         f"💰 Xizmat narxi: <b>{int(service_price):,} so'm</b>\n"
#         f"🚚 Pickup extra: <b>{int(pickup_extra):,} so'm</b>\n"
#         f"💳 Karta: <code>{payment_card}</code>\n"
#         f"👤 Karta egasi: <b>{payment_owner}</b>\n"
#         f"🔗 Click URL: <code>{click_url[:50] if click_url != '—' else '—'}</code>",
#         reply_markup=kb,
#         parse_mode="HTML",
#     )


# async def _toggle_sub(update, context, query, lang: str):
#     current = await _get_setting("mandatory_sub", "1")
#     new_val = "0" if current == "1" else "1"
#     await _set_setting("mandatory_sub", new_val)
#     status = "yoqildi ✅" if new_val == "1" else "o'chirildi ❌"
#     await query.answer(f"Majburiy obuna {status}", show_alert=True)
#     await _show_settings(query, lang)


# # ═══════════════════════════════════════════════════════════════════════════════
# #  STATISTIKA
# # ═══════════════════════════════════════════════════════════════════════════════
# async def _show_stats(query):
#     today = date.today()
#     week_ago = today - timedelta(days=7)

#     # Parallel so'rovlar (Django ORM async)
#     total_users = await sync_to_async(TelegramUser.objects.count)()

#     total_orders = await sync_to_async(Order.objects.count)()

#     completed = await sync_to_async(
#         Order.objects.filter(status="done").count
#     )()

#     pending_pay = await sync_to_async(
#         Order.objects.filter(status="pending").count
#     )()

#     delivering = await sync_to_async(
#         Order.objects.filter(status="delivering").count
#     )()

#     canceled = await sync_to_async(
#         Order.objects.filter(status="canceled").count
#     )()

#     today_orders = await sync_to_async(
#         Order.objects.filter(created_at__date=today).count
#     )()

#     week_orders = await sync_to_async(
#         Order.objects.filter(created_at__date__gte=week_ago).count
#     )()

#     today_users = await sync_to_async(
#         TelegramUser.objects.filter(date_joined__date=today).count
#     )()

#     # Jami daromad (faqat to'langan buyurtmalar)
#     from django.db.models import Sum
#     revenue_data = await sync_to_async(
#         lambda: Order.objects.filter(status="done").aggregate(total=Sum("total_price"))
#     )()
#     total_revenue = revenue_data.get("total") or 0

#     # Rollar bo'yicha foydalanuvchilar
#     couriers = await sync_to_async(
#         TelegramUser.objects.filter(role="courier").count
#     )()
#     doctors = await sync_to_async(
#         TelegramUser.objects.filter(role="doctor").count
#     )()

#     kb = InlineKeyboardMarkup([
#         [InlineKeyboardButton("🔄 Yangilash", callback_data="admin_stats")],
#         [InlineKeyboardButton("⬅️ Orqaga",   callback_data="admin_back")],
#     ])

#     await query.message.reply_text(
#         f"📊 <b>Bot statistikasi</b>\n"
#         f"━━━━━━━━━━━━━━━━━━━━\n\n"
#         f"👥 <b>Foydalanuvchilar:</b>\n"
#         f"  Jami: <b>{total_users}</b>\n"
#         f"  Bugun yangi: <b>{today_users}</b>\n"
#         f"  Kuryerlar: <b>{couriers}</b>\n"
#         f"  Shifokorlar: <b>{doctors}</b>\n\n"
#         f"📦 <b>Buyurtmalar:</b>\n"
#         f"  Jami: <b>{total_orders}</b>\n"
#         f"  Bugun: <b>{today_orders}</b>\n"
#         f"  7 kunda: <b>{week_orders}</b>\n"
#         f"  ✅ Bajarilgan: <b>{completed}</b>\n"
#         f"  🚚 Yo'lda: <b>{delivering}</b>\n"
#         f"  💳 To'lov kutilmoqda: <b>{pending_pay}</b>\n"
#         f"  ❌ Bekor qilingan: <b>{canceled}</b>\n\n"
#         f"💰 <b>Jami daromad:</b> <b>{int(total_revenue):,} so'm</b>",
#         reply_markup=kb,
#         parse_mode="HTML",
#     )


# # ═══════════════════════════════════════════════════════════════════════════════
# #  BUYURTMALAR
# # ═══════════════════════════════════════════════════════════════════════════════
# async def _show_orders(query, context, tg_id: int, lang: str, page: int = 0):
#     """Aktiv buyurtmalarni sahifalab ko'rsatadi (har sahifada 5 ta)."""
#     PAGE_SIZE = 5

#     total = await sync_to_async(
#         Order.objects.filter(status__in=["pending", "paid", "delivering"]).count
#     )()

#     orders = await sync_to_async(
#         lambda: list(
#             Order.objects.filter(status__in=["pending", "paid", "delivering"])
#             .select_related("user", "service", "district")
#             .order_by("-created_at")[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]
#         )
#     )()

#     if not orders:
#         nav_kb = [[InlineKeyboardButton("⬅️ Orqaga", callback_data="admin_back")]]
#         await query.message.reply_text("📭 Aktiv buyurtmalar yo'q.", reply_markup=InlineKeyboardMarkup(nav_kb))
#         return

#     STATUS_EMOJI = {
#         "pending":    "💳 To'lov kutilmoqda",
#         "paid":       "✅ To'langan",
#         "delivering": "🚚 Yo'lda",
#         "done":       "🎉 Bajarildi",
#         "canceled":   "❌ Bekor qilindi",
#     }

#     for order in orders:
#         status_label = STATUS_EMOJI.get(order.status, order.status)
#         district_name = order.district.name if order.district else "—"
#         service_name  = order.service.name_uz if order.service else "—"
#         user_name     = order.user.first_name if order.user else "—"
#         user_id       = order.user.user_id if order.user else "—"
#         total_price   = int(order.total_price or 0)
#         date_str      = order.created_at.strftime("%Y-%m-%d %H:%M") if order.created_at else "—"

#         text = (
#             f"📋 Buyurtma <code>#{order.id}</code>\n"
#             f"━━━━━━━━━━━━━━━━━━━━\n"
#             f"👤 Bemor: <b>{order.patient_name or user_name}</b>"
#             + (f", {order.patient_age} yosh" if order.patient_age else "") + "\n"
#             f"🩺 Xizmat: {service_name}\n"
#             f"📍 Tuman: {district_name}\n"
#             f"💰 Summa: <b>{total_price:,} so'm</b>\n"
#             f"🔖 Holat: {status_label}\n"
#             f"📅 Sana: {date_str}\n"
#             f"🆔 TG ID: <code>{user_id}</code>"
#         )

#         # Tasdiqlash/Rad tugmalari faqat kutilayotgan buyurtmalar uchun
#         row = []
#         if order.status == "pending":
#             webapp_url = f"{WEB_APP_URL}admin?tg_id={tg_id}&lang={lang}&tab=pending"
#             row = [
#                 InlineKeyboardButton(
#                     "✅ Tasdiqlash",
#                     callback_data=f"admin_approve_{order.id}",
#                 ),
#                 InlineKeyboardButton(
#                     "❌ Rad etish",
#                     callback_data=f"admin_reject_{order.id}",
#                 ),
#             ]
#         elif order.status == "paid":
#             row = [
#                 InlineKeyboardButton(
#                     "🚚 Yo'lga chiqarish",
#                     callback_data=f"admin_approve_{order.id}",
#                 ),
#                 InlineKeyboardButton(
#                     "❌ Bekor qilish",
#                     callback_data=f"admin_reject_{order.id}",
#                 ),
#             ]

#         order_kb = InlineKeyboardMarkup([row]) if row else None
#         await query.message.reply_text(text, reply_markup=order_kb, parse_mode="HTML")

#     # Navigatsiya tugmalari
#     nav_row = []
#     if page > 0:
#         nav_row.append(InlineKeyboardButton("◀️ Oldingi", callback_data=f"admin_orders_page_{page - 1}"))
#     if (page + 1) * PAGE_SIZE < total:
#         nav_row.append(InlineKeyboardButton("▶️ Keyingi", callback_data=f"admin_orders_page_{page + 1}"))

#     nav_kb = []
#     if nav_row:
#         nav_kb.append(nav_row)
#     nav_kb.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="admin_back")])

#     await query.message.reply_text(
#         f"📦 <b>Jami aktiv: {total}</b> | Sahifa: {page + 1}/{max(1, -(-total // PAGE_SIZE))}",
#         reply_markup=InlineKeyboardMarkup(nav_kb),
#         parse_mode="HTML",
#     )


# async def _approve_order(update, context, query, order_id: int, lang: str):
#     """Buyurtmani tasdiqlash va foydalanuvchiga xabar."""
#     try:
#         order = await sync_to_async(
#             Order.objects.select_related("user").get
#         )(id=order_id)
#     except Order.DoesNotExist:
#         await query.answer("❌ Buyurtma topilmadi!", show_alert=True)
#         return

#     # Statusni yangilash
#     new_status = "delivering" if order.status == "paid" else "paid"
#     order.status = new_status
#     await sync_to_async(order.save)(update_fields=["status"])

#     await query.answer("✅ Tasdiqlandi!", show_alert=True)

#     # Foydalanuvchiga xabar
#     if order.user:
#         user_lang = order.user.lang or "uz"
#         msg = {
#             "uz": f"✅ Buyurtmangiz (<code>#{order_id}</code>) tasdiqlandi!\n🚚 Kuryer yo'lda.",
#             "ru": f"✅ Ваш заказ (<code>#{order_id}</code>) подтверждён!\n🚚 Курьер едет.",
#             "en": f"✅ Your order (<code>#{order_id}</code>) is approved!\n🚚 Courier is on the way.",
#         }
#         try:
#             await context.bot.send_message(
#                 order.user.user_id,
#                 msg.get(user_lang, msg["uz"]),
#                 parse_mode="HTML",
#             )
#         except Exception:
#             pass

#     # Eng yaqin kuryer topish va biriktirish
#     if order.district:
#         courier = await sync_to_async(
#             lambda: TelegramUser.objects.filter(
#                 role="courier", district=order.district, is_active=True
#             ).first()
#         )()
#         if courier:
#             try:
#                 await context.bot.send_message(
#                     courier.user_id,
#                     f"🆕 <b>Yangi buyurtma sizga tayinlandi!</b>\n\n"
#                     f"📋 ID: <code>#{order_id}</code>\n"
#                     f"👤 Bemor: {order.patient_name or '—'}\n"
#                     f"📍 Tuman: {order.district.name}\n"
#                     f"🏠 Manzil: {order.address_note or '—'}\n"
#                     f"💰 Summa: {int(order.total_price or 0):,} so'm",
#                     parse_mode="HTML",
#                 )
#             except Exception:
#                 pass


# async def _reject_order(update, context, query, order_id: int, lang: str):
#     """Buyurtmani rad etish."""
#     try:
#         order = await sync_to_async(
#             Order.objects.select_related("user").get
#         )(id=order_id)
#     except Order.DoesNotExist:
#         await query.answer("❌ Buyurtma topilmadi!", show_alert=True)
#         return

#     order.status = "canceled"
#     await sync_to_async(order.save)(update_fields=["status"])
#     await query.answer("❌ Rad etildi!", show_alert=True)

#     if order.user:
#         user_lang = order.user.lang or "uz"
#         msg = {
#             "uz": f"❌ Buyurtmangiz (<code>#{order_id}</code>) rad etildi.\n📞 Muammo bo'lsa, aloqaga chiqing.",
#             "ru": f"❌ Ваш заказ (<code>#{order_id}</code>) отклонён.\n📞 По вопросам свяжитесь с нами.",
#             "en": f"❌ Your order (<code>#{order_id}</code>) was rejected.\n📞 Contact us if you have questions.",
#         }
#         try:
#             await context.bot.send_message(
#                 order.user.user_id,
#                 msg.get(user_lang, msg["uz"]),
#                 parse_mode="HTML",
#             )
#         except Exception:
#             pass


# # ═══════════════════════════════════════════════════════════════════════════════
# #  TUMANLAR (DISTRICTS)
# # ═══════════════════════════════════════════════════════════════════════════════
# async def _show_districts(query):
#     """Faol va nofaol tumanlarni ko'rsatadi."""
#     active_districts = await sync_to_async(
#         lambda: list(
#             District.objects.filter(is_active=True)
#             .select_related("region")
#             .values("id", "name", "region__name", "delivery_price")
#         )
#     )()

#     inactive_count = await sync_to_async(
#         District.objects.filter(is_active=False).count
#     )()

#     if not active_districts:
#         lines = "📭 Faol tumanlar yo'q."
#     else:
#         lines = "\n".join(
#             f"✅ <b>{d['name']}</b> ({d['region__name']}) — {d['delivery_price']:,} so'm"
#             for d in active_districts
#         )

#     kb = InlineKeyboardMarkup([
#         [InlineKeyboardButton("✏️ Faol tumanlarni o'zgartirish", callback_data="admin_edit_districts")],
#         [InlineKeyboardButton("⬅️ Orqaga",                       callback_data="admin_back")],
#     ])

#     await query.message.reply_text(
#         f"📍 <b>Faol tumanlar ({len(active_districts)}):</b>\n\n"
#         + lines
#         + (f"\n\n🔴 Nofaol tumanlar: {inactive_count} ta" if inactive_count else ""),
#         reply_markup=kb,
#         parse_mode="HTML",
#     )


# # ═══════════════════════════════════════════════════════════════════════════════
# #  XODIMLAR (STAFF)
# # ═══════════════════════════════════════════════════════════════════════════════
# async def _show_staff_menu(query):
#     admins_count  = await sync_to_async(TelegramUser.objects.filter(is_admin=True).count)()
#     courier_count = await sync_to_async(TelegramUser.objects.filter(role="courier").count)()
#     doctor_count  = await sync_to_async(TelegramUser.objects.filter(role="doctor").count)()

#     kb = InlineKeyboardMarkup([
#         [InlineKeyboardButton(f"👑 Admin qo'shish  ({admins_count})",    callback_data="admin_add_admin")],
#         [InlineKeyboardButton(f"🚗 Kuryer qo'shish  ({courier_count})",   callback_data="admin_add_courier")],
#         [InlineKeyboardButton(f"👨‍⚕️ Shifokor qo'shish ({doctor_count})", callback_data="admin_add_doctor")],
#         [
#             InlineKeyboardButton("📋 Kuryerlar ro'yxati",   callback_data="admin_list_couriers"),
#             InlineKeyboardButton("📋 Shifokorlar ro'yxati", callback_data="admin_list_doctors"),
#         ],
#         [InlineKeyboardButton("⬅️ Orqaga", callback_data="admin_back")],
#     ])
#     await query.message.reply_text(
#         "👥 <b>Xodimlar boshqaruvi:</b>", reply_markup=kb, parse_mode="HTML"
#     )


# async def _list_staff(query, role: str, title: str):
#     """Kuryer yoki shifokorlar ro'yxati."""
#     staff = await sync_to_async(
#         lambda: list(
#             TelegramUser.objects.filter(role=role)
#             .select_related("district")
#             .values("user_id", "first_name", "username", "district__name", "is_active")
#         )
#     )()

#     if not staff:
#         await query.message.reply_text(f"📭 {title} ro'yxati bo'sh.")
#         return

#     lines = []
#     buttons = []
#     for s in staff:
#         name     = s["first_name"] or "—"
#         username = f"@{s['username']}" if s["username"] else ""
#         district = s["district__name"] or "Tuman belgilanmagan"
#         active   = "🟢" if s["is_active"] else "🔴"
#         lines.append(
#             f"{active} <b>{name}</b> {username}\n"
#             f"   🆔 <code>{s['user_id']}</code> | 📍 {district}"
#         )
#         buttons.append([
#             InlineKeyboardButton(
#                 f"🗑 {name} ni o'chirish",
#                 callback_data=f"admin_remove_staff_{s['user_id']}",
#             )
#         ])

#     buttons.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="admin_users")])

#     await query.message.reply_text(
#         f"<b>{title}:</b>\n\n" + "\n\n".join(lines),
#         reply_markup=InlineKeyboardMarkup(buttons),
#         parse_mode="HTML",
#     )


# async def _show_user_selector(update, context, admin_id: int, role: str):
#     """Telegram-dan user tanlash yoki qo'lda ID kiritish."""
#     role_names = {"admin": "Admin", "courier": "Kuryer", "doctor": "Shifokor"}
#     context.user_data["admin_step"]     = f"add_staff_{role}"
#     context.user_data["pending_role"]   = role

#     try:
#         request_users = KeyboardButtonRequestUsers(
#             request_id=42,
#             user_is_bot=False,
#             max_quantity=1,
#             request_name=True,
#         )
#         kb = ReplyKeyboardMarkup(
#             [
#                 [KeyboardButton("👤 Telegramdagi userlardan tanlash", request_users=request_users)],
#                 [KeyboardButton("⬅️ Orqaga")],
#             ],
#             one_time_keyboard=True,
#             resize_keyboard=True,
#         )
#         await context.bot.send_message(
#             admin_id,
#             f"👤 <b>{role_names[role]}</b> qo'shish uchun Telegram-dan user tanlang\n"
#             f"yoki Telegram <b>user ID</b> ni yozing:",
#             reply_markup=kb,
#             parse_mode="HTML",
#         )
#     except Exception:
#         # KeyboardButtonRequestUsers qo'llab-quvvatlanmasa, faqat matn so'raymiz
#         await context.bot.send_message(
#             admin_id,
#             f"👤 <b>{role_names[role]}</b> uchun Telegram user ID ni kiriting:\n"
#             f"📌 Masalan: <code>123456789</code>",
#             reply_markup=ReplyKeyboardRemove(),
#             parse_mode="HTML",
#         )


# async def _remove_staff(query, uid: int):
#     """Xodimni roldan chiqarish (user sifatida qoldiradi)."""
#     try:
#         user = await sync_to_async(TelegramUser.objects.get)(user_id=uid)
#         old_role = user.role
#         user.role     = "user"
#         user.is_admin = False
#         await sync_to_async(user.save)(update_fields=["role", "is_admin"])
#         await query.answer(f"✅ {old_role.capitalize()} roldan chiqarildi", show_alert=True)
#         await _show_staff_menu(query)
#     except TelegramUser.DoesNotExist:
#         await query.answer("❌ Foydalanuvchi topilmadi!", show_alert=True)


# async def _assign_courier_district(query, courier_tg_id: int, district_id: int, context, admin_id: int):
#     """Kuryer uchun tuman biriktirish."""
#     try:
#         courier  = await sync_to_async(TelegramUser.objects.get)(user_id=courier_tg_id)
#         district = await sync_to_async(District.objects.get)(id=district_id)
#         courier.district = district
#         courier.role     = "courier"
#         await sync_to_async(courier.save)(update_fields=["district", "role"])
#         await query.message.reply_text(
#             f"✅ Kuryer <code>{courier_tg_id}</code> → <b>{district.name}</b> tumaniga biriktirildi.",
#             parse_mode="HTML",
#         )
#         # Admin paneliga qaytish
#         class _FakeUpdate:
#             effective_message = query.message
#         await send_admin_panel(_FakeUpdate(), context, admin_id)
#     except (TelegramUser.DoesNotExist, District.DoesNotExist) as e:
#         await query.answer("❌ Foydalanuvchi yoki tuman topilmadi!", show_alert=True)


# # ═══════════════════════════════════════════════════════════════════════════════
# #  XABAR YUBORISH (BROADCAST)
# # ═══════════════════════════════════════════════════════════════════════════════
# async def _show_broadcast_menu(query):
#     kb = InlineKeyboardMarkup([
#         [InlineKeyboardButton("📝 Matn yuborish",  callback_data="admin_broadcast_text")],
#         [InlineKeyboardButton("🖼 Rasm + matn",    callback_data="admin_broadcast_photo")],
#         [InlineKeyboardButton("⬅️ Orqaga",         callback_data="admin_back")],
#     ])
#     await query.message.reply_text(
#         "📣 <b>Xabar yuborish</b>\n\n"
#         "Barcha foydalanuvchilarga xabar yuboring.",
#         reply_markup=kb,
#         parse_mode="HTML",
#     )


# async def _broadcast_text(context: ContextTypes.DEFAULT_TYPE, text: str) -> tuple[int, int]:
#     """Barcha faol foydalanuvchilarga matn yuboradi. (ok_count, fail_count) qaytaradi."""
#     import asyncio
#     users = await sync_to_async(
#         lambda: list(TelegramUser.objects.filter(is_active=True).values_list("user_id", flat=True))
#     )()
#     ok, fail = 0, 0
#     for i, uid in enumerate(users):
#         try:
#             await context.bot.send_message(uid, text, parse_mode="HTML")
#             ok += 1
#         except Exception:
#             fail += 1
#         if (i + 1) % 25 == 0:
#             await asyncio.sleep(1)
#     return ok, fail


# async def _broadcast_photo(context: ContextTypes.DEFAULT_TYPE, file_id: str, caption: str = "") -> tuple[int, int]:
#     """Barcha faol foydalanuvchilarga rasm yuboradi."""
#     import asyncio
#     users = await sync_to_async(
#         lambda: list(TelegramUser.objects.filter(is_active=True).values_list("user_id", flat=True))
#     )()
#     ok, fail = 0, 0
#     for i, uid in enumerate(users):
#         try:
#             await context.bot.send_photo(
#                 uid, file_id,
#                 caption=caption or None,
#                 parse_mode="HTML" if caption else None,
#             )
#             ok += 1
#         except Exception:
#             fail += 1
#         if (i + 1) % 25 == 0:
#             await asyncio.sleep(1)
#     return ok, fail


# # ═══════════════════════════════════════════════════════════════════════════════
# #  MATN HANDLER (admin_step orqali)
# # ═══════════════════════════════════════════════════════════════════════════════
# async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """
#     Admin uchun matnli xabar handleri.
#     Har bir admin_step uchun mos amal bajaradi.
#     Faqat admin bo'lgan foydalanuvchilar uchun ishlaydi.
#     """
#     tg_id = update.effective_user.id
#     if not await _is_admin(tg_id):
#         return  # Admin emas — boshqa handlerlarga o'tadi

#     step = context.user_data.get("admin_step")
#     if not step:
#         return  # Admin stepda emas

#     text = update.message.text.strip()

#     # ── "Orqaga" tugmasi ──────────────────────────────────────────────────────
#     if text in ("⬅️ Orqaga", "/admin", "/start"):
#         context.user_data.pop("admin_step", None)
#         context.user_data.pop("pending_role", None)
#         await update.message.reply_text(
#             "Admin panelga qaytildi.", reply_markup=ReplyKeyboardRemove()
#         )
#         await send_admin_panel(update, context, tg_id)
#         return

#     # ── Sozlamalar ─────────────────────────────────────────────────────────────
#     if step == "set_channel":
#         await _set_setting("channel_id", text)
#         context.user_data.pop("admin_step")
#         await update.message.reply_text(f"✅ Kanal ID yangilandi: <code>{text}</code>", parse_mode="HTML")
#         await send_admin_panel(update, context, tg_id)

#     elif step == "set_price":
#         if not text.isdigit():
#             await update.message.reply_text("❌ Faqat raqam kiriting (masalan: <code>150000</code>)", parse_mode="HTML")
#             return
#         await _set_setting("service_price", text)
#         context.user_data.pop("admin_step")
#         await update.message.reply_text(f"✅ Xizmat narxi: <b>{int(text):,} so'm</b>", parse_mode="HTML")
#         await send_admin_panel(update, context, tg_id)

#     elif step == "set_extra":
#         if not text.isdigit():
#             await update.message.reply_text("❌ Faqat raqam kiriting.", parse_mode="HTML")
#             return
#         await _set_setting("pickup_extra", text)
#         context.user_data.pop("admin_step")
#         await update.message.reply_text(f"✅ Pickup extra: <b>{int(text):,} so'm</b>", parse_mode="HTML")
#         await send_admin_panel(update, context, tg_id)

#     elif step == "set_card":
#         await _set_setting("payment_card", text)
#         context.user_data.pop("admin_step")
#         await update.message.reply_text(f"✅ Karta raqami yangilandi: <code>{text}</code>", parse_mode="HTML")
#         await send_admin_panel(update, context, tg_id)

#     elif step == "set_owner":
#         await _set_setting("payment_owner", text)
#         context.user_data.pop("admin_step")
#         await update.message.reply_text(f"✅ Karta egasi: <b>{text}</b>", parse_mode="HTML")
#         await send_admin_panel(update, context, tg_id)

#     elif step == "set_click_url":
#         if not text.startswith("http"):
#             await update.message.reply_text("❌ To'g'ri URL kiriting (https:// bilan boshlaning).")
#             return
#         await _set_setting("click_payment_url", text)
#         context.user_data.pop("admin_step")
#         await update.message.reply_text(f"✅ Click URL yangilandi.", parse_mode="HTML")
#         await send_admin_panel(update, context, tg_id)

#     elif step == "set_allowed_regions":
#         # "1,2,5,8" formatidagi ID lar
#         ids = [i.strip() for i in text.split(",") if i.strip().isdigit()]
#         if not ids:
#             await update.message.reply_text(
#                 "❌ Noto'g'ri format. Vergul bilan ajratilgan ID kiriting:\n<code>1,2,5,8</code>",
#                 parse_mode="HTML",
#             )
#             return
#         # District larni faol/nofaol qilish
#         all_ids = await sync_to_async(
#             lambda: list(District.objects.values_list("id", flat=True))
#         )()
#         int_ids = [int(i) for i in ids]
#         await sync_to_async(
#             lambda: District.objects.filter(id__in=int_ids).update(is_active=True)
#         )()
#         await sync_to_async(
#             lambda: District.objects.exclude(id__in=int_ids).update(is_active=False)
#         )()
#         context.user_data.pop("admin_step")
#         await update.message.reply_text(
#             f"✅ Faol tumanlar yangilandi. Faol: <b>{len(int_ids)}</b> ta tuman.",
#             parse_mode="HTML",
#         )
#         await send_admin_panel(update, context, tg_id)

#     # ── Broadcast matn ────────────────────────────────────────────────────────
#     elif step == "broadcast_text":
#         context.user_data.pop("admin_step")
#         msg = await update.message.reply_text("📤 Xabar yuborilmoqda, iltimos kuting...")
#         import asyncio
#         ok, fail = await _broadcast_text(context, text)
#         await msg.edit_text(
#             f"✅ Xabar yuborildi!\n\n"
#             f"✅ Muvaffaqiyatli: <b>{ok}</b>\n"
#             f"❌ Xatolik: <b>{fail}</b>",
#             parse_mode="HTML",
#         )

#     # ── Xodim qo'shish (ID kiritilganda) ─────────────────────────────────────
#     elif step and step.startswith("add_staff_"):
#         role = step[len("add_staff_"):]
#         if text.lstrip("-").isdigit():
#             await _add_staff_by_id(update, context, int(text), role, tg_id)
#         else:
#             await update.message.reply_text(
#                 "❌ Faqat raqamli Telegram user ID kiriting:\n<code>123456789</code>",
#                 parse_mode="HTML",
#             )


# async def _add_staff_by_id(update, context, uid: int, role: str, admin_id: int):
#     """User ID bo'yicha xodim qo'shish."""
#     try:
#         user = await sync_to_async(TelegramUser.objects.get)(user_id=uid)
#     except TelegramUser.DoesNotExist:
#         await update.message.reply_text(
#             f"❌ Telegram ID <code>{uid}</code> topilmadi.\n"
#             f"Foydalanuvchi avval botni ishga tushirishi kerak.",
#             parse_mode="HTML",
#         )
#         return

#     role_names = {"admin": "Admin", "courier": "Kuryer", "doctor": "Shifokor"}
#     user.role = role
#     if role == "admin":
#         user.is_admin = True
#     await sync_to_async(user.save)(update_fields=["role", "is_admin"])
#     context.user_data.pop("admin_step", None)
#     context.user_data.pop("pending_role", None)

#     await update.message.reply_text(
#         f"✅ <b>{user.first_name or uid}</b> → <b>{role_names[role]}</b> roliga qo'shildi!",
#         reply_markup=ReplyKeyboardRemove(),
#         parse_mode="HTML",
#     )

#     # Kuryer bo'lsa, tuman tanlash
#     if role == "courier":
#         districts = await sync_to_async(
#             lambda: list(
#                 District.objects.filter(is_active=True)
#                 .select_related("region")
#                 .values("id", "name", "region__name")[:20]
#             )
#         )()
#         if districts:
#             rows = []
#             for i in range(0, len(districts), 2):
#                 row = []
#                 for d in districts[i:i+2]:
#                     row.append(InlineKeyboardButton(
#                         f"{d['name']} ({d['region__name']})",
#                         callback_data=f"admin_region_courier_{uid}_{d['id']}",
#                     ))
#                 rows.append(row)
#             rows.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="admin_users")])
#             await update.message.reply_text(
#                 f"📍 Kuryer <code>{uid}</code> uchun tuman tanlang:",
#                 reply_markup=InlineKeyboardMarkup(rows),
#                 parse_mode="HTML",
#             )
#             return

#     await send_admin_panel(update, context, admin_id)


# # ═══════════════════════════════════════════════════════════════════════════════
# #  RASM HANDLER (broadcast_photo / instruction)
# # ═══════════════════════════════════════════════════════════════════════════════
# async def handle_admin_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Admin uchun rasm/fayl handleri."""
#     tg_id = update.effective_user.id
#     if not await _is_admin(tg_id):
#         return

#     step = context.user_data.get("admin_step")
#     if not step:
#         return

#     photo  = update.message.photo
#     doc    = update.message.document
#     video  = update.message.video

#     if step == "broadcast_photo":
#         if not photo and not doc:
#             await update.message.reply_text("❌ Rasm yuboring.")
#             return
#         file_id = photo[-1].file_id if photo else doc.file_id
#         caption = update.message.caption or ""
#         context.user_data.pop("admin_step")
#         msg = await update.message.reply_text("📤 Rasm yuborilmoqda...")
#         ok, fail = await _broadcast_photo(context, file_id, caption)
#         await msg.edit_text(
#             f"✅ Rasm yuborildi!\n✅ Muvaffaqiyatli: <b>{ok}</b>\n❌ Xatolik: <b>{fail}</b>",
#             parse_mode="HTML",
#         )

#     elif step == "waiting_instruction":
#         if photo:
#             file_id = photo[-1].file_id
#             ftype   = "photo"
#         elif video:
#             file_id = video.file_id
#             ftype   = "video"
#         elif doc:
#             file_id = doc.file_id
#             ftype   = "document"
#         else:
#             await update.message.reply_text("❌ Fayl, rasm yoki video yuboring.")
#             return

#         await _set_setting("instruction_file_id", file_id)
#         await _set_setting("instruction_file_type", ftype)
#         context.user_data.pop("admin_step")
#         await update.message.reply_text(
#             f"✅ Ko'rsatma fayl saqlandi! (<b>{ftype}</b>)", parse_mode="HTML"
#         )
#         await send_admin_panel(update, context, tg_id)


# # ═══════════════════════════════════════════════════════════════════════════════
# #  USER SHARED HANDLER (Telegram user tanlanganda)
# # ═══════════════════════════════════════════════════════════════════════════════
# async def handle_user_shared_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """
#     KeyboardButtonRequestUsers orqali tanlangan user ID ni qayta ishlaydi.
#     apps/Bot/handlers/main.py da:
#         MessageHandler(filters.StatusUpdate.USERS_SHARED, handle_user_shared_admin)
#     """
#     tg_id = update.effective_user.id
#     if not await _is_admin(tg_id):
#         return

#     step = context.user_data.get("admin_step", "")
#     if not step.startswith("add_staff_"):
#         return

#     role = step[len("add_staff_"):]
#     users_shared = update.message.users_shared
#     if not users_shared or not users_shared.users:
#         await update.message.reply_text("❌ User tanlanmadi.")
#         return

#     shared_user = users_shared.users[0]
#     uid = shared_user.user_id

#     await _add_staff_by_id(update, context, uid, role, tg_id)