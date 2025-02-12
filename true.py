from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import random
import pymongo

TOKEN = "7470264967:AAHTssrBhJ2IyNOpzdCGMTlaANqf8B2Je-k"
MONGO_URI = "mongodb+srv://botmaker9675208:botmaker9675208@cluster0.sc9mq8b.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

client = pymongo.MongoClient(MONGO_URI)
db = client["hp_game"]
players_collection = db["players"]
game_collection = db["game"]

# Initialize bot
app = Application.builder().token(TOKEN).build()

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    members = await context.bot.get_chat_administrators(chat_id)
    
    player_ids = [m.user.id for m in members if not m.user.is_bot]
    random.shuffle(player_ids)
    
    num_players = len(player_ids)
    num_voldemorts = min(3, max(1, num_players // 5))
    num_muggles = int(num_players * 0.7)
    
    roles = ["Lord Voldemort"] * num_voldemorts + ["Harry Potter", "Madam Pomfrey"]
    
    if num_players > 8:
        roles.append("Malfoy")

    roles += ["Muggle"] * (num_players - len(roles))
    random.shuffle(roles)

    game_collection.update_one({"chat_id": chat_id}, {"$set": {"status": "running"}}, upsert=True)

    for player_id, role in zip(player_ids, roles):
        players_collection.update_one({"player_id": player_id}, {"$set": {"role": role, "alive": True}}, upsert=True)
        await context.bot.send_message(player_id, f"You are **{role}**.")

    await update.message.reply_text("Game has started! Night phase begins.")
    await night_phase(update, context)

async def night_phase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    await context.bot.send_message(chat_id, "🌙 Night phase has begun. Special roles, check your DMs.")

    alive_players = players_collection.find({"alive": True})
    
    for player in alive_players:
        if player["role"] == "Lord Voldemort":
            await context.bot.send_message(player["player_id"], "Select a player to kill.", reply_markup=await get_player_buttons())
        elif player["role"] == "Harry Potter":
            await context.bot.send_message(player["player_id"], "Choose: Kill a player or check a player's role.", reply_markup=await get_harry_buttons())
        elif player["role"] == "Madam Pomfrey":
            await context.bot.send_message(player["player_id"], "Choose a player to heal.", reply_markup=await get_player_buttons())

async def get_player_buttons():
    buttons = []
    for player in players_collection.find({"alive": True}):
        buttons.append([InlineKeyboardButton(player["player_id"], callback_data=f"kill_{player['player_id']}")])
    return InlineKeyboardMarkup(buttons)

async def get_harry_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Kill", callback_data="harry_kill"), InlineKeyboardButton("Check Role", callback_data="harry_check")]
    ])

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    player_id = query.from_user.id
    data = query.data

    if data.startswith("kill_"):
        victim_id = int(data.split("_")[1])
        players_collection.update_one({"player_id": victim_id}, {"$set": {"alive": False}})
        await context.bot.send_message(victim_id, "You were killed.")
    
    elif data == "harry_kill":
        await context.bot.send_message(player_id, "Select a player to kill.", reply_markup=await get_player_buttons())

    elif data == "harry_check":
        await context.bot.send_message(player_id, "Select a player to check.", reply_markup=await get_player_buttons())

    await query.answer()

async def day_phase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    killed_players = players_collection.find({"alive": False})

    msg = "☀️ Day begins. Last night's events:\n"
    for player in killed_players:
        msg += f"{player['player_id']} ({player['role']}) was killed.\n"

    await context.bot.send_message(chat_id, msg)
    await context.bot.send_message(chat_id, "Discuss and vote to lynch someone!", reply_markup=await get_player_buttons())

async def vote_lynch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    victim_id = int(query.data.split("_")[1])
    
    players_collection.update_one({"player_id": victim_id}, {"$set": {"alive": False}})
    victim = players_collection.find_one({"player_id": victim_id})

    await context.bot.send_message(query.message.chat_id, f"{victim_id} ({victim['role']}) was lynched.")
    await check_game_end(update, context)

async def check_game_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    villains = players_collection.count_documents({"role": "Lord Voldemort", "alive": True})
    muggles = players_collection.count_documents({"role": "Muggle", "alive": True})

    if villains == 0:
        await context.bot.send_message(chat_id, "🎉 The Muggles have won!")
        game_collection.update_one({"chat_id": chat_id}, {"$set": {"status": "ended"}})
    elif villains >= muggles:
        await context.bot.send_message(chat_id, "💀 The Villains have dominated!")
        game_collection.update_one({"chat_id": chat_id}, {"$set": {"status": "ended"}})
      
app.add_handler(CommandHandler("startgame", start_game))
app.add_handler(CallbackQueryHandler(button_callback))

app.run_polling()

