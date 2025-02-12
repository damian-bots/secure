import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Data storage
team_scores = {}  # {team_name: score}
user_teams = {}  # {user_id: team_name}
team_players = {}  # {team_name: [user_ids]}
matches = {}  # {team1: team2}
batting_team = {}  # {match_id: team_name}
bowling_choices = {}  # {user_id: selected_delivery}

# Cricket shots and deliveries
shots = ["Straight Drive", "Cover Drive", "Pull Shot", "Cut Shot", "Helicopter Shot", "Defensive Shot"]
runs_mapping = {"Straight Drive": 2, "Cover Drive": 4, "Pull Shot": 6, "Cut Shot": 4, "Helicopter Shot": 6, "Defensive Shot": 1}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - Display main menu with buttons."""
    keyboard = [
        [InlineKeyboardButton("🏏 Start Match", callback_data="start_match")],
        [InlineKeyboardButton("👥 Create Team", callback_data="create_team"), InlineKeyboardButton("➕ Join Team", callback_data="join_team")],
        [InlineKeyboardButton("📊 Scoreboard", callback_data="scoreboard")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = "🏏 Welcome to Cricket Game Bot!\nChoose an option below:"
    await update.message.reply_text(message, reply_markup=reply_markup)

async def create_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a new team."""
    user_id = update.effective_user.id
    if len(context.args) == 0:
        await update.message.reply_text("❌ Please provide a team name. Example: /create_team Warriors")
        return

    team_name = " ".join(context.args)
    if team_name in team_scores:
        await update.message.reply_text("⚠️ Team name already exists! Choose another name.")
        return

    team_scores[team_name] = 0
    team_players[team_name] = [user_id]
    user_teams[user_id] = team_name
    await update.message.reply_text(f"✅ Team '{team_name}' created! Others can join using /join_team {team_name}.")

async def join_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Join an existing team."""
    user_id = update.effective_user.id
    if len(context.args) == 0:
        await update.message.reply_text("❌ Please provide a team name. Example: /join_team Warriors")
        return

    team_name = " ".join(context.args)
    if team_name not in team_scores:
        await update.message.reply_text("⚠️ Team does not exist! Create one with /create_team <team_name>.")
        return

    if user_id in user_teams:
        await update.message.reply_text("❌ You are already in a team! Leave your current team first.")
        return

    team_players[team_name].append(user_id)
    user_teams[user_id] = team_name
    await update.message.reply_text(f"✅ You joined team '{team_name}'! Get ready to play!")

async def start_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a match between two teams."""
    if len(context.args) < 2:
        await update.message.reply_text("❌ Please mention two teams to start a match. Example: /start_match TeamA TeamB")
        return

    team1, team2 = context.args[0], context.args[1]
    if team1 not in team_scores or team2 not in team_scores:
        await update.message.reply_text("⚠️ One or both teams do not exist!")
        return

    matches[team1] = team2
    batting_team[team1] = team1  # Team1 bats first
    await update.message.reply_text(f"🏏 Match Started: {team1} vs {team2}\n\n{team1} will bat first!")

    await next_batsman(team1, context)

async def next_batsman(team_name, context):
    """Send private message to the next batsman."""
    players = team_players[team_name]
    if not players:
        return

    batsman = players[0]  # Rotate players (can be improved)
    keyboard = [[InlineKeyboardButton(shot, callback_data=f"shot_{shot}")] for shot in shots]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(batsman, "🏏 Your turn to bat! Choose a shot:", reply_markup=reply_markup)

async def next_bowler(team_name, context):
    """Send private message to the next bowler."""
    opponent_team = matches.get(team_name)
    if not opponent_team:
        return

    players = team_players[opponent_team]
    if not players:
        return

    bowler = players[0]  # Rotate players
    keyboard = [[InlineKeyboardButton(shot, callback_data=f"bowl_{shot}")] for shot in shots]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(bowler, "🎯 Your turn to bowl! Choose a delivery:", reply_markup=reply_markup)

async def handle_shot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle batting shots."""
    query = update.callback_query
    user_id = query.from_user.id
    user_choice = query.data.replace("shot_", "")

    team_name = user_teams.get(user_id)
    opponent_team = matches.get(team_name)

    if not team_name or not opponent_team:
        await query.answer("You're not in an active match!")
        return

    bot_delivery = random.choice(shots)  # Simulated bowler

    if user_choice == bot_delivery:
        message = f"❌ OUT! You played {user_choice}, but the ball was also {bot_delivery}.\n🏏 Team {team_name} score: {team_scores[team_name]}"
    else:
        runs = runs_mapping[user_choice]
        team_scores[team_name] += runs
        message = f"🎯 You played: {user_choice}\n🏏 Ball was: {bot_delivery}\n✅ Team {team_name} scored {runs} runs!"

    await query.answer()
    await query.message.reply_text(message)
    await next_bowler(team_name, context)

async def handle_bowl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bowling choices."""
    query = update.callback_query
    user_id = query.from_user.id
    bowling_choices[user_id] = query.data.replace("bowl_", "")

    team_name = user_teams.get(user_id)
    if not team_name:
        await query.answer("You're not in an active match!")
        return

    await query.answer()
    await query.message.reply_text(f"🎯 You bowled a {bowling_choices[user_id]}!\nNow wait for the batsman’s shot.")

async def scoreboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display current scores of all teams."""
    if not team_scores:
        await update.message.reply_text("🏏 No matches played yet.")
        return

    scores = "\n".join([f"{team}: {score} runs" for team, score in team_scores.items()])
    await update.message.reply_text(f"📊 **Scoreboard:**\n{scores}")

def main():
    """Main function to run the bot."""
    TOKEN = "7470264967:AAHVC0iv2UwplOTEDj6-vO0Qfa1OagRNjWE"
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("create_team", create_team))
    app.add_handler(CommandHandler("join_team", join_team))
    app.add_handler(CommandHandler("start_match", start_match))
    app.add_handler(CommandHandler("scoreboard", scoreboard))

    app.add_handler(CallbackQueryHandler(handle_shot, pattern="^shot_"))
    app.add_handler(CallbackQueryHandler(handle_bowl, pattern="^bowl_"))

    print("🏏 Cricket Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
