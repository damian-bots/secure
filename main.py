import random
import motor.motor_asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# MongoDB Setup
client = motor.motor_asyncio.AsyncIOMotorClient("mongodb+srv://botmaker9675208:botmaker9675208@cluster0.sc9mq8b.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["cricket_bot"]

# Cricket shots and runs mapping
shots = ["Straight Drive", "Cover Drive", "Pull Shot", "Cut Shot", "Helicopter Shot", "Defensive Shot"]
runs_mapping = {"Straight Drive": 2, "Cover Drive": 4, "Pull Shot": 6, "Cut Shot": 4, "Helicopter Shot": 6, "Defensive Shot": 1}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display main menu."""
    keyboard = [
        [InlineKeyboardButton("🏏 Start Match", callback_data="start_match")],
        [InlineKeyboardButton("👥 Create Team", callback_data="create_team"), InlineKeyboardButton("➕ Join Team", callback_data="join_team")],
        [InlineKeyboardButton("📊 Scoreboard", callback_data="scoreboard")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🏏 Welcome to Cricket Game Bot!\nChoose an option below:", reply_markup=reply_markup)

async def create_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a new team."""
    user_id = update.effective_user.id
    if len(context.args) == 0:
        await update.message.reply_text("❌ Provide a team name. Example: /create_team Warriors")
        return

    team_name = " ".join(context.args)
    existing_team = await db.teams.find_one({"name": team_name})
    
    if existing_team:
        await update.message.reply_text("⚠️ Team name already exists! Choose another name.")
        return

    await db.teams.insert_one({"name": team_name, "players": [user_id], "score": 0})
    await db.users.update_one({"user_id": user_id}, {"$set": {"team": team_name}}, upsert=True)
    await update.message.reply_text(f"✅ Team '{team_name}' created! Others can join using /join_team {team_name}.")

async def join_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Join an existing team."""
    user_id = update.effective_user.id
    if len(context.args) == 0:
        await update.message.reply_text("❌ Provide a team name. Example: /join_team Warriors")
        return

    team_name = " ".join(context.args)
    team = await db.teams.find_one({"name": team_name})

    if not team:
        await update.message.reply_text("⚠️ Team does not exist!")
        return

    await db.teams.update_one({"name": team_name}, {"$addToSet": {"players": user_id}})
    await db.users.update_one({"user_id": user_id}, {"$set": {"team": team_name}}, upsert=True)
    await update.message.reply_text(f"✅ You joined team '{team_name}'! Get ready to play!")

async def start_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a match between two teams."""
    if len(context.args) < 2:
        await update.message.reply_text("❌ Mention two teams. Example: /start_match TeamA TeamB")
        return

    team1, team2 = context.args[0], context.args[1]
    existing_teams = await db.teams.find({"name": {"$in": [team1, team2]}}).to_list(length=2)

    if len(existing_teams) < 2:
        await update.message.reply_text("⚠️ One or both teams do not exist!")
        return

    await db.matches.insert_one({"team1": team1, "team2": team2, "batting": team1, "bowling": team2})
    await update.message.reply_text(f"🏏 Match Started: {team1} vs {team2}\n\n{team1} will bat first!")
    await next_batsman(team1, context)

async def next_batsman(team_name, context):
    """Send batting choice to the next player."""
    team = await db.teams.find_one({"name": team_name})
    if not team or not team.get("players"):
        return

    batsman = team["players"][0]  # Rotate players in order
    keyboard = [[InlineKeyboardButton(shot, callback_data=f"shot_{shot}")] for shot in shots]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(batsman, "🏏 Your turn to bat! Choose a shot:", reply_markup=reply_markup)

async def next_bowler(team_name, context):
    """Send bowling choice to the next player."""
    match = await db.matches.find_one({"batting": team_name})
    if not match:
        return

    bowler_team = match["bowling"]
    team = await db.teams.find_one({"name": bowler_team})
    if not team or not team.get("players"):
        return

    bowler = team["players"][0]  # Rotate players
    keyboard = [[InlineKeyboardButton(shot, callback_data=f"bowl_{shot}")] for shot in shots]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(bowler, "🎯 Your turn to bowl! Choose a delivery:", reply_markup=reply_markup)

async def handle_shot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle batting shots."""
    query = update.callback_query
    user_id = query.from_user.id
    user_choice = query.data.replace("shot_", "")

    user_data = await db.users.find_one({"user_id": user_id})
    if not user_data or "team" not in user_data:
        await query.answer("You're not in a team!")
        return

    team_name = user_data["team"]
    match = await db.matches.find_one({"batting": team_name})
    if not match:
        await query.answer("You're not batting!")
        return

    bowler_data = await db.bowling.find_one({"team": match["bowling"]})
    if not bowler_data:
        await query.answer("Waiting for bowler!")
        return

    bowler_choice = bowler_data["delivery"]
    if user_choice == bowler_choice:
        message = f"❌ OUT! You played {user_choice}, but the bowler delivered {bowler_choice}."
    else:
        runs = runs_mapping[user_choice]
        await db.teams.update_one({"name": team_name}, {"$inc": {"score": runs}})
        message = f"✅ {user_choice} for {runs} runs!"

    await query.answer()
    await context.bot.send_message(update.effective_chat.id, message)
    await next_bowler(team_name, context)

async def handle_bowl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bowling choices."""
    query = update.callback_query
    user_id = query.from_user.id
    delivery = query.data.replace("bowl_", "")

    user_data = await db.users.find_one({"user_id": user_id})
    if not user_data or "team" not in user_data:
        await query.answer("You're not in a team!")
        return

    await db.bowling.update_one({"team": user_data["team"]}, {"$set": {"delivery": delivery}}, upsert=True)
    await query.answer()
    await query.message.reply_text(f"🎯 You bowled a {delivery}! Waiting for the batsman.")

# Bot setup
app = Application.builder().token("7470264967:AAHVC0iv2UwplOTEDj6-vO0Qfa1OagRNjWE").build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("create_team", create_team))
app.add_handler(CommandHandler("join_team", join_team))
app.add_handler(CommandHandler("start_match", start_match))
app.add_handler(CallbackQueryHandler(handle_shot, pattern="^shot_"))
app.add_handler(CallbackQueryHandler(handle_bowl, pattern="^bowl_"))
app.run_polling()
