from telegram import Update, ChatMember, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, JobQueue
from pymongo import MongoClient

# MongoDB Setup
MONGO_URI = "mongodb+srv://botmaker9675208:botmaker9675208@cluster0.sc9mq8b.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"  # Change if needed
client = MongoClient(MONGO_URI)
db = client["telegram_bot"]
auth_collection = db["authorized_users"]
sudo_collection = db["sudo_users"]

# Define the bot owner ID (Replace with your Telegram user ID)
BOT_OWNER_ID = 6848223695  # Change this to your Telegram ID

# Function to check if a user is an admin with "Add Admins" permission
async def is_super_admin(update: Update, user_id: int) -> bool:
    """Check if the user is an admin with 'can_promote_members' permission"""
    chat = update.effective_chat
    member = await chat.get_member(user_id)

    if member.status == ChatMember.OWNER:
        return True
    elif member.status == ChatMember.ADMINISTRATOR:
        return member.can_promote_members if member.can_promote_members is not None else False
    return False

# Check if a user is in sudo list
def is_sudo(user_id: int) -> bool:
    return sudo_collection.find_one({"user_id": user_id}) is not None

# Add user to sudo list
def add_sudo(user_id: int):
    if not is_sudo(user_id):
        sudo_collection.insert_one({"user_id": user_id})

# Remove user from sudo list
def remove_sudo(user_id: int):
    sudo_collection.delete_one({"user_id": user_id})

# Check if a user is authorized (exempt from deletion)
def is_authorized(chat_id: int, user_id: int) -> bool:
    return auth_collection.find_one({"chat_id": chat_id, "user_id": user_id}) is not None

# Add user to authorized list
def authorize_user(chat_id: int, user_id: int):
    if not is_authorized(chat_id, user_id):
        auth_collection.insert_one({"chat_id": chat_id, "user_id": user_id})

# Remove user from authorized list
def unauthorize_user(chat_id: int, user_id: int):
    auth_collection.delete_one({"chat_id": chat_id, "user_id": user_id})

# Command: Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send introduction and command list with inline buttons"""
    keyboard = [
        [InlineKeyboardButton("Add to your Chat ➕", url="https://t.me/DeadlineTechGuardianBot?startgroup=true")],
        [
            InlineKeyboardButton("Support Chat 💬", url="https://t.me/deadlineTechSupport"),
            InlineKeyboardButton("Update Channel 📢", url="https://t.me/DeadlineTech")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    intro_text = (
        "👋 Welcome to the Bot!\n\n"
        "This bot deletes edited messages and supports admin authentication.\n\n"
        "🔹 **Commands:**\n"
        "/start - Show this message\n"
        "/auth - Exempt a user from deletion (Super Admins Only)\n"
        "/unauth - Remove exemption (Super Admins Only)\n"
    )
    
    await update.message.reply_text(intro_text, reply_markup=reply_markup)

# Command: Sudolist (Check sudo users)
async def sudolist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List sudo users (Only sudo users can access)"""
    message = update.message
    user_id = message.from_user.id

    if not is_sudo(user_id):
        await message.reply_text("❌ Only sudo users can check the sudo list.")
        return

    sudo_users = sudo_collection.find()
    sudo_list = [f"- `{user['user_id']}`" for user in sudo_users]

    if not sudo_list:
        await message.reply_text("❌ No sudo users found.")
    else:
        await message.reply_text(f"✅ **Sudo Users List:**\n\n" + "\n".join(sudo_list), parse_mode="Markdown")

# Command: Authlist (Check authorized users)
async def authlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List authorized users in the group (Only for admins)"""
    message = update.message
    user_id = message.from_user.id
    chat_id = message.chat_id

    if not await is_super_admin(update, user_id):
        await message.reply_text("❌ Only group admins can check the auth list.")
        return

    authorized_users = auth_collection.find({"chat_id": chat_id})
    auth_list = [f"- `{user['user_id']}`" for user in authorized_users]

    if not auth_list:
        await message.reply_text("❌ No authorized users found in this group.")
    else:
        await message.reply_text(f"✅ **Authorized Users in this Group:**\n\n" + "\n".join(auth_list), parse_mode="Markdown")
                                
# Command: Auth (Exempt user from deletion)
async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Authorize a user (Only super admins can do this)"""
    message = update.message
    user_id = message.from_user.id

    if not await is_super_admin(update, user_id):
        await message.reply_text("❌ You must be a super admin (can add admins) to use this command.")
        return

    if not message.reply_to_message:
        await message.reply_text("❌ Reply to a user’s message to authorize them.")
        return

    target_user_id = message.reply_to_message.from_user.id
    chat_id = message.chat_id

    authorize_user(chat_id, target_user_id)
    await message.reply_text(f"✅ {message.reply_to_message.from_user.mention_html()} is now authorized.", parse_mode="HTML")

# Command: Unauth (Remove exemption)
async def unauth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove authorization (Only super admins can do this)"""
    message = update.message
    user_id = message.from_user.id

    if not await is_super_admin(update, user_id):
        await message.reply_text("❌ You must be a super admin (can add admins) to use this command.")
        return

    if not message.reply_to_message:
        await message.reply_text("❌ Reply to a user’s message to unauthorize them.")
        return

    target_user_id = message.reply_to_message.from_user.id
    chat_id = message.chat_id

    unauthorize_user(chat_id, target_user_id)
    await message.reply_text(f"🔒 {message.reply_to_message.from_user.mention_html()} is no longer authorized.", parse_mode="HTML")

# Command: Add Sudo
async def add_sudo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a user to the sudo list (Owner Only)"""
    message = update.message
    if message.from_user.id != BOT_OWNER_ID:
        await message.reply_text("❌ Only the bot owner can use this command.")
        return

    if not message.reply_to_message:
        await message.reply_text("❌ Reply to a user's message to add them to sudo list.")
        return

    user_id = message.reply_to_message.from_user.id

    add_sudo(user_id)
    await message.reply_text(f"✅ {message.reply_to_message.from_user.mention_html()} is now a sudo user.", parse_mode="HTML")

# Command: Remove Sudo
async def del_sudo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a user from the sudo list (Owner Only)"""
    message = update.message
    if message.from_user.id != BOT_OWNER_ID:
        await message.reply_text("❌ Only the bot owner can use this command.")
        return

    if not message.reply_to_message:
        await message.reply_text("❌ Reply to a user's message to remove them from sudo list.")
        return

    user_id = message.reply_to_message.from_user.id

    remove_sudo(user_id)
    await message.reply_text(f"🔒 {message.reply_to_message.from_user.mention_html()} is no longer a sudo user.", parse_mode="HTML")

# Function to delete an edited message (executed after delay)
async def delayed_delete(context: ContextTypes.DEFAULT_TYPE):
    """Delete the message after a 5-minute delay"""
    job = context.job
    try:
        await context.bot.delete_message(chat_id=job.chat_id, message_id=job.data)
    except Exception as e:
        print(f"Failed to delete message {job.data}: {e}")

# Handler: Delete Edited Messages (with delay)
async def delete_edited_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Schedule deletion of edited messages after 5 minutes"""
    edited_message = update.edited_message
    chat_id = edited_message.chat_id
    user_id = edited_message.from_user.id

# If user is in sudo list or authorized list, do not delete the message
    if is_sudo(user_id) or is_authorized(chat_id, user_id):
        return

    keyboard = [
        [
            InlineKeyboardButton("Support 💬", url="https://t.me/DeadlineTechSupport"),
            InlineKeyboardButton("Updates 📢", url="https://t.me/DeadlineTech")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Inform the user about the scheduled deletion
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"⚠️ {edited_message.from_user.mention_html()}, your edited message will be deleted in **5 minutes**!",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

    # Schedule message deletion after 5 minutes (300 seconds)
    context.job_queue.run_once(delayed_delete, 300, chat_id=chat_id, data=edited_message.message_id)

# Main function
def main():
    """Run the bot"""
    TOKEN = "7470264967:AAHTssrBhJ2IyNOpzdCGMTlaANqf8B2Je-k"

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("auth", auth))
    app.add_handler(CommandHandler("unauth", unauth))
    app.add_handler(CommandHandler("dev", add_sudo_command))
    app.add_handler(CommandHandler("deldev", del_sudo_command))
    app.add_handler(CommandHandler("authlist", authlist))
    app.add_handler(CommandHandler("devlist", sudolist))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, delete_edited_messages))


    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
