"""
Userlar boshqaruvi - Admin panel uchun
Barcha foydalanuvchilarni ko'rish va rollarini o'zgartirish
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from asgiref.sync import sync_to_async
from django.db import models
from ..models.TelegramBot import TelegramUser
from ..decorators import admin_required
from ..translations import t

# States
SEARCH_USER, SELECT_USER, SELECT_ROLE = range(3)

# Sahifalash
PAGE_SIZE = 10


@admin_required
async def users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Userlar ro'yxatini ko'rsatish"""
    query = update.callback_query
    await query.answer()
    
    # Til aniqlash
    tg_user = update.effective_user
    try:
        user = await sync_to_async(TelegramUser.objects.get)(user_id=tg_user.id)
        lang = user.lang or 'uz'
    except:
        lang = 'uz'
    
    # Context ga lang saqlaymiz
    context.user_data['lang'] = lang
    
    # Sahifa raqami
    page = context.user_data.get('users_page', 0)
    
    # Barcha userlarni olish
    total_users = await sync_to_async(TelegramUser.objects.count)()
    
    # Sahifalash
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    
    users = await sync_to_async(
        lambda: list(
            TelegramUser.objects.all()
            .order_by('-date_joined')[start:end]
        )
    )()
    
    if not users:
        text = {
            'uz': "📭 Foydalanuvchilar topilmadi.",
            'ru': "📭 Пользователи не найдены.",
            'en': "📭 No users found."
        }
        await query.edit_message_text(text.get(lang, text['uz']))
        return ConversationHandler.END
    
    # Userlar ro'yxati
    text_lines = [
        {
            'uz': f"👥 <b>Barcha foydalanuvchilar</b>\n📊 Jami: {total_users} ta\n📄 Sahifa: {page + 1}/{(total_users + PAGE_SIZE - 1) // PAGE_SIZE}\n",
            'ru': f"👥 <b>Все пользователи</b>\n📊 Всего: {total_users}\n📄 Страница: {page + 1}/{(total_users + PAGE_SIZE - 1) // PAGE_SIZE}\n",
            'en': f"👥 <b>All users</b>\n📊 Total: {total_users}\n📄 Page: {page + 1}/{(total_users + PAGE_SIZE - 1) // PAGE_SIZE}\n"
        }[lang]
    ]
    
    # Har bir user uchun
    role_labels = {
        'uz': {'user': '👤 User', 'courier': '🚗 Kuryer', 'doctor': '👨‍⚕️ Shifokor', 'admin': '👑 Admin'},
        'ru': {'user': '👤 Пользователь', 'courier': '🚗 Курьер', 'doctor': '👨‍⚕️ Врач', 'admin': '👑 Админ'},
        'en': {'user': '👤 User', 'courier': '🚗 Courier', 'doctor': '👨‍⚕️ Doctor', 'admin': '👑 Admin'}
    }
    
    buttons = []
    for user in users:
        role_label = role_labels[lang].get(user.role, user.role)
        user_text = f"{user.first_name or 'N/A'} (@{user.username or 'no_username'})"
        text_lines.append(f"━━━━━━━━━━━━━━━━━━━━")
        text_lines.append(f"🆔 <code>{user.user_id}</code>")
        text_lines.append(f"👤 {user_text}")
        text_lines.append(f"📋 {role_label}")
        
        # Tugma qo'shamiz
        buttons.append([
            InlineKeyboardButton(
                f"✏️ {user.first_name or user.user_id}",
                callback_data=f"edit_user_{user.user_id}"
            )
        ])
    
    # Navigatsiya tugmalari
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton("◀️ Oldingi", callback_data="users_prev_page")
        )
    if end < total_users:
        nav_buttons.append(
            InlineKeyboardButton("▶️ Keyingi", callback_data="users_next_page")
        )
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Qidiruv tugmasi
    search_text = {
        'uz': "🔍 Qidirish",
        'ru': "🔍 Поиск",
        'en': "🔍 Search"
    }
    buttons.append([
        InlineKeyboardButton(search_text[lang], callback_data="search_user")
    ])
    
    # Orqaga tugmasi
    back_text = {
        'uz': "🔙 Orqaga",
        'ru': "🔙 Назад",
        'en': "🔙 Back"
    }
    buttons.append([
        InlineKeyboardButton(back_text[lang], callback_data="admin_panel")
    ])
    
    await query.edit_message_text(
        "\n".join(text_lines),
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='HTML'
    )
    return ConversationHandler.END


@admin_required
async def users_next_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Keyingi sahifa"""
    context.user_data['users_page'] = context.user_data.get('users_page', 0) + 1
    return await users_list(update, context)


@admin_required
async def users_prev_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Oldingi sahifa"""
    page = context.user_data.get('users_page', 0)
    if page > 0:
        context.user_data['users_page'] = page - 1
    return await users_list(update, context)


@admin_required
async def search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User qidirish"""
    query = update.callback_query
    await query.answer()
    
    lang = context.user_data.get('lang', 'uz')
    
    # Qidiruv holatini belgilaymiz
    context.user_data['searching_user'] = True
    
    text = {
        'uz': "🔍 Foydalanuvchini qidirish\n\nUser ID, username yoki ismni kiriting:",
        'ru': "🔍 Поиск пользователя\n\nВведите User ID, username или имя:",
        'en': "🔍 Search user\n\nEnter User ID, username or name:"
    }
    
    await query.edit_message_text(
        text.get(lang, text['uz']),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(
                t("btn_cancel", lang),
                callback_data="users_management"
            )
        ]])
    )
    return SEARCH_USER


@admin_required
async def process_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Qidiruv natijalarini ko'rsatish"""
    # Faqat qidiruv holatida bo'lsa ishlaydi
    if not context.user_data.get('searching_user'):
        return
    
    # Qidiruv holatini o'chiramiz
    context.user_data['searching_user'] = False
    
    search_text = update.message.text.strip()
    lang = context.user_data.get('lang', 'uz')
    
    # Qidiruv
    try:
        # Agar raqam bo'lsa user_id bo'yicha qidirish
        if search_text.isdigit():
            users = await sync_to_async(
                lambda: list(
                    TelegramUser.objects.filter(user_id=int(search_text))
                )
            )()
        else:
            # Aks holda username yoki first_name bo'yicha
            users = await sync_to_async(
                lambda: list(
                    TelegramUser.objects.filter(
                        models.Q(username__icontains=search_text) |
                        models.Q(first_name__icontains=search_text)
                    )[:20]
                )
            )()
    except Exception as e:
        print(f"Qidiruv xatosi: {e}")
        users = []
    
    if not users:
        text = {
            'uz': f"❌ '{search_text}' uchun natija topilmadi.",
            'ru': f"❌ Результаты для '{search_text}' не найдены.",
            'en': f"❌ No results found for '{search_text}'."
        }
        await update.message.reply_text(
            text.get(lang, text['uz']),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    t("btn_back", lang),
                    callback_data="users_management"
                )
            ]])
        )
        return
    
    # Natijalarni ko'rsatish
    role_labels = {
        'uz': {'user': '👤', 'courier': '🚗', 'doctor': '👨‍⚕️', 'admin': '👑'},
        'ru': {'user': '👤', 'courier': '🚗', 'doctor': '👨‍⚕️', 'admin': '👑'},
        'en': {'user': '👤', 'courier': '🚗', 'doctor': '👨‍⚕️', 'admin': '👑'}
    }
    
    buttons = []
    text_lines = [
        {
            'uz': f"🔍 <b>Qidiruv natijalari</b>\n📊 Topildi: {len(users)} ta\n",
            'ru': f"🔍 <b>Результаты поиска</b>\n📊 Найдено: {len(users)}\n",
            'en': f"🔍 <b>Search results</b>\n📊 Found: {len(users)}\n"
        }[lang]
    ]
    
    for user in users:
        role_emoji = role_labels[lang].get(user.role, '👤')
        user_text = f"{role_emoji} {user.first_name or 'N/A'} (@{user.username or 'no_username'})"
        
        buttons.append([
            InlineKeyboardButton(
                user_text,
                callback_data=f"edit_user_{user.user_id}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(
            t("btn_back", lang),
            callback_data="users_management"
        )
    ])
    
    await update.message.reply_text(
        "\n".join(text_lines),
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='HTML'
    )


@admin_required
async def edit_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Userni tahrirlash"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split('_')[-1])
    lang = context.user_data.get('lang', 'uz')
    
    # Userni olish
    try:
        user = await sync_to_async(TelegramUser.objects.get)(user_id=user_id)
    except TelegramUser.DoesNotExist:
        text = {
            'uz': "❌ Foydalanuvchi topilmadi.",
            'ru': "❌ Пользователь не найден.",
            'en': "❌ User not found."
        }
        await query.edit_message_text(text.get(lang, text['uz']))
        return ConversationHandler.END
    
    # User ma'lumotlari
    role_labels = {
        'uz': {'user': '👤 Oddiy foydalanuvchi', 'courier': '🚗 Kuryer', 'doctor': '👨‍⚕️ Shifokor', 'admin': '👑 Admin'},
        'ru': {'user': '👤 Обычный пользователь', 'courier': '🚗 Курьер', 'doctor': '👨‍⚕️ Врач', 'admin': '👑 Админ'},
        'en': {'user': '👤 Regular user', 'courier': '🚗 Courier', 'doctor': '👨‍⚕️ Doctor', 'admin': '👑 Admin'}
    }
    
    current_role = role_labels[lang].get(user.role, user.role)
    
    text = {
        'uz': f"""
👤 <b>Foydalanuvchi ma'lumotlari</b>

🆔 ID: <code>{user.user_id}</code>
👤 Ism: {user.first_name or 'N/A'}
📛 Username: @{user.username or 'yo\'q'}
🌐 Til: {user.lang.upper()}
📋 Hozirgi rol: {current_role}
📅 Ro'yxatdan o'tgan: {user.date_joined.strftime('%Y-%m-%d')}

Yangi rolni tanlang:
""",
        'ru': f"""
👤 <b>Информация о пользователе</b>

🆔 ID: <code>{user.user_id}</code>
👤 Имя: {user.first_name or 'N/A'}
📛 Username: @{user.username or 'нет'}
🌐 Язык: {user.lang.upper()}
📋 Текущая роль: {current_role}
📅 Зарегистрирован: {user.date_joined.strftime('%Y-%m-%d')}

Выберите новую роль:
""",
        'en': f"""
👤 <b>User information</b>

🆔 ID: <code>{user.user_id}</code>
👤 Name: {user.first_name or 'N/A'}
📛 Username: @{user.username or 'none'}
🌐 Language: {user.lang.upper()}
📋 Current role: {current_role}
📅 Registered: {user.date_joined.strftime('%Y-%m-%d')}

Select new role:
"""
    }
    
    # Rol tanlash tugmalari
    role_buttons = {
        'uz': [
            [InlineKeyboardButton("👤 Oddiy foydalanuvchi", callback_data=f"set_role_{user_id}_user")],
            [InlineKeyboardButton("🚗 Kuryer", callback_data=f"set_role_{user_id}_courier")],
            [InlineKeyboardButton("👨‍⚕️ Shifokor", callback_data=f"set_role_{user_id}_doctor")],
            [InlineKeyboardButton("👑 Admin", callback_data=f"set_role_{user_id}_admin")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="users_management")]
        ],
        'ru': [
            [InlineKeyboardButton("👤 Обычный пользователь", callback_data=f"set_role_{user_id}_user")],
            [InlineKeyboardButton("🚗 Курьер", callback_data=f"set_role_{user_id}_courier")],
            [InlineKeyboardButton("👨‍⚕️ Врач", callback_data=f"set_role_{user_id}_doctor")],
            [InlineKeyboardButton("👑 Админ", callback_data=f"set_role_{user_id}_admin")],
            [InlineKeyboardButton("🔙 Назад", callback_data="users_management")]
        ],
        'en': [
            [InlineKeyboardButton("👤 Regular user", callback_data=f"set_role_{user_id}_user")],
            [InlineKeyboardButton("🚗 Courier", callback_data=f"set_role_{user_id}_courier")],
            [InlineKeyboardButton("👨‍⚕️ Doctor", callback_data=f"set_role_{user_id}_doctor")],
            [InlineKeyboardButton("👑 Admin", callback_data=f"set_role_{user_id}_admin")],
            [InlineKeyboardButton("🔙 Back", callback_data="users_management")]
        ]
    }
    
    await query.edit_message_text(
        text.get(lang, text['uz']),
        reply_markup=InlineKeyboardMarkup(role_buttons.get(lang, role_buttons['uz'])),
        parse_mode='HTML'
    )
    return ConversationHandler.END


@admin_required
async def set_user_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User rolini o'zgartirish"""
    query = update.callback_query
    await query.answer()
    
    # Callback data: set_role_{user_id}_{new_role}
    parts = query.data.split('_')
    user_id = int(parts[2])
    new_role = parts[3]
    
    lang = context.user_data.get('lang', 'uz')
    
    # Userni olish va yangilash
    try:
        user = await sync_to_async(TelegramUser.objects.get)(user_id=user_id)
        old_role = user.role
        user.role = new_role
        
        # Agar admin qilinsa
        if new_role == 'admin':
            user.is_admin = True
        elif old_role == 'admin':
            user.is_admin = False
        
        await sync_to_async(user.save)(update_fields=['role', 'is_admin'])
        
        # Muvaffaqiyat xabari
        role_labels = {
            'uz': {'user': 'Oddiy foydalanuvchi', 'courier': 'Kuryer', 'doctor': 'Shifokor', 'admin': 'Admin'},
            'ru': {'user': 'Обычный пользователь', 'courier': 'Курьер', 'doctor': 'Врач', 'admin': 'Админ'},
            'en': {'user': 'Regular user', 'courier': 'Courier', 'doctor': 'Doctor', 'admin': 'Admin'}
        }
        
        success_text = {
            'uz': f"✅ {user.first_name or user.user_id} ning roli <b>{role_labels['uz'][new_role]}</b> ga o'zgartirildi!",
            'ru': f"✅ Роль пользователя {user.first_name or user.user_id} изменена на <b>{role_labels['ru'][new_role]}</b>!",
            'en': f"✅ User {user.first_name or user.user_id} role changed to <b>{role_labels['en'][new_role]}</b>!"
        }
        
        await query.edit_message_text(
            success_text.get(lang, success_text['uz']),
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t("btn_back", lang), callback_data="users_management")
            ]])
        )
        
        # Foydalanuvchiga xabar yuborish
        try:
            notification_text = {
                'uz': f"🎉 Sizning rolingiz <b>{role_labels['uz'][new_role]}</b> ga o'zgartirildi!",
                'ru': f"🎉 Ваша роль изменена на <b>{role_labels['ru'][new_role]}</b>!",
                'en': f"🎉 Your role has been changed to <b>{role_labels['en'][new_role]}</b>!"
            }
            user_lang = user.lang or 'uz'
            await context.bot.send_message(
                chat_id=user_id,
                text=notification_text.get(user_lang, notification_text['uz']),
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"Foydalanuvchiga xabar yuborishda xato: {e}")
        
    except TelegramUser.DoesNotExist:
        error_text = {
            'uz': "❌ Foydalanuvchi topilmadi.",
            'ru': "❌ Пользователь не найден.",
            'en': "❌ User not found."
        }
        await query.edit_message_text(error_text.get(lang, error_text['uz']))
    
    return ConversationHandler.END
