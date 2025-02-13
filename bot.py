import random
import asyncio
import motor.motor_asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# MongoDB Setup
client = motor.motor_asyncio.AsyncIOMotorClient("mongodb+srv://botmaker9675208:botmaker9675208@cluster0.sc9mq8b.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["harry_potter_bot"]

special_roles = ["Voldemort", "Harry Potter", "Malfoy", "Hermione"]
game_data = {}

BOT_USERNAME = "slaveXgameBot"  # Replace with your bot's username

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the registration process with an inline button that redirects to the bot's private chat."""
    chat_id = update.message.chat_id

    if chat_id not in game_data:
        game_data[chat_id] = {"players": [], "registering": True}
        await update.message.reply_text("📢 Registration has started! Click the button below to join.")

    # URL Button to redirect users to the bot's private chat
    register_url = f"https://t.me/{BOT_USERNAME}?start=register_{chat_id}"
    button = InlineKeyboardButton("📝 Register", url=register_url)
    reply_markup = InlineKeyboardMarkup([[button]])

    await update.message.reply_text("Click below to register:", reply_markup=reply_markup)

    # Start auto-begin timer
    await asyncio.sleep(120)
    if len(game_data[chat_id]["players"]) >= 4 and game_data[chat_id]["registering"]:
        await start_game(chat_id, context)
    else:
        await context.bot.send_message(chat_id, "❌ Not enough players. Registration is now closed.")
        del game_data[chat_id]

async def register_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user registration when they start the bot in private chat."""
    user_id = update.message.from_user.id
    args = context.args

    if not args or not args[0].startswith("register_"):
        await update.message.reply_text("❌ Invalid registration request.")
        return

    chat_id = int(args[0].split("_")[1])

    if chat_id not in game_data or not game_data[chat_id]["registering"]:
        await update.message.reply_text("❌ Registration is closed!")
        return

    if user_id in game_data[chat_id]["players"]:
        await update.message.reply_text("✅ You are already registered!")
    else:
        game_data[chat_id]["players"].append(user_id)
        await update.message.reply_text("📜 You have successfully registered for the game! Wait for it to begin.")

async def begin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually start the game."""
    chat_id = update.message.chat_id

    if chat_id not in game_data or not game_data[chat_id]["registering"]:
        await update.message.reply_text("❌ No active registration. Start with /register first.")
        return

    if len(game_data[chat_id]["players"]) < 4:
        await update.message.reply_text("❌ At least 4 players are needed to start the game.")
        return

    await start_game(chat_id, context)

async def start_game(chat_id, context):
    """Start the game and assign roles."""
    game_data[chat_id]["registering"] = False
    players = game_data[chat_id]["players"]
    random.shuffle(players)

    assigned_roles = {}
    chosen_players = random.sample(players, min(len(players), len(special_roles)))

    for i, player in enumerate(chosen_players):
        assigned_roles[player] = special_roles[i]

    for player in players:
        if player not in assigned_roles:
            assigned_roles[player] = "Muggles"

    game_data[chat_id].update({
        "players": assigned_roles,
        "night": True,
        "alive": players,
        "used_heal": {},
        "dead": []
    })

    for player_id, role in assigned_roles.items():
        await context.bot.send_message(player_id, f"🧙 Your role is **{role}**. Use your abilities wisely!")

    await context.bot.send_message(chat_id, "✨ The game has begun! Night phase starts now.")
    await night_phase(chat_id, context)

async def night_phase(chat_id, context):
    """Handle the night phase actions."""
    game = game_data.get(chat_id)
    if not game:
        return

    for player_id, role in game["players"].items():
        if player_id not in game["alive"]:
            continue

        if role == "Voldemort":
            await send_action_buttons(player_id, chat_id, "kill")
        elif role == "Harry Potter":
            await send_action_buttons(player_id, chat_id, "check_or_kill")
        elif role == "Malfoy" and player_id not in game["used_heal"]:
            await send_action_buttons(player_id, chat_id, "heal_self")
        elif role == "Hermione":
            await send_action_buttons(player_id, chat_id, "heal_anyone")

async def send_action_buttons(player_id, chat_id, action):
    """Send action buttons to a player."""
    game = game_data[chat_id]
    alive_players = [p for p in game["alive"] if p != player_id]

    if not alive_players:
        return

    buttons = [
        [InlineKeyboardButton(f"{action.capitalize()} {p}", callback_data=f"{action}_{chat_id}_{p}")] for p in alive_players
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(player_id, f"Choose an action:", reply_markup=reply_markup)

async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process night phase actions."""
    query = update.callback_query
    data = query.data.split("_")
    action, chat_id, target_id = data[0], int(data[1]), int(data[2])

    game = game_data.get(chat_id)
    if not game:
        return

    if action == "kill":
        if target_id in game["alive"]:
            game["alive"].remove(target_id)
            game["dead"].append(target_id)

            player_role = game["players"].get(target_id, "Unknown")
            await context.bot.send_message(chat_id, f"💀 A player was killed last night... They were **{player_role}**.")

            try:
                await context.bot.restrict_chat_member(chat_id, target_id, ChatPermissions(can_send_messages=False))
            except Exception as e:
                print(f"Failed to restrict player {target_id}: {e}")

    elif action == "check_or_kill":
        role = game["players"].get(target_id, "Unknown")
        await query.message.reply_text(f"🔍 The checked player is {role}.")
    elif action == "heal_self":
        game["used_heal"][query.from_user.id] = True
        await query.message.reply_text("💖 You have healed yourself!")
    elif action == "heal_anyone":
        if target_id not in game["alive"]:
            game["alive"].append(target_id)
        await query.message.reply_text("💖 You healed a player!")

    await query.answer()
    await check_night_over(chat_id, context)

async def check_night_over(chat_id, context):
    """Check if all night actions are completed."""
    game = game_data.get(chat_id)
    if not game:
        return

    if len(game["alive"]) <= 1:
        winner = list(game["players"].values())[0]
        await context.bot.send_message(chat_id, f"🎉 The game is over! {winner} wins!")

        for dead_player in game["dead"]:
            try:
                await context.bot.restrict_chat_member(chat_id, dead_player, ChatPermissions(can_send_messages=True))
            except Exception as e:
                print(f"Failed to restore permissions for {dead_player}: {e}")

        del game_data[chat_id]
    else:
        await context.bot.send_message(chat_id, "☀️ Day phase begins! Discuss and vote on the culprit.")

# Bot setup
app = Application.builder().token("7470264967:AAHVC0iv2UwplOTEDj6-vO0Qfa1OagRNjWE").build()
app.add_handler(CommandHandler("register", register))
app.add_handler(CommandHandler("start", register_callback))
app.add_handler(CommandHandler("begin", begin))
app.add_handler(CallbackQueryHandler(handle_action))

app.run_polling()
