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
        [InlineKeyboardButton("Add to Your Chat for Start Match", url=f"https://t.me/SlaveXGameBot?startGroup=true"")],
        [InlineKeyboardButton("Support 💬", url=f"https://t.me/DeadlineTech"), InlineKeyboardButton("Updates 📢", url=f"https://t.me/DeadlineTechsupport")]
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

    match_id = f"{team1}_vs_{team2}"
    group_id = update.effective_chat.id  

    await db.matches.insert_one({
        "match_id": match_id, 
        "team1": team1, "team2": team2, 
        "batting": team1, "bowling": team2, 
        "inning": 1, "wickets": 0, "overs": 0, "balls": 0, 
        "group_id": group_id, 
        "current_batsman_index": 0, "current_bowler_index": 0
    })

    await update.message.reply_text(f"🏏 Match Started: {team1} vs {team2}\n\n{team1} will bat first!")
    await next_batsman(match_id, context)

async def next_batsman(match_id, context):
    """Send batting choice to the next player."""
    match = await db.matches.find_one({"match_id": match_id})
    if not match:
        return

    team_name = match["batting"]
    team = await db.teams.find_one({"name": team_name})

    if match["wickets"] >= 5 or match["overs"] >= 5:
        await switch_innings(match_id, context)
        return

    batsman_index = match["current_batsman_index"] % len(team["players"])
    batsman = team["players"][batsman_index]

    keyboard = [[InlineKeyboardButton(shot, callback_data=f"shot_{match_id}_{shot}")] for shot in shots]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(batsman, f"🏏 Your turn to bat for {team_name}! Choose a shot:", reply_markup=reply_markup)

async def handle_shot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle batting shots."""
    query = update.callback_query
    data_parts = query.data.split("_", 2)
    match_id, user_choice = data_parts[1], data_parts[2]

    match = await db.matches.find_one({"match_id": match_id})
    if not match:
        await query.answer("⚠️ Match not found!")
        return

    group_id = match["group_id"]
    balls = match["balls"] + 1
    overs = match["overs"]

    if balls >= 6:
        balls = 0
        overs += 1

    if overs >= 5 or match["wickets"] >= 5:
        await switch_innings(match_id, context)
        return

    runs = runs_mapping[user_choice]
    await db.teams.update_one({"name": match["batting"]}, {"$inc": {"score": runs}})
    await db.matches.update_one({"match_id": match_id}, {"$set": {"balls": balls, "overs": overs}})

    message = f"🏏 {user_choice} for {runs} runs!\n\nOvers: {overs}.{balls} | Wickets: {match['wickets']}/5"
    await context.bot.send_message(group_id, message)

    await next_batsman(match_id, context)

async def top_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display top 10 players by points."""
    top_users = await db.users.find().sort("points", -1).limit(10).to_list(length=10)
    if not top_users:
        await update.message.reply_text("No top players yet!")
        return

    leaderboard = "🏆 **Top 10 Players** 🏆\n\n"
    for idx, user in enumerate(top_users, start=1):
        leaderboard += f"{idx}. Player {user['user_id']} - {user.get('points', 0)} points\n"

    await update.message.reply_text(leaderboard)

# Bot setup
app = Application.builder().token("7470264967:AAHVC0iv2UwplOTEDj6-vO0Qfa1OagRNjWE").build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("create_team", create_team))
app.add_handler(CommandHandler("join_team", join_team))
app.add_handler(CommandHandler("start_match", start_match))
app.add_handler(CommandHandler("top", top_players))
app.add_handler(CallbackQueryHandler(handle_shot, pattern="^shot_"))

app.run_polling()
