import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Data storage
user_scores = {}  # {user_id: score}
team_scores = {}  # {team_name: score}
user_teams = {}  # {user_id: team_name}
team_players = {}  # {team_name: [user_ids]}
bowling_choices = {}  # {user_id: selected_delivery}

# Cricket shots and deliveries
shots = ["Straight Drive", "Cover Drive", "Pull Shot", "Cut Shot", "Helicopter Shot", "Defensive Shot"]
runs_mapping = {"Straight Drive": 2, "Cover Drive": 4, "Pull Shot": 6, "Cut Shot": 4, "Helicopter Shot": 6, "Defensive Shot": 1}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - Display main menu with buttons."""
    keyboard = [
        [InlineKeyboardButton("🏏 Bat", callback_data="bat"), InlineKeyboardButton("🎯 Bowl", callback_data="bowl")],
        [InlineKeyboardButton("👥 Create Team", callback_data="create_team"), InlineKeyboardButton("➕ Join Team", callback_data="join_team")],
        [InlineKeyboardButton("ℹ Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = "🏏 Welcome to Cricket Game Bot!\nChoose an option below:"
    await update.message.reply_text(message, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command - Display game instructions."""
    keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="start")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = (
        "🏏 **Cricket Game Instructions** 🏏\n\n"
        "🔹 **Batting**: Choose a shot. If it matches the bowler's delivery, you're OUT!\n"
        "🔹 **Bowling**: Choose a delivery. If it matches the batsman's shot, they are OUT!\n"
        "🔹 **Teams**: Create or join a team to play together.\n\n"
        "✅ Commands:\n"
        "➖ /bat - Start batting\n"
        "➖ /bowl - Start bowling\n"
        "➖ /create_team <team_name> - Create a new team\n"
        "➖ /join_team <team_name> - Join an existing team\n"
        "➖ /leave_team - Leave your current team\n"
    )
    await update.message.reply_text(message, reply_markup=reply_markup)

async def bat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bat command - Show shot selection buttons."""
    keyboard = [[InlineKeyboardButton(shot, callback_data=f"shot_{shot}")] for shot in shots]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🏏 Choose your shot:", reply_markup=reply_markup)

async def bowl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bowl command - Show delivery selection buttons."""
    keyboard = [[InlineKeyboardButton(shot, callback_data=f"bowl_{shot}")] for shot in shots]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🎯 Choose your delivery:", reply_markup=reply_markup)

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
        await update.message.reply_text("❌ You are already in a team! Leave your current team first using /leave_team.")
        return

    team_players[team_name].append(user_id)
    user_teams[user_id] = team_name
    await update.message.reply_text(f"✅ You joined team '{team_name}'! Get ready to bat or bowl!")

async def handle_shot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle batting shots."""
    query = update.callback_query
    user_id = query.from_user.id
    user_choice = query.data.replace("shot_", "")

    bot_delivery = random.choice(shots)  # Bot chooses a delivery

    if user_choice == bot_delivery:
        message = f"❌ OUT! You played {user_choice}, but the ball was also {bot_delivery}.\n🏏 Your final score: {user_scores.get(user_id, 0)}"
        user_scores[user_id] = 0
    else:
        runs = runs_mapping[user_choice]
        user_scores[user_id] = user_scores.get(user_id, 0) + runs
        message = f"🎯 You played: {user_choice}\n🏏 Ball was: {bot_delivery}\n✅ You scored {runs} runs!\n🏆 Total Score: {user_scores[user_id]}"

    await query.answer()
    await query.message.reply_text(message)

async def handle_bowl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bowling choices."""
    query = update.callback_query
    user_id = query.from_user.id
    bowling_choices[user_id] = query.data.replace("bowl_", "")

    await query.answer()
    await query.message.reply_text(f"🎯 You bowled a {bowling_choices[user_id]}!\nNow wait for the batsman’s shot.")

def main():
    """Main function to run the bot."""
    TOKEN = "7470264967:AAHVC0iv2UwplOTEDj6-vO0Qfa1OagRNjWE"
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("bat", bat))
    app.add_handler(CommandHandler("bowl", bowl))
    app.add_handler(CommandHandler("create_team", create_team))
    app.add_handler(CommandHandler("join_team", join_team))

    app.add_handler(CallbackQueryHandler(handle_shot, pattern="^shot_"))
    app.add_handler(CallbackQueryHandler(handle_bowl, pattern="^bowl_"))
    app.add_handler(CallbackQueryHandler(start, pattern="^start$"))
    app.add_handler(CallbackQueryHandler(help_command, pattern="^help$"))

    print("🏏 Cricket Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
