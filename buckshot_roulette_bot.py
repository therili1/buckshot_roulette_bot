import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ігровий стан
GAMES = {}

# Стандартні предмети
ITEMS = ["аптечка", "х-рей", "свапер", "прострочена аптечка", "хапалка", "наручники", "банка з порохом"]

MAX_HP = 5
MAX_BULLETS = 8

# Клавіатури

def get_action_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔫 Вистріл", callback_data="shoot")],
        [InlineKeyboardButton("🎒 Предмет", callback_data="use_item")]
    ])

def get_back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("↩️ Назад", callback_data="back_to_action")]
    ])

# Команди

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Вітаємо у грі 'Рулетка смерті'. Використайте /join щоб приєднатися до гри.")

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id not in GAMES:
        GAMES[chat_id] = {
            'players': {},
            'queue': [],
            'current': 0,
            'state': 'waiting',
            'barrel': [],
            'current_bullet': 0,
            'powder_boost': None
        }

    game = GAMES[chat_id]
    if user.id not in game['players']:
        game['players'][user.id] = {
            'name': user.full_name,
            'hp': MAX_HP,
            'items': []
        }
        game['queue'].append(user.id)
        await update.message.reply_text(f"{user.full_name} приєднався до гри!")
    else:
        await update.message.reply_text("Ви вже в грі!")

async def begin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game = GAMES.get(chat_id)

    if not game or len(game['players']) < 2:
        await update.message.reply_text("Має бути щонайменше 2 гравці для початку гри.")
        return

    game['state'] = 'playing'
    game['barrel'] = generate_barrel()
    game['current_bullet'] = 0
    game['powder_boost'] = None
    await context.bot.send_message(chat_id, "Гру розпочато!")
    await next_turn(chat_id, context)

# Генерація ствола

def generate_barrel():
    while True:
        total = random.randint(2, MAX_BULLETS)
        num_live = random.randint(1, total)
        num_blank = total - num_live
        if num_live >= 1:
            barrel = ["live"] * num_live + ["blank"] * num_blank
            random.shuffle(barrel)
            return barrel

# Наступний хід

async def next_turn(chat_id, context):
    game = GAMES[chat_id]
    queue = game['queue']
    player_id = queue[game['current'] % len(queue)]
    player = game['players'][player_id]
    game['state'] = 'await_action'

    await context.bot.send_message(player_id, f"Ваш хід, {player['name']}! Оберіть дію:", reply_markup=get_action_keyboard())

# Обробка натискань

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    game = None
    for gid, g in GAMES.items():
        if user_id in g['players']:
            game = g
            chat_id = gid
            break

    if not game:
        await query.edit_message_text("Гру не знайдено.")
        return

    if data == "shoot":
        await shoot(chat_id, user_id, context)
    elif data == "use_item":
        player = game['players'][user_id]
        if not player['items']:
            await query.edit_message_text("У вас немає предметів!", reply_markup=get_action_keyboard())
            return
        # TODO: Додати меню вибору предметів
        await query.edit_message_text("(Вибір предметів тут)", reply_markup=get_back_keyboard())
    elif data == "back_to_action":
        await query.edit_message_text("Оберіть дію:", reply_markup=get_action_keyboard())

# Вистріл

async def shoot(chat_id, user_id, context):
    game = GAMES[chat_id]
    barrel = game['barrel']
    bullet = barrel[game['current_bullet']]
    player = game['players'][user_id]

    if bullet == "live":
        damage = 2 if game['powder_boost'] == user_id else 1
        player['hp'] -= damage
        text = f"💥 {player['name']} отримує {damage} шкоди! (HP: {player['hp']})"
        if player['hp'] <= 0:
            text += " ☠️ ВИ ВБИТІ!"
            del game['players'][user_id]
            game['queue'].remove(user_id)
    else:
        text = f"💨 {player['name']} вижив!"

    game['current_bullet'] += 1
    game['powder_boost'] = None

    await context.bot.send_message(chat_id, text)

    if game['current_bullet'] >= len(barrel):
        await context.bot.send_message(chat_id, "🔁 Новий барабан і роздача предметів!")
        game['barrel'] = generate_barrel()
        game['current_bullet'] = 0
        distribute_items(game)

    if len(game['players']) <= 1:
        winner = list(game['players'].values())[0]['name'] if game['players'] else "Ніхто"
        await context.bot.send_message(chat_id, f"Гру завершено. Переможець: {winner}")
        del GAMES[chat_id]
        return

    game['current'] += 1
    await next_turn(chat_id, context)

# Роздача предметів

def distribute_items(game):
    for player in game['players'].values():
        new_item = random.choice(ITEMS)
        player['items'].append(new_item)

# Головна функція запуску

def main():
    app = ApplicationBuilder().token("8146584127:AAGfTzyqYbClLe09pJ0Xgdnu3JRj8HrnfQM").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("begin", begin))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.run_polling()

if __name__ == '__main__':
    main()
