# full_bot.py
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# -------------------------
# Настройки
# -------------------------
TOKEN = "8383636698:AAFPUOLPIuIZS-l0PUWkjN5PjMdd6WyldxA"
bot = telebot.TeleBot(TOKEN)

ADMIN_PASSWORD = "7422"
CREATOR_ID = 8299510214 # 8299510214

# -------------------------
# Хранилище (в памяти)
# -------------------------
users = {}      # user_id -> {"nickname","desc","gems","stars","gifts":[], "chats": set(), "tick":bool}
chats = {}      # chat_name -> {"admin": user_id, "members": set(), "messages": [], "banned": False, "decorations": []}
personal_chats = {}    # user_id -> partner_id
admin_access = {}      # user_id -> True (временный доступ к админке)
admin_pending = {}     # user_id -> pending dict for multi-step actions

# -------------------------
# Магазин (подарки - для пользователей, украшения - для чатов)
# -------------------------
gift_store = {
    "🧸": {"price": 10, "desc": "Подарок — мягкая игрушка для пользователя"},
    "♥️": {"price": 20, "desc": "Подарок — сердечко, показывает внимание"},
    "🚀": {"price": 50, "desc": "Подарок — ракета, праздничный эффект"},
    "🏆": {"price": 70, "desc": "Подарок — кубок победителя"},
    "⚽": {"price": 30, "desc": "Подарок — футбольный мяч"}
}
decor_store = {
    "🖼️": {"price": 10, "desc": "Украшение для чата — картина"},
    "👑": {"price": 20, "desc": "Украшение для чата — корона"},
    "🪞": {"price": 25, "desc": "Украшение для чата — зеркало"},
    "🏅": {"price": 40, "desc": "Украшение для чата — медаль"},
    "🎍": {"price": 15, "desc": "Украшение для чата — новогоднее"},
    "⚜️": {"price": 35, "desc": "Украшение для чата — элегантный символ"},
    "💎": {"price": 100, "desc": "Украшение для чата — бриллиант"},
    "🎄": {"price": 30, "desc": "Украшение для чата — ёлка"},
    "💍": {"price": 80, "desc": "Украшение для чата — кольцо"},
    "🌲": {"price": 20, "desc": "Украшение для чата — природный декор"}
}

# пакеты гемов (только кнопки, покупка реализована сообщением)
gems_packages = {
    "pkg_100": {"gems": 100, "stars": 10, "label": "100 gems — 10 ⭐"},
    "pkg_500": {"gems": 500, "stars": 30, "label": "500 gems — 30 ⭐"},
    "pkg_1000": {"gems": 1000, "stars": 50, "label": "1000 gems — 50 ⭐"},
}

# правила
MAX_DECOR = 5
DECOR_LEVEL_MULTIPLIER = 1.5  # каждый декор = +1.5 уровня

# -------------------------
# Вспомогательные функции
# -------------------------
def ensure_user(uid, username=None):
    if uid not in users:
        users[uid] = {
            "nickname": username or f"User{uid}",
            "desc": "",
            "gems": 0,
            "stars": 0,
            "gifts": [],
            "chats": set(),
            "tick": False  # верификация
        }

def user_display(uid):
    u = users.get(uid)
    if not u:
        return f"User{uid}"
    mark = "✅" if u.get("tick") else ""
    return f"{u['nickname']} {mark}".strip()

def chat_display_name(cname):
    c = chats.get(cname)
    if not c:
        return cname
    decs = c.get("decorations", [])
    if decs:
        return f"{cname} " + "".join(decs)
    return cname

def chat_level(cname):
    c = chats.get(cname)
    if not c:
        return 0.0
    cnt = len(c.get("decorations", []))
    return cnt * DECOR_LEVEL_MULTIPLIER

def list_users_buttons(prefix):
    markup = InlineKeyboardMarkup()
    if not users:
        markup.add(InlineKeyboardButton("Нет пользователей", callback_data="noop"))
        return markup
    for uid, info in users.items():
        label = f"{info['nickname']} (g:{info['gems']} s:{info['stars']})"
        markup.add(InlineKeyboardButton(label, callback_data=f"{prefix}{uid}"))
    return markup

def list_chats_buttons(prefix):
    markup = InlineKeyboardMarkup()
    if not chats:
        markup.add(InlineKeyboardButton("Нет чатов", callback_data="noop"))
        return markup
    for cname, info in chats.items():
        banned_mark = " (забанен)" if info.get("banned") else ""
        display = f"{cname}{banned_mark}"
        markup.add(InlineKeyboardButton(display, callback_data=f"{prefix}{cname}"))
    return markup

# -------------------------
# Команды: старт/хелп
# -------------------------
@bot.message_handler(commands=["start"])
def cmd_start(message):
    global CREATOR_ID
    uid = message.from_user.id
    ensure_user(uid, message.from_user.username)
    if CREATOR_ID is None:
        CREATOR_ID = uid
    bot.reply_to(message, "Привет! Используй /help для списка команд.")

@bot.message_handler(commands=["help"])
def cmd_help(message):
    help_text = (
        "/new_chat <название> — создать чат\n"
        "/all_chats — список всех чатов (вступить нажатием)\n"
        "/chat — ваши чаты\n"
        "/delete_chat — удалить ваш чат\n"
        "/message — отправить сообщение в чате\n"
        "/profile — показать профиль\n"
        "/shop — магазин подарков/украшений\n"
        "/shop_gems — покупка гемов (инструкция)\n"
        "/give \"ник\" — подарить подарок\n"
        "/sell — продать свой подарок\n"
        "/chatD \"название\" — информация о чате\n"
        "/settings_chat \"название\" — настройки чата (только админ)\n"
        "/admin_panel — админ-панель (пароль)\n"
        "/admin_panel_chat — админ-панель для админов чатов\n"
        "/ls \"ник\" — ЛС (есть предупреждение)\n"
        "/t <сообщение> — отправить ЛС\n"
        "/bye \"ник\" — закрыть ЛС\n"
    )
    bot.reply_to(message, help_text)

# -------------------------
# Профиль
# -------------------------
@bot.message_handler(commands=["profile"])
def cmd_profile(message):
    uid = message.from_user.id
    ensure_user(uid, message.from_user.username)
    u = users[uid]
    tick = "✅" if u.get("tick") else "🚫"
    gifts = " ".join(u["gifts"]) if u["gifts"] else "нет"
    text = (
        f"Профиль:\nНик: {u['nickname']} {tick}\n"
        f"Описание: {u['desc']}\n"
        f"Верификация: {tick}\n"
        f"Гемы: {u['gems']}\n"
        f"Звезды: {u['stars']}\n"
        f"Подарки: {gifts}"
    )
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Изменить ник", callback_data="edit_nick"))
    markup.add(InlineKeyboardButton("Изменить описание", callback_data="edit_desc"))
    markup.add(InlineKeyboardButton("Поставить/Убрать галочку", callback_data="toggle_tick"))
    bot.send_message(uid, text, reply_markup=markup)

# -------------------------
# Чаты: создание, список, вход, удалить, информация
# -------------------------
@bot.message_handler(commands=["new_chat"])
def cmd_new_chat(message):
    uid = message.from_user.id
    ensure_user(uid, message.from_user.username)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        bot.reply_to(message, "Использование: /new_chat Название")
        return
    name = parts[1].strip()
    if name in chats:
        bot.reply_to(message, "Чат с таким названием уже существует.")
        return
    chats[name] = {"admin": uid, "members": {uid}, "messages": [], "banned": False, "decorations": []}
    users[uid]["chats"].add(name)
    users[uid]["tick"] = True
    bot.reply_to(message, f"Чат '{name}' создан! Вы — админ.")

@bot.message_handler(commands=["all_chats"])
def cmd_all_chats(message):
    ensure_user(message.from_user.id, message.from_user.username)
    if not chats:
        bot.reply_to(message, "Чатов пока нет.")
        return
    bot.send_message(message.from_user.id, "Список чатов (нажми чтобы вступить):", reply_markup=list_chats_buttons("join_"))

@bot.message_handler(commands=["chat"])
def cmd_user_chats(message):
    uid = message.from_user.id
    ensure_user(uid, message.from_user.username)
    my = users[uid]["chats"]
    if not my:
        bot.reply_to(message, "Вы не состоите ни в одном чате.")
        return
    markup = InlineKeyboardMarkup()
    for c in my:
        markup.add(InlineKeyboardButton(chat_display_name(c), callback_data=f"viewchat_{c}"))
    bot.send_message(uid, "Ваши чаты:", reply_markup=markup)

@bot.message_handler(commands=["delete_chat"])
def cmd_delete_chat(message):
    uid = message.from_user.id
    ensure_user(uid, message.from_user.username)
    my_admin = [c for c in users[uid]["chats"] if chats.get(c, {}).get("admin") == uid]
    if not my_admin:
        bot.reply_to(message, "У вас нет чатов для удаления.")
        return
    markup = InlineKeyboardMarkup()
    for c in my_admin:
        markup.add(InlineKeyboardButton(c, callback_data=f"delete_{c}"))
    bot.send_message(uid, "Выберите чат для удаления:", reply_markup=markup)

@bot.message_handler(commands=["message"])
def cmd_message(message):
    uid = message.from_user.id
    ensure_user(uid, message.from_user.username)
    my = users[uid]["chats"]
    if not my:
        bot.reply_to(message, "Вы не состоите ни в одном чате.")
        return
    markup = InlineKeyboardMarkup()
    for c in my:
        markup.add(InlineKeyboardButton(chat_display_name(c), callback_data=f"sendmsg_{c}"))
    bot.send_message(uid, "Выберите чат для отправки сообщения:", reply_markup=markup)

@bot.message_handler(commands=["chatD"])
def cmd_chatD(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, 'Использование: /chatD "название чата"')
        return
    cname = parts[1].strip().strip('"')
    if cname not in chats:
        bot.reply_to(message, "Чат не найден.")
        return
    c = chats[cname]
    members = c["members"]
    admin_uid = c["admin"]
    banned = c.get("banned", False)
    decs = c.get("decorations", [])
    level = chat_level(cname)
    text = (
        f"Информация о чате:\n"
        f"Название: {chat_display_name(cname)}\n"
        f"Участники ({len(members)}): {', '.join(user_display(uid) for uid in members)}\n"
        f"Админ: {user_display(admin_uid)}\n"
        f"Забанен: {'Да' if banned else 'Нет'}\n"
        f"Украшения ({len(decs)}/{MAX_DECOR}): {' '.join(decs) if decs else 'нет'}\n"
        f"Уровень: {level}"
    )
    bot.send_message(message.from_user.id, text)

# -------------------------
# Shop: вывод товаров + кнопки
# -------------------------
@bot.message_handler(commands=["shop"])
def cmd_shop(message):
    uid = message.from_user.id
    ensure_user(uid, message.from_user.username)
    text = "🎁 Магазин подарков (для пользователей):\n"
    for g,v in gift_store.items():
        text += f"{g} — {v['price']} gems — {v['desc']}\n"
    text += "\n🎨 Магазин украшений (для чатов):\n"
    for d,v in decor_store.items():
        text += f"{d} — {v['price']} gems — {v['desc']}\n"
    bot.send_message(uid, text)

    # Кнопки — подарки и украшения
    markup = InlineKeyboardMarkup()
    for g in gift_store:
        markup.add(InlineKeyboardButton(f"Купить {g} ({gift_store[g]['price']}g)", callback_data=f"buy_gift_{g}"))
    for d in decor_store:
        markup.add(InlineKeyboardButton(f"Купить {d} ({decor_store[d]['price']}g)", callback_data=f"buy_decor_{d}"))
    bot.send_message(uid, "Выберите покупку:", reply_markup=markup)

# shop_gems — не продаём в боте, даём инструкцию
@bot.message_handler(commands=["shop_gems"])
def cmd_shop_gems(message):
    uid = message.from_user.id
    ensure_user(uid, message.from_user.username)
    bot.send_message(uid, "К сожалению гемы нельзя купить в боте, покупайте лично с создателем @Edikoffe_4")

# -------------------------
# Sell — продать подарок за 50% цены
# -------------------------
@bot.message_handler(commands=["sell"])
def cmd_sell(message):
    uid = message.from_user.id
    ensure_user(uid, message.from_user.username)
    gifts = users[uid]["gifts"]
    if not gifts:
        bot.reply_to(message, "У вас нет подарков.")
        return
    markup = InlineKeyboardMarkup()
    used = set()
    for g in gifts:
        if g in used:
            continue
        used.add(g)
        price = gift_store[g]["price"] // 2
        markup.add(InlineKeyboardButton(f"Продать {g} — {price}g", callback_data=f"sell_{g}"))
    bot.send_message(uid, "Выберите подарок для продажи:", reply_markup=markup)

# -------------------------
# Give — подарить другому
# -------------------------
@bot.message_handler(commands=["give"])
def cmd_give(message):
    uid = message.from_user.id
    ensure_user(uid, message.from_user.username)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, 'Использование: /give "ник"')
        return
    target_nick = parts[1].strip().strip('"')
    target_id = None
    for tid, info in users.items():
        if info["nickname"] == target_nick:
            target_id = tid
            break
    if not target_id:
        bot.reply_to(message, "Пользователь не найден.")
        return
    markup = InlineKeyboardMarkup()
    for g in gift_store:
        markup.add(InlineKeyboardButton(f"{g} — {gift_store[g]['price']}g", callback_data=f"giftsend_{target_id}_{g}"))
    bot.send_message(uid, f"Выберите подарок для {target_nick}:", reply_markup=markup)

# -------------------------
# Личные сообщения: /ls, /t, /bye
# -------------------------
@bot.message_handler(commands=["ls"])
def cmd_ls(message):
    uid = message.from_user.id
    ensure_user(uid, message.from_user.username)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, 'Использование: /ls "ник"')
        return
    bot.reply_to(message, "Внимание! Личные Сообщения могут не работать!")
    target_nick = parts[1].strip().strip('"')
    target_id = None
    for tid, info in users.items():
        if info["nickname"] == target_nick:
            target_id = tid
            break
    if not target_id:
        bot.reply_to(message, "Пользователь не найден.")
        return
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Общаться", callback_data=f"pm_{target_id}"))
    bot.send_message(uid, f'Найден пользователь "{target_nick}"', reply_markup=markup)

@bot.message_handler(commands=["t"])
def cmd_t(message):
    uid = message.from_user.id
    ensure_user(uid, message.from_user.username)
    if uid not in personal_chats:
        bot.reply_to(message, "У вас нет открытого ЛС. Используйте /ls")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Использование: /t <сообщение>")
        return
    target = personal_chats[uid]
    text = parts[1]
    bot.send_message(target, f"[ЛС] {user_display(uid)}: {text}")
    bot.reply_to(message, "Сообщение отправлено!")

@bot.message_handler(commands=["bye"])
def cmd_bye(message):
    uid = message.from_user.id
    ensure_user(uid, message.from_user.username)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, 'Использование: /bye "ник"')
        return
    target_nick = parts[1].strip().strip('"')
    target = None
    for tid, info in users.items():
        if info["nickname"] == target_nick:
            target = tid
            break
    if not target or personal_chats.get(uid) != target:
        bot.reply_to(message, "ЛС не найдено.")
        return
    del personal_chats[uid]
    if target in personal_chats:
        del personal_chats[target]
    bot.send_message(uid, f"Вы закрыли ЛС с {target_nick}")
    bot.send_message(target, f"{user_display(uid)} закрыл ЛС с вами")

# -------------------------
# Settings chat: переименовать, назначить админа (только админ чата)
# -------------------------
@bot.message_handler(commands=["settings_chat"])
def cmd_settings_chat(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, 'Использование: /settings_chat "название чата"')
        return
    cname = parts[1].strip().strip('"')
    if cname not in chats:
        bot.reply_to(message, "Чат не найден.")
        return
    uid = message.from_user.id
    ensure_user(uid, message.from_user.username)
    if chats[cname]["admin"] != uid and uid != CREATOR_ID:
        bot.reply_to(message, "Только админ чата может менять настройки.")
        return
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Переименовать чат", callback_data=f"settings_rename_{cname}"))
    markup.add(InlineKeyboardButton("Назначить админа", callback_data=f"settings_setadmin_{cname}"))
    bot.send_message(uid, f"Настройки чата '{cname}':", reply_markup=markup)

# -------------------------
# Admin panel (global)
# -------------------------
@bot.message_handler(commands=["admin_panel"])
def cmd_admin_panel(message):
    uid = message.from_user.id
    ensure_user(uid, message.from_user.username)
    msg = bot.send_message(uid, "Введите пароль для доступа к админ-панели:")
    bot.register_next_step_handler(msg, admin_password_step)

def admin_password_step(message):
    uid = message.from_user.id
    text = message.text.strip()
    if text == ADMIN_PASSWORD or (CREATOR_ID is not None and uid == CREATOR_ID):
        admin_access[uid] = True
        send_admin_menu(uid)
    else:
        bot.reply_to(message, "Неверный пароль.")

def send_admin_menu(uid):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Баны: пользователи", callback_data="admin_ban_users"))
    markup.add(InlineKeyboardButton("Баны: чаты", callback_data="admin_ban_chats"))
    markup.add(InlineKeyboardButton("Начислить/снять гемы", callback_data="admin_balance"))
    markup.add(InlineKeyboardButton("Список пользователей", callback_data="admin_list_users"))
    bot.send_message(uid, "Админ-панель:", reply_markup=markup)

# -------------------------
# Admin panel for chat admins: /admin_panel_chat
# -------------------------
@bot.message_handler(commands=["admin_panel_chat"])
def cmd_admin_panel_chat(message):
    uid = message.from_user.id
    ensure_user(uid, message.from_user.username)
    # find chats where user is admin
    my_admin = [c for c, info in chats.items() if info.get("admin") == uid]
    if not my_admin:
        bot.reply_to(message, "Вы не являетесь админом ни одного чата.")
        return
    markup = InlineKeyboardMarkup()
    for c in my_admin:
        markup.add(InlineKeyboardButton(c, callback_data=f"apc_{c}"))
    bot.send_message(uid, "Выберите чат для админ-действий:", reply_markup=markup)

# -------------------------
# Единый обработчик callback'ов
# -------------------------
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid = call.from_user.id
    ensure_user(uid, call.from_user.username)
    data = call.data

    # noop
    if data == "noop":
        bot.answer_callback_query(call.id, "")
        return

    # JOIN chat
    if data.startswith("join_"):
        cname = data[5:]
        if cname in chats:
            if users[uid].get("banned"):
                bot.answer_callback_query(call.id, "Вы забанены и не можете вступить.")
                return
            if chats[cname].get("banned"):
                bot.answer_callback_query(call.id, "Этот чат заблокирован.")
                return
            chats[cname]["members"].add(uid)
            users[uid]["chats"].add(cname)
            bot.answer_callback_query(call.id, f"Вы присоединились к {chat_display_name(cname)}")
        return

    # VIEW chat members (from /chat)
    if data.startswith("viewchat_"):
        cname = data[9:]
        if cname in chats:
            members = chats[cname]["members"]
            names = ", ".join(user_display(m) for m in members) or "нет участников"
            bot.send_message(uid, f"Чат '{chat_display_name(cname)}'\nУчастники: {names}")
        return

    # DELETE chat (admin)
    if data.startswith("delete_"):
        cname = data[7:]
        if cname in chats and chats[cname]["admin"] == uid:
            for m in chats[cname]["members"]:
                users[m]["chats"].discard(cname)
            del chats[cname]
            bot.answer_callback_query(call.id, f"Чат '{cname}' удалён")
        else:
            bot.answer_callback_query(call.id, "Только админ может удалить чат.")
        return

    # SEND message (start flow)
    if data.startswith("sendmsg_"):
        cname = data[8:]
        if cname not in chats:
            bot.answer_callback_query(call.id, "Чат не найден.")
            return
        msg = bot.send_message(uid, f"Введите сообщение для чата '{chat_display_name(cname)}':")
        bot.register_next_step_handler(msg, send_message_step, cname)
        bot.answer_callback_query(call.id, "")
        return

    # BUY gift
    if data.startswith("buy_gift_"):
        g = data[len("buy_gift_"):]
        item = gift_store.get(g)
        if not item:
            bot.answer_callback_query(call.id, "Товар не найден.")
            return
        price = item["price"]
        if users[uid]["gems"] < price:
            bot.answer_callback_query(call.id, "Недостаточно gems.")
            return
        users[uid]["gems"] -= price
        users[uid]["gifts"].append(g)
        bot.answer_callback_query(call.id, f"Куплено {g} — {item['desc']}")
        bot.send_message(uid, f"Вы купили {g}: {item['desc']} (списано {price} gems).")
        return

    # BUY decor — start flow: choose chat to apply
    if data.startswith("buy_decor_"):
        d = data[len("buy_decor_"):]
        item = decor_store.get(d)
        if not item:
            bot.answer_callback_query(call.id, "Товар не найден.")
            return
        price = item["price"]
        user_chats = list(users[uid]["chats"])
        if not user_chats:
            bot.answer_callback_query(call.id, "У вас нет чатов для украшения.")
            return
        # show user's chats — will check limit when applying
        markup = InlineKeyboardMarkup()
        for c in user_chats:
            markup.add(InlineKeyboardButton(chat_display_name(c), callback_data=f"apply_decor_{d}|{c}"))
        bot.send_message(uid, f"Выберите чат для установки {d} — {item['desc']} (цена {price}g):", reply_markup=markup)
        bot.answer_callback_query(call.id, "")
        return

    # APPLY decor to specific chat
    if data.startswith("apply_decor_"):
        rest = data[len("apply_decor_"):]
        try:
            d, cname = rest.split("|", 1)
        except:
            bot.answer_callback_query(call.id, "Ошибка данных.")
            return
        if d not in decor_store:
            bot.answer_callback_query(call.id, "Украшение не найдено.")
            return
        if cname not in chats:
            bot.answer_callback_query(call.id, "Чат не найден.")
            return
        price = decor_store[d]["price"]
        if users[uid]["gems"] < price:
            bot.answer_callback_query(call.id, "Недостаточно gems.")
            return
        decorations = chats[cname].get("decorations", [])
        if len(decorations) >= MAX_DECOR:
            bot.answer_callback_query(call.id, f"У этого чата уже максимум украшений ({MAX_DECOR}/{MAX_DECOR})!")
            return
        users[uid]["gems"] -= price
        decorations.append(d)
        chats[cname]["decorations"] = decorations
        bot.answer_callback_query(call.id, f"{d} применено в чате '{cname}' (списано {price}g).")
        # notify members
        for m in chats[cname]["members"]:
            try:
                bot.send_message(m, f"✨ В чате '{cname}' появилось украшение: {d}")
            except:
                pass
        return

    # SEND gift to another user (flow from /give)
    if data.startswith("giftsend_"):
        try:
            _, target_str, g = data.split("_", 2)
            target = int(target_str)
        except:
            bot.answer_callback_query(call.id, "Ошибка.")
            return
        if g not in gift_store:
            bot.answer_callback_query(call.id, "Подарок не найден.")
            return
        price = gift_store[g]["price"]
        if users[uid]["gems"] < price:
            bot.answer_callback_query(call.id, "Недостаточно gems.")
            return
        users[uid]["gems"] -= price
        users[target]["gifts"].append(g)
        bot.answer_callback_query(call.id, f"Вы отправили {g} пользователю {users[target]['nickname']}.")
        bot.send_message(target, f"🎁 Пользователь {user_display(uid)} подарил вам {g}!\n{gift_store[g]['desc']}")
        bot.send_message(uid, f"Вы отправили {g} пользователю {users[target]['nickname']} (списано {price}g).")
        return

    # SELL gift
    if data.startswith("sell_"):
        g = data[len("sell_"):]
        if g not in users[uid]["gifts"]:
            bot.answer_callback_query(call.id, "У вас нет такого подарка.")
            return
        price = gift_store.get(g, {}).get("price", 0) // 2
        users[uid]["gifts"].remove(g)
        users[uid]["gems"] += price
        bot.answer_callback_query(call.id, f"Вы продали {g} за {price}g.")
        bot.send_message(uid, f"Подарок {g} продан — вы получили {price} gems.")
        return

    # BUY package of gems (donate) — just message
    if data.startswith("buy_pkg_"):
        bot.answer_callback_query(call.id, "")
        bot.send_message(uid, "К сожалению гемы нельзя купить в боте, покупайте лично с создателем @Edikoffe_4")
        return

    # PM open
    if data.startswith("pm_"):
        target = int(data[3:])
        personal_chats[uid] = target
        personal_chats[target] = uid
        bot.answer_callback_query(call.id, "Личный чат открыт.")
        bot.send_message(uid, f"Вы начали личный чат с {user_display(target)}")
        bot.send_message(target, f"{user_display(uid)} начал с вами ЛС")
        return

    # SETTINGS: rename chat (from /settings_chat)
    if data.startswith("settings_rename_"):
        cname = data[len("settings_rename_"):]
        if cname not in chats:
            bot.answer_callback_query(call.id, "Чат не найден.")
            return
        if chats[cname]["admin"] != uid and uid != CREATOR_ID:
            bot.answer_callback_query(call.id, "Только админ чата может переименовать.")
            return
        admin_pending[uid] = {"action": "rename_chat", "chat": cname}
        msg = bot.send_message(uid, f"Введите новое название для чата '{cname}':")
        bot.register_next_step_handler(msg, admin_rename_step)
        bot.answer_callback_query(call.id, "")
        return

    # SETTINGS: set admin
    if data.startswith("settings_setadmin_"):
        cname = data[len("settings_setadmin_"):]
        if cname not in chats:
            bot.answer_callback_query(call.id, "Чат не найден.")
            return
        if chats[cname]["admin"] != uid and uid != CREATOR_ID:
            bot.answer_callback_query(call.id, "Только админ чата может назначить админа.")
            return
        bot.send_message(uid, "Выберите пользователя для назначения админом:", reply_markup=list_users_buttons(f"setadmin_{cname}_"))
        bot.answer_callback_query(call.id, "")
        return

    if data.startswith("setadmin_"):
        rest = data[len("setadmin_"):]
        try:
            cname, target_str = rest.split("_", 1)
            target = int(target_str)
        except:
            bot.answer_callback_query(call.id, "Ошибка.")
            return
        if cname not in chats or target not in users:
            bot.answer_callback_query(call.id, "Ошибка данных.")
            return
        if chats[cname]["admin"] != uid and uid != CREATOR_ID:
            bot.answer_callback_query(call.id, "Только админ чата может назначить админа.")
            return
        chats[cname]["admin"] = target
        bot.answer_callback_query(call.id, f"{user_display(target)} теперь админ чата '{cname}'.")
        bot.send_message(target, f"Вас назначили админом чата '{cname}'.")
        return

    # ADMIN PANEL: global
    if data == "admin_ban_users":
        if not admin_access.get(uid):
            bot.answer_callback_query(call.id, "Нет доступа!")
            return
        bot.send_message(uid, "Выберите пользователя для бана/разбана:", reply_markup=list_users_buttons("admin_toggle_ban_"))
        return

    if data.startswith("admin_toggle_ban_"):
        if not admin_access.get(uid):
            bot.answer_callback_query(call.id, "Нет доступа!")
            return
        target = int(data[len("admin_toggle_ban_"):])
        if target in users:
            if users[target].get("banned"):
                users[target].pop("banned", None)
                bot.answer_callback_query(call.id, f"{users[target]['nickname']} разбанен.")
            else:
                users[target]["banned"] = True
                bot.answer_callback_query(call.id, f"{users[target]['nickname']} забанен.")
        else:
            bot.answer_callback_query(call.id, "Пользователь не найден.")
        return

    if data == "admin_ban_chats":
        if not admin_access.get(uid):
            bot.answer_callback_query(call.id, "Нет доступа!")
            return
        bot.send_message(uid, "Выберите чат для бана/разбана:", reply_markup=list_chats_buttons("admin_toggle_ban_chat_"))
        return

    if data.startswith("admin_toggle_ban_chat_"):
        if not admin_access.get(uid):
            bot.answer_callback_query(call.id, "Нет доступа!")
            return
        cname = data[len("admin_toggle_ban_chat_"):]
        if cname in chats:
            chats[cname]["banned"] = not chats[cname].get("banned", False)
            bot.answer_callback_query(call.id, f"Статус чата {cname}: {'Забанен' if chats[cname]['banned'] else 'Активен'}")
        else:
            bot.answer_callback_query(call.id, "Чат не найден.")
        return

    if data == "admin_balance":
        if not admin_access.get(uid):
            bot.answer_callback_query(call.id, "Нет доступа!")
            return
        bot.send_message(uid, "Выберите пользователя для изменения баланса:", reply_markup=list_users_buttons("admin_balance_user_"))
        return

    if data.startswith("admin_balance_user_"):
        if not admin_access.get(uid):
            bot.answer_callback_query(call.id, "Нет доступа!")
            return
        target = int(data[len("admin_balance_user_"):])
        admin_pending[uid] = {"action": "balance_set", "target": target}
        msg = bot.send_message(uid, f"Введите число (напр. 100 или -50) для пользователя {users[target]['nickname']}:")
        bot.register_next_step_handler(msg, admin_balance_amount_step)
        return

    if data == "admin_list_users":
        if not admin_access.get(uid):
            bot.answer_callback_query(call.id, "Нет доступа!")
            return
        txt = "Пользователи:\n"
        for tid, info in users.items():
            txt += f"{info['nickname']} — gems:{info['gems']} stars:{info['stars']} gifts:{' '.join(info['gifts']) if info['gifts'] else 'нет'}\n"
        bot.send_message(uid, txt)
        return

    # Admin panel chat (apc_) — choose chat then actions
    if data.startswith("apc_"):
        cname = data[len("apc_"):]
        if cname not in chats:
            bot.answer_callback_query(call.id, "Чат не найден.")
            return
        if chats[cname]["admin"] != uid and uid != CREATOR_ID:
            bot.answer_callback_query(call.id, "Только админ чата может управлять этим меню.")
            return
        # menu: ban/unban chat, ban/unban users, rename, delete
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Забанить/Разбанить чат", callback_data=f"apc_toggle_ban_{cname}"))
        markup.add(InlineKeyboardButton("Забанить пользователя в чате", callback_data=f"apc_ban_user_{cname}"))
        markup.add(InlineKeyboardButton("Разбанить пользователя в чате", callback_data=f"apc_unban_user_{cname}"))
        markup.add(InlineKeyboardButton("Переименовать чат", callback_data=f"apc_rename_{cname}"))
        markup.add(InlineKeyboardButton("Удалить чат", callback_data=f"apc_delete_{cname}"))
        bot.send_message(uid, f"Панель админа чата '{cname}':", reply_markup=markup)
        bot.answer_callback_query(call.id, "")
        return

    # apc_toggle_ban
    if data.startswith("apc_toggle_ban_"):
        cname = data[len("apc_toggle_ban_"):]
        if cname not in chats:
            bot.answer_callback_query(call.id, "Чат не найден.")
            return
        if chats[cname]["admin"] != uid and uid != CREATOR_ID:
            bot.answer_callback_query(call.id, "Только админ чата может выполнять это.")
            return
        chats[cname]["banned"] = not chats[cname].get("banned", False)
        bot.answer_callback_query(call.id, f"Статус чата {cname}: {'Забанен' if chats[cname]['banned'] else 'Активен'}")
        return

    # apc_ban_user -> show list of members to ban
    if data.startswith("apc_ban_user_"):
        cname = data[len("apc_ban_user_"):]
        if cname not in chats:
            bot.answer_callback_query(call.id, "Чат не найден.")
            return
        if chats[cname]["admin"] != uid and uid != CREATOR_ID:
            bot.answer_callback_query(call.id, "Только админ чата может выполнять это.")
            return
        members = chats[cname]["members"]
        if not members:
            bot.answer_callback_query(call.id, "В чате нет участников.")
            return
        markup = InlineKeyboardMarkup()
        for m in members:
            markup.add(InlineKeyboardButton(user_display(m), callback_data=f"apc_ban_user_do_{cname}_{m}"))
        bot.send_message(uid, "Выберите участника для бана в чате:", reply_markup=markup)
        return

    if data.startswith("apc_ban_user_do_"):
        rest = data[len("apc_ban_user_do_"):]
        try:
            cname, mid_str = rest.rsplit("_", 1)
            mid = int(mid_str)
        except:
            bot.answer_callback_query(call.id, "Ошибка.")
            return
        if cname not in chats or mid not in users:
            bot.answer_callback_query(call.id, "Данные неверны.")
            return
        # mark user banned globally (or per-chat? spec said ban users; implement global ban)
        users[mid]["banned"] = True
        bot.answer_callback_query(call.id, f"{user_display(mid)} забанен.")
        bot.send_message(mid, f"Вы были забанены админом чата '{cname}'.")
        return

    # apc_unban_user -> show banned users list (global)
    if data.startswith("apc_unban_user_"):
        cname = data[len("apc_unban_user_"):]
        if cname not in chats:
            bot.answer_callback_query(call.id, "Чат не найден.")
            return
        if chats[cname]["admin"] != uid and uid != CREATOR_ID:
            bot.answer_callback_query(call.id, "Только админ чата может выполнять это.")
            return
        # show users who are banned
        banned_list = [uid_ for uid_, info in users.items() if info.get("banned")]
        if not banned_list:
            bot.answer_callback_query(call.id, "Нет забаненных пользователей.")
            return
        markup = InlineKeyboardMarkup()
        for b in banned_list:
            markup.add(InlineKeyboardButton(user_display(b), callback_data=f"apc_unban_user_do_{cname}_{b}"))
        bot.send_message(uid, "Выберите пользователя для разбанивания:", reply_markup=markup)
        return

    if data.startswith("apc_unban_user_do_"):
        rest = data[len("apc_unban_user_do_"):]
        try:
            cname, mid_str = rest.rsplit("_", 1)
            mid = int(mid_str)
        except:
            bot.answer_callback_query(call.id, "Ошибка.")
            return
        if mid in users and users[mid].get("banned"):
            users[mid].pop("banned", None)
            bot.answer_callback_query(call.id, f"{users[mid]['nickname']} разбанен.")
            bot.send_message(mid, f"Вас разбанили в чате '{cname}'.")
        else:
            bot.answer_callback_query(call.id, "Пользователь не найден или не забанен.")
        return

    # apc_rename_ -> start rename flow
    if data.startswith("apc_rename_"):
        cname = data[len("apc_rename_"):]
        if cname not in chats:
            bot.answer_callback_query(call.id, "Чат не найден.")
            return
        if chats[cname]["admin"] != uid and uid != CREATOR_ID:
            bot.answer_callback_query(call.id, "Только админ чата может выполнять это.")
            return
        admin_pending[uid] = {"action": "apc_rename", "chat": cname}
        msg = bot.send_message(uid, f"Введите новое название для чата '{cname}':")
        bot.register_next_step_handler(msg, admin_rename_step)
        bot.answer_callback_query(call.id, "")
        return

    # apc_delete_ -> delete chat
    if data.startswith("apc_delete_"):
        cname = data[len("apc_delete_"):]
        if cname not in chats:
            bot.answer_callback_query(call.id, "Чат не найден.")
            return
        if chats[cname]["admin"] != uid and uid != CREATOR_ID:
            bot.answer_callback_query(call.id, "Только админ чата может выполнять это.")
            return
        for m in chats[cname]["members"]:
            users[m]["chats"].discard(cname)
        del chats[cname]
        bot.answer_callback_query(call.id, f"Чат '{cname}' удалён.")
        return

    # admin panel: choose user to ban/unban (global)
    if data.startswith("admin_toggle_ban_"):
        if not admin_access.get(uid):
            bot.answer_callback_query(call.id, "Нет доступа!")
            return
        target = int(data[len("admin_toggle_ban_"):])
        if target in users:
            if users[target].get("banned"):
                users[target].pop("banned", None)
                bot.answer_callback_query(call.id, f"{users[target]['nickname']} разбанен.")
            else:
                users[target]["banned"] = True
                bot.answer_callback_query(call.id, f"{users[target]['nickname']} забанен.")
        else:
            bot.answer_callback_query(call.id, "Пользователь не найден.")
        return

    # admin settings: toggle ban chat
    if data.startswith("admin_toggle_ban_chat_"):
        if not admin_access.get(uid):
            bot.answer_callback_query(call.id, "Нет доступа!")
            return
        cname = data[len("admin_toggle_ban_chat_"):]
        if cname in chats:
            chats[cname]["banned"] = not chats[cname].get("banned", False)
            bot.answer_callback_query(call.id, f"Статус чата {cname}: {'Забанен' if chats[cname]['banned'] else 'Активен'}")
        else:
            bot.answer_callback_query(call.id, "Чат не найден.")
        return

    # admin_balance_user_ (from admin_balance)
    if data.startswith("admin_balance_user_"):
        if not admin_access.get(uid):
            bot.answer_callback_query(call.id, "Нет доступа!")
            return
        target = int(data[len("admin_balance_user_"):])
        admin_pending[uid] = {"action": "balance_set", "target": target}
        msg = bot.send_message(uid, f"Введите число (напр. 100 или -50) для пользователя {users[target]['nickname']}:")
        bot.register_next_step_handler(msg, admin_balance_amount_step)
        return

    # admin list users
    if data == "admin_list_users":
        if not admin_access.get(uid):
            bot.answer_callback_query(call.id, "Нет доступа!")
            return
        txt = "Пользователи:\n"
        for tid, info in users.items():
            txt += f"{info['nickname']} — gems:{info['gems']} stars:{info['stars']} gifts:{' '.join(info['gifts']) if info['gifts'] else 'нет'}\n"
        bot.send_message(uid, txt)
        return

    # open admin menu button
    if data == "admin_open":
        if uid == CREATOR_ID or admin_access.get(uid):
            send_admin_menu(uid)
            bot.answer_callback_query(call.id, "")
        else:
            bot.answer_callback_query(call.id, "Нет доступа.")
        return

    bot.answer_callback_query(call.id, "Команда пока не реализована или ошибка данных.")

# -------------------------
# Шаги: админские операции и rename
# -------------------------
def admin_balance_amount_step(message):
    uid = message.from_user.id
    data = admin_pending.get(uid)
    if not data or data.get("action") != "balance_set":
        bot.reply_to(message, "Нет активной операции.")
        return
    target = data["target"]
    try:
        amt = int(message.text.strip())
    except:
        bot.reply_to(message, "Ошибка: введите целое число, например 100 или -50")
        return
    users[target]["gems"] = max(0, users[target]["gems"] + amt)
    bot.send_message(uid, f"Баланс {users[target]['nickname']} изменён на {amt}. Теперь: {users[target]['gems']} gems.")
    bot.send_message(target, f"Вам изменили баланс: {amt} gems. Текущий баланс: {users[target]['gems']}")
    admin_pending.pop(uid, None)

def admin_rename_step(message):
    uid = message.from_user.id
    data = admin_pending.get(uid)
    if not data or data.get("action") not in ("rename_chat", "apc_rename"):
        bot.reply_to(message, "Нет активной операции.")
        return
    old = data["chat"]
    new = message.text.strip()
    if not new:
        bot.reply_to(message, "Название не может быть пустым.")
        return
    if new in chats:
        bot.reply_to(message, "Чат с таким названием уже существует.")
        return
    # rename
    chats[new] = chats.pop(old)
    for m in chats[new]["members"]:
        if old in users[m]["chats"]:
            users[m]["chats"].remove(old)
            users[m]["chats"].add(new)
    bot.send_message(uid, f"Чат '{old}' переименован в '{new}'.")
    # notify members
    for m in chats[new]["members"]:
        try:
            bot.send_message(m, f"Чат '{old}' переименован в '{new}'.")
        except:
            pass
    admin_pending.pop(uid, None)

# -------------------------
# send message step for chats
# -------------------------
def send_message_step(message, chat_name):
    uid = message.from_user.id
    ensure_user(uid, message.from_user.username)
    if chat_name not in chats:
        bot.reply_to(message, "Чат не найден.")
        return
    if chats[chat_name].get("banned"):
        bot.reply_to(message, "Чат заблокирован.")
        return
    if users[uid].get("banned"):
        bot.reply_to(message, "Вы заблокированы админом.")
        return
    text = message.text
    if uid not in chats[chat_name]["members"]:
        chats[chat_name]["members"].add(uid)
        users[uid]["chats"].add(chat_name)
    decs = chats[chat_name].get("decorations", [])
    decs_str = "".join(decs)
    for m in list(chats[chat_name]["members"]):
        try:
            mark = " ✅" if users[uid].get("tick") else ""
            bot.send_message(m, f"[{chat_name}{(' ' + decs_str) if decs_str else ''}] {users[uid]['nickname']}{mark}: {text}")
        except Exception:
            pass
    bot.reply_to(message, "Сообщение отправлено!")

# -------------------------
# Запуск
# -------------------------
if __name__ == "__main__":
    print("Бот запущен.")
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print("Ошибка polling:", e)
            import time
            time.sleep(2)