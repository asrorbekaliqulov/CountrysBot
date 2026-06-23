"""
Markazlashtirilgan tarjima tizimi
Bot, Admin panel, Kuryer panel va WebApp uchun
"""

def t(key: str, lang: str = "uz", **kwargs) -> str:
    """
    Tarjima funksiyasi
    Args:
        key: Tarjima kaliti
        lang: Til kodi (uz, ru, en)
        **kwargs: Format uchun parametrlar
    Returns:
        Tarjimalangan matn
    """
    text = TRANSLATIONS.get(key, {}).get(lang)
    if not text:
        text = TRANSLATIONS.get(key, {}).get("uz", key)
    
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text


# ═══════════════════════════════════════════════════════════════════════════════
# BOT UMUMIY XABARLAR
# ═══════════════════════════════════════════════════════════════════════════════

TRANSLATIONS = {
    # ── Welcome va asosiy menyu ─────────────────────────────────────────────
    "welcome": {
        "uz": """🖤 Assalomu alaykum,
NMED HOME LAB ga xush kelibsiz. Siz premium xizmatimizdan foydalanayotganingizdan mamnunmiz.

🚚 Maxsus konteyner xodimlarimiz tomonidan uyingizga yetkaziladi
🧪 3 kun davomida namunadan kerakli qism konteynerga joylashtiriladi
📦 Tayyor namuna laboratoriyamizga yuboriladi
🔬 Tekshiruv professional standart asosida amalga oshiriladi
📊 Natijalar online tarzda yuboriladi

✨ Laboratoriya endi uyingizda.""",
        "ru": """🖤 Добро пожаловать в NMED HOME LAB. Мы рады, что вы пользуетесь нашим премиум-сервисом.

🚚 Специальный контейнер доставят вам домой наши сотрудники
🧪 На 3 дня необходимая часть образца помещается в контейнер
📦 Готовый образец отправляется в нашу лабораторию
🔬 Проверка проводится на основании профессиональных стандартов
📊 Результаты будут отправлены онлайн

✨ Лаборатория теперь дома.""",
        "en": """🖤 Welcome to NMED HOME LAB. We are happy that you are using our premium service.

🚚 Our employees will deliver the special container to your home
🧪 The necessary part of the sample is placed in the container in 3 days
📦 The ready sample is sent to our laboratory
🔬 The check is carried out according to professional standards
📊 The results are sent online

✨ The laboratory is now at home."""
    },
    
    # ── Tugmalar ──────────────────────────────────────────────────────────
    "btn_order": {
        "uz": "🧪 Tahlil buyurtma berish",
        "ru": "🧪 Заказать анализ",
        "en": "🧪 Order analysis"
    },
    "btn_results": {
        "uz": "📊 Natijalarim",
        "ru": "📊 Мои результаты",
        "en": "📊 My results"
    },
    "btn_order_status": {
        "uz": "🚚 Buyurtma holati",
        "ru": "🚚 Статус заказа",
        "en": "🚚 Order status"
    },

    "btn_profile": {
        "uz": "👤 Mening profilim",
        "ru": "👤 Мой профиль",
        "en": "👤 My profile"
    },
    "btn_feedback": {
        "uz": "⭐️ Fikr & shikoyat",
        "ru": "⭐️ Отзыв & жалоба",
        "en": "⭐️ Feedback & complaint"
    },
    "btn_contact": {
        "uz": "📞 Biz bilan bog'lanish",
        "ru": "📞 Связаться с нами",
        "en": "📞 Contact us"
    },
    "btn_admin_panel": {
        "uz": "🖥 Admin panel",
        "ru": "🖥 Панель админа",
        "en": "🖥 Admin panel"
    },
    "btn_back": {
        "uz": "🔙 Orqaga",
        "ru": "🔙 Назад",
        "en": "🔙 Back"
    },
    "btn_cancel": {
        "uz": "❌ Bekor qilish",
        "ru": "❌ Отменить",
        "en": "❌ Cancel"
    },
    "btn_continue": {
        "uz": "Davom etish →",
        "ru": "Продолжить →",
        "en": "Continue →"
    },
    
    # ── Til tanlash ───────────────────────────────────────────────────────
    "lang_prompt": {
        "uz": "🌐 Tilni tanlang / Выберите язык / Choose language:",
        "ru": "🌐 Tilni tanlang / Выберите язык / Choose language:",
        "en": "🌐 Tilni tanlang / Выберите язык / Choose language:"
    },
    "lang_confirmed": {
        "uz": "✅ Til o'zbek tiliga o'rnatildi!",
        "ru": "✅ Язык установлен: русский!",
        "en": "✅ Language set to English!"
    },
    
    # ── Admin panel ───────────────────────────────────────────────────────
    "admin_welcome": {
        "uz": "<b>Main Menu 🖥\n<tg-spoiler>/admin_panel</tg-spoiler></b>",
        "ru": "<b>Главное меню 🖥\n<tg-spoiler>/admin_panel</tg-spoiler></b>",
        "en": "<b>Main Menu 🖥\n<tg-spoiler>/admin_panel</tg-spoiler></b>"
    },

    
    # ── Admin menu ────────────────────────────────────────────────────────
    "admin_menu_title": {
        "uz": "🛠 <b>Admin boshqaruv paneli</b>",
        "ru": "🛠 <b>Панель управления админа</b>",
        "en": "🛠 <b>Admin control panel</b>"
    },
    "admin_pending_orders": {
        "uz": "💳 Kutilayotgan to'lovlar ({count})",
        "ru": "💳 Ожидающие платежи ({count})",
        "en": "💳 Pending payments ({count})"
    },
    "admin_pending_orders_zero": {
        "uz": "💳 Kutilayotgan to'lovlar",
        "ru": "💳 Ожидающие платежи",
        "en": "💳 Pending payments"
    },
    "admin_bot_stats": {
        "uz": "📊 Bot Statistikasi",
        "ru": "📊 Статистика бота",
        "en": "📊 Bot Statistics"
    },
    "admin_send_message": {
        "uz": "📣 Xabar yuborish",
        "ru": "📣 Отправить сообщение",
        "en": "📣 Send message"
    },
    
    # ── Bot stats ─────────────────────────────────────────────────────────
    "stats_title": {
        "uz": "<b>@{username} ning statistikasi:\n\n👥 <i>Bot foydalanuvchilar soni:</i> {total} ta\n——————————\n🆕 <i>Yangi qo'shilgan foydalanuvchilar soni:</i> {new} ta\n——————————\n👮‍♂️ <i>Adminlar soni:</i> {admins} ta\n——————————\n🔥 <i>Faol foydalanuvchilar:</i> {active} ta\n——————————\n🚫 <i>Nofaol foydalanuvchilar:</i> {inactive} ta</b>",
        "ru": "<b>Статистика @{username}:\n\n👥 <i>Количество пользователей бота:</i> {total}\n——————————\n🆕 <i>Новых пользователей:</i> {new}\n——————————\n👮‍♂️ <i>Количество админов:</i> {admins}\n——————————\n🔥 <i>Активные пользователи:</i> {active}\n——————————\n🚫 <i>Неактивные пользователи:</i> {inactive}</b>",
        "en": "<b>@{username} statistics:\n\n👥 <i>Bot users count:</i> {total}\n——————————\n🆕 <i>New users:</i> {new}\n——————————\n👮‍♂️ <i>Admins count:</i> {admins}\n——————————\n🔥 <i>Active users:</i> {active}\n——————————\n🚫 <i>Inactive users:</i> {inactive}</b>"
    },
    "stats_loading": {
        "uz": "Malumotlar yuklanmoqda...",
        "ru": "Загрузка данных...",
        "en": "Loading data..."
    },

    
    # ── Send message ──────────────────────────────────────────────────────
    "send_msg_select_type": {
        "uz": "Xabar turini tanlang:",
        "ru": "Выберите тип сообщения:",
        "en": "Select message type:"
    },
    "send_msg_text": {
        "uz": "💬 Text xabar",
        "ru": "💬 Текстовое сообщение",
        "en": "💬 Text message"
    },
    "send_msg_photo": {
        "uz": "🖼 Rasmli xabar",
        "ru": "🖼 Сообщение с фото",
        "en": "🖼 Photo message"
    },
    "send_msg_video": {
        "uz": "🎞 Video xabar",
        "ru": "🎞 Видео сообщение",
        "en": "🎞 Video message"
    },
    "send_msg_audio": {
        "uz": "🔈 Audio xabar",
        "ru": "🔈 Аудио сообщение",
        "en": "🔈 Audio message"
    },
    "send_msg_file": {
        "uz": "📁 Fayl xabar",
        "ru": "📁 Файл сообщение",
        "en": "📁 File message"
    },
    "send_msg_voice": {
        "uz": "🎙 Ovozli xabar",
        "ru": "🎙 Голосовое сообщение",
        "en": "🎙 Voice message"
    },
    "send_msg_now": {
        "uz": "Endi xabarni yuboring:",
        "ru": "Теперь отправьте сообщение:",
        "en": "Now send the message:"
    },
    "send_msg_sent": {
        "uz": "{count} ta foydalanuvchiga xabar yuborildi.",
        "ru": "Сообщение отправлено {count} пользователям.",
        "en": "Message sent to {count} users."
    },
    "send_msg_cancelled": {
        "uz": "Xabar yuborish bekor qilindi.",
        "ru": "Отправка сообщения отменена.",
        "en": "Message sending cancelled."
    },

    
    # ── Admin qo'shish ────────────────────────────────────────────────────
    "admin_add_select_user": {
        "uz": "Quyidagi tugmani bosish orqali kerakli foydalanuvchini tanlang:",
        "ru": "Выберите нужного пользователя, нажав на кнопку ниже:",
        "en": "Select the required user by clicking the button below:"
    },
    "admin_add_select_btn": {
        "uz": "Foydalanuvchilar",
        "ru": "Пользователи",
        "en": "Users"
    },
    "admin_add_confirm": {
        "uz": "Foydalanuvchi ID: {user_id}. Ushbu foydalanuvchini admin qilishni tasdiqlaysizmi? (Ha/Yo'q)",
        "ru": "ID пользователя: {user_id}. Подтверждаете назначение этого пользователя администратором? (Да/Нет)",
        "en": "User ID: {user_id}. Do you confirm making this user an admin? (Yes/No)"
    },
    "admin_add_success": {
        "uz": "Foydalanuvchi {user} admin qilindi.",
        "ru": "Пользователь {user} назначен администратором.",
        "en": "User {user} has been made an admin."
    },
    "admin_add_success_notify": {
        "uz": "Tabriklayman siz hozirgina admin bo'ldingiz",
        "ru": "Поздравляем, вы теперь администратор",
        "en": "Congratulations, you are now an admin"
    },
    "admin_add_not_found": {
        "uz": "Bunday foydalanuvchi topilmadi.",
        "ru": "Пользователь не найден.",
        "en": "User not found."
    },
    "admin_add_cancelled": {
        "uz": "Amal bekor qilindi.",
        "ru": "Действие отменено.",
        "en": "Action cancelled."
    },
    "admin_first_success": {
        "uz": "Siz Admin bo'ldingiz",
        "ru": "Вы стали администратором",
        "en": "You have become an admin"
    },
    "admin_first_exists": {
        "uz": "Botda boshqa admin mavjud.",
        "ru": "В боте уже есть другой администратор.",
        "en": "Another admin already exists in the bot."
    },

    
    # ── Feedback ──────────────────────────────────────────────────────────
    "feedback_title": {
        "uz": "⭐️ Fikr va baholash\n\nXizmatimizni baholang yoki takliflaringizni yozing:",
        "ru": "⭐️ Отзыв и оценка\n\nОцените нашу услугу или напишите предложения:",
        "en": "⭐️ Feedback and rating\n\nRate our service or write suggestions:"
    },
    "feedback_rate": {
        "uz": "⭐ Baholash",
        "ru": "⭐ Оценить",
        "en": "⭐ Rate"
    },
    "feedback_suggestion": {
        "uz": "📝 Faqat taklif yozish",
        "ru": "📝 Только предложение",
        "en": "📝 Suggestion only"
    },
    "feedback_rate_service": {
        "uz": "⭐️ Xizmatimizni baholang (1-5):",
        "ru": "⭐️ Оцените нашу услугу (1-5):",
        "en": "⭐️ Rate our service (1-5):"
    },
    "feedback_write_suggestion": {
        "uz": "📝 Taklifingizni yozing:\n\nYuborish uchun xabaringizni yuboring.",
        "ru": "📝 Напишите ваше предложение:\n\nОтправьте сообщение для отправки.",
        "en": "📝 Write your suggestion:\n\nSend your message to submit."
    },
    "feedback_rating_selected": {
        "uz": "⭐️ Siz {rating} yulduz tanladingiz.\n\nQo'shimcha fikringiz bormi? Yuborish uchun xabaringizni yuboring, yoki \"Skip\" tugmasini bosing.",
        "ru": "⭐️ Вы выбрали {rating} звезд.\n\nЕсть ли дополнительные комментарии? Отправьте сообщение или нажмите \"Skip\".",
        "en": "⭐️ You selected {rating} stars.\n\nAny additional comments? Send a message or press \"Skip\"."
    },
    "feedback_skip": {
        "uz": "⏭️ Skip",
        "ru": "⏭️ Пропустить",
        "en": "⏭️ Skip"
    },
    "feedback_thanks": {
        "uz": "✅ Fikringiz qabul qilindi! ({rating} ⭐)\n\nRahmat!",
        "ru": "✅ Ваш отзыв принят! ({rating} ⭐)\n\nСпасибо!",
        "en": "✅ Your feedback has been accepted! ({rating} ⭐)\n\nThank you!"
    },
    "feedback_suggestion_thanks": {
        "uz": "✅ Taklifingiz qabul qilindi! Rahmat!",
        "ru": "✅ Ваше предложение принято! Спасибо!",
        "en": "✅ Your suggestion has been accepted! Thank you!"
    },
    "feedback_rating_thanks": {
        "uz": "✅ Baholashingiz qabul qilindi! ({rating} ⭐)\n\nRahmat!",
        "ru": "✅ Ваша оценка принята! ({rating} ⭐)\n\nСпасибо!",
        "en": "✅ Your rating has been accepted! ({rating} ⭐)\n\nThank you!"
    },

    
    # ── Guide ─────────────────────────────────────────────────────────────
    "guide_help": {
        "uz": "ℹ️ Qo'llanma",
        "ru": "ℹ️ Руководство",
        "en": "ℹ️ Guide"
    },
    "guide_no_content": {
        "uz": "Qo'llanma mavjud emas",
        "ru": "Руководство недоступно",
        "en": "No guide available"
    },
    "guide_create_title": {
        "uz": "Yangi qo'llanma sarlavhasini kiriting:",
        "ru": "Введите заголовок нового руководства:",
        "en": "Enter new guide title:"
    },
    "guide_create_content": {
        "uz": "Qo'llanma matnini kiriting:",
        "ru": "Введите текст руководства:",
        "en": "Enter guide content:"
    },
    "guide_created": {
        "uz": "Qo'llanma muvaffaqiyatli yaratildi.",
        "ru": "Руководство успешно создано.",
        "en": "Guide created successfully."
    },
    "guide_no_guides": {
        "uz": "Hech qanday qo'llanma mavjud emas.",
        "ru": "Руководства отсутствуют.",
        "en": "No guides available."
    },
    "guide_select_update": {
        "uz": "O'zgartirmoqchi bo'lgan qo'llanmani tanlang:",
        "ru": "Выберите руководство для изменения:",
        "en": "Select guide to update:"
    },
    "guide_current_title": {
        "uz": "Hozirgi sarlavha: {title}\nYangi sarlavhani kiriting (yoki eski sarlavhani qayta kiriting):",
        "ru": "Текущий заголовок: {title}\nВведите новый заголовок (или введите старый заголовок повторно):",
        "en": "Current title: {title}\nEnter new title (or re-enter old title):"
    },
    "guide_new_content": {
        "uz": "Yangi matnni kiriting (yoki eski matnni qayta kiriting):",
        "ru": "Введите новый текст (или введите старый текст повторно):",
        "en": "Enter new content (or re-enter old content):"
    },
    "guide_updated": {
        "uz": "Qo'llanma muvaffaqiyatli o'zgartirildi.",
        "ru": "Руководство успешно изменено.",
        "en": "Guide updated successfully."
    },
    "guide_select_delete": {
        "uz": "O'chirmoqchi bo'lgan qo'llanmani tanlang:",
        "ru": "Выберите руководство для удаления:",
        "en": "Select guide to delete:"
    },
    "guide_deleted": {
        "uz": "Qo'llanma muvaffaqiyatli o'chirildi.",
        "ru": "Руководство успешно удалено.",
        "en": "Guide deleted successfully."
    },

    
    # ── Support & Appeals ─────────────────────────────────────────────────
    "support_send_message": {
        "uz": "Adminga yubormochi bo'lgan xabarni kiritingiz.",
        "ru": "Введите сообщение, которое хотите отправить администратору.",
        "en": "Enter the message you want to send to the admin."
    },
    "support_message_sent": {
        "uz": "Xabani adminga yubordim🤓\nTez orada javob olasiz!!!",
        "ru": "Сообщение отправлено администратору🤓\nВы скоро получите ответ!!!",
        "en": "Message sent to admin🤓\nYou will receive a response soon!!!"
    },
    "support_no_appeals": {
        "uz": "Hozircha murojaatlar yo'q.",
        "ru": "Обращений пока нет.",
        "en": "No appeals yet."
    },
    "support_appeals_title": {
        "uz": "<b>Murojaatlar — sahifa {page}/{total}</b>\n\n{text}",
        "ru": "<b>Обращения — страница {page}/{total}</b>\n\n{text}",
        "en": "<b>Appeals — page {page}/{total}</b>\n\n{text}"
    },
    "support_reply_sent": {
        "uz": "✅ Javob yuborildi va murojaat holati yangilandi.",
        "ru": "✅ Ответ отправлен и статус обращения обновлен.",
        "en": "✅ Reply sent and appeal status updated."
    },
    "support_reply_error": {
        "uz": "Xatolik: foydalanuvchiga xabar yuborib bo'lmadi.\n{error}",
        "ru": "Ошибка: не удалось отправить сообщение пользователю.\n{error}",
        "en": "Error: could not send message to user.\n{error}"
    },
    "support_no_user_id": {
        "uz": "Xatolik: <code>User ID topilmadi.</code>",
        "ru": "Ошибка: <code>User ID не найден.</code>",
        "en": "Error: <code>User ID not found.</code>"
    },
    "support_appeal_not_found": {
        "uz": "❗ Murojaat topilmadi yoki allaqachon ko'rilgan.",
        "ru": "❗ Обращение не найдено или уже рассмотрено.",
        "en": "❗ Appeal not found or already reviewed."
    },
    "support_admin_reply": {
        "uz": "<b>Admin javobi:</b> {text}",
        "ru": "<b>Ответ администратора:</b> {text}",
        "en": "<b>Admin reply:</b> {text}"
    },

    
    # ── Profile ───────────────────────────────────────────────────────────
    "profile_title": {
        "uz": "<b>👤 SHAXSIY PROFIL</b>\n\n🆔 ID: <code>{patient_id}</code>\n📛 Ism: {first_name}\n📅 Ro'yxatdan o'tgan: {date_joined}\n⭐️ Bonuslar: {bonus_points} ball\n\n<b>Buyurtmalar holati:</b>\n└ Jami: {count} ta\n└ Yakunlangan: {completed} ta\n\n<b>🎁 Har 6-chi buyurtma bepul!</b>\n{bar}\n💡 Yana <b>{next_free} ta</b> buyurtmadan keyin keyingisi bepul.",
        "ru": "<b>👤 МОЙ ПРОФИЛЬ</b>\n\n🆔 ID: <code>{patient_id}</code>\n📛 Имя: {first_name}\n📅 Дата регистрации: {date_joined}\n⭐️ Бонусы: {bonus_points} баллов\n\n<b>Статус заказов:</b>\n└ Всего: {count}\n└ Выполнено: {completed}\n\n<b>🎁 Каждый 6-й заказ бесплатно!</b>\n{bar}\n💡 Ещё <b>{next_free}</b> заказов до бесплатного.",
        "en": "<b>👤 MY PROFILE</b>\n\n🆔 ID: <code>{patient_id}</code>\n📛 Name: {first_name}\n📅 Joined: {date_joined}\n⭐️ Bonus points: {bonus_points}\n\n<b>Order stats:</b>\n└ Total: {count}\n└ Completed: {completed}\n\n<b>🎁 Every 6th order is FREE!</b>\n{bar}\n💡 <b>{next_free}</b> more orders until your free one."
    },
    "profile_no_user": {
        "uz": "❌ Foydalanuvchi topilmadi.",
        "ru": "❌ Пользователь не найден.",
        "en": "❌ User not found."
    },
    "profile_no_results": {
        "uz": "📭 Hozircha natijalar mavjud emas.\nTahlil buyurtma bering va natijangiz bu yerda chiqadi.",
        "ru": "📭 Результатов пока нет.\nОформите заказ — результаты появятся здесь.",
        "en": "📭 No results yet.\nPlace an order and your results will appear here."
    },
    "profile_no_orders": {
        "uz": "📭 Hozircha buyurtmalar yo'q.\nBirinchi buyurtmangizni bering! 🎉",
        "ru": "📭 Заказов пока нет.\nОформите первый заказ! 🎉",
        "en": "📭 No orders yet.\nPlace your first order! 🎉"
    },
    "profile_results_header": {
        "uz": "📊 <b>Tahlil natijalari</b>\n\nSo'nggi {count} ta natija:",
        "ru": "📊 <b>Результаты анализов</b>\n\nПоследние {count} результатов:",
        "en": "📊 <b>Analysis Results</b>\n\nLatest {count} results:"
    },
    "profile_orders_header": {
        "uz": "🚚 <b>Buyurtmalar holati</b>\n\nSo'nggi {count} ta buyurtma:",
        "ru": "🚚 <b>Статус заказов</b>\n\nПоследние {count} заказов:",
        "en": "🚚 <b>Order Status</b>\n\nLatest {count} orders:"
    },

    
    # ── Status labels ─────────────────────────────────────────────────────
    "status_pending": {
        "uz": "⏳ Kutilmoqda",
        "ru": "⏳ Ожидает",
        "en": "⏳ Pending"
    },
    "status_paid": {
        "uz": "💳 To'langan",
        "ru": "💳 Оплачен",
        "en": "💳 Paid"
    },
    "status_delivering": {
        "uz": "🚚 Kuryer yo'lda",
        "ru": "🚚 Курьер едет",
        "en": "🚚 On the way"
    },
    "status_done": {
        "uz": "✅ Yetkazildi",
        "ru": "✅ Доставлено",
        "en": "✅ Delivered"
    },
    "status_canceled": {
        "uz": "❌ Bekor qilindi",
        "ru": "❌ Отменён",
        "en": "❌ Cancelled"
    },
    
    # ── Error messages ────────────────────────────────────────────────────
    "error_generic": {
        "uz": "Qandaydir xatolik ro'y berdi.",
        "ru": "Произошла какая-то ошибка.",
        "en": "An error occurred."
    },
    "error_no_access": {
        "uz": "Siz admin emassiz!😠",
        "ru": "Вы не администратор!😠",
        "en": "You are not an admin!😠"
    },
    "error_user_not_found": {
        "uz": "Sizning ma'lumotlaringiz topilmadi.\n/start",
        "ru": "Ваши данные не найдены.\n/start",
        "en": "Your data not found.\n/start"
    },
    "error_no_permission": {
        "uz": "Iltimos, botdan to'liq foydalanish uchun quyidagi kanallarga a'zo bo'ling:",
        "ru": "Пожалуйста, подпишитесь на следующие каналы для полного использования бота:",
        "en": "Please subscribe to the following channels to fully use the bot:"
    },
    
    # ── Success messages ──────────────────────────────────────────────────
    "success_generic": {
        "uz": "✅ Muvaffaqiyatli!",
        "ru": "✅ Успешно!",
        "en": "✅ Success!"
    },
    
    # ── Yes/No ────────────────────────────────────────────────────────────
    "yes": {
        "uz": "Ha",
        "ru": "Да",
        "en": "Yes"
    },
    "no": {
        "uz": "Yo'q",
        "ru": "Нет",
        "en": "No"
    },
}
