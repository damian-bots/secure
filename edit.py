from telegram import Update, ChatMember, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, JobQueue
from pymongo import MongoClient

# MongoDB Setup
MONGO_URI = "mongodb+srv://botmaker9675208:botmaker9675208@cluster0.sc9mq8b.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"  # Change if needed
client = MongoClient(MONGO_URI)
db = client["telegram_bot"]
auth_collection = db["authorized_users"]
sudo_collection = db["sudo_users"]
delay_collection = db["delete_delay"]
free_users_collection = db["free_users"]
gmute_collection = db["gmute_list"]

# Define the bot owner ID (Replace with your Telegram user ID)
DEFAULT_DELETE_TIME = 40
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
        [InlineKeyboardButton("Add to your Chat ➕", url="https://t.me/slaveSecurityBot?startgroup=true")],
        [
            InlineKeyboardButton("Support Chat 💬", url="https://t.me/deadlineTechSupport"),
            InlineKeyboardButton("Update Channel 📢", url="https://t.me/DeadlineTech")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    intro_text = (
        "Welcome to the Security Bot 📢!\n\n"
        "deletes edited messages and supports admin authentication.\n"
        "deletes all media like [photos,videos,documents,gif,stickers]\n\n"
        "**𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀:**\n"
        "/start - Show this message\n"
        "/auth - Exempt a user from deletion of edit messages (Super Admins Only)\n"
        "/unauth - Remove exemption of deletion edit messages (Super Admins Only)\n"
        "/delay - delay the time of deletion of media (Admins Only)\n"
        "/free - exempt a user from deletion of media (Admins Only)\n"
        "/unfree - Remove exemption of deletion of media (Admins Only)\n"
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
    await message.reply_text(f"✅ {message.reply_to_message.from_user.mention_html()} is now a sudo user in edited deletion.", parse_mode="HTML")

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
    reply_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=f"⚠️ {edited_message.from_user.mention_html()}, your edited message will be deleted in **5 minutes**!",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

    # Schedule message deletion after 5 minutes (300 seconds)
    context.job_queue.run_once(delayed_delete, 300, chat_id=chat_id, data=edited_message.message_id)
    context.job_queue.run_once(delayed_delete, 30, chat_id=chat_id, data=reply_msg.message_id)

def get_delete_delay(chat_id: int) -> int:
    data = delay_collection.find_one({"chat_id": chat_id})
    return data["delay"] if data else DEFAULT_DELETE_TIME

def set_delete_delay(chat_id: int, delay: int):
    delay_collection.update_one({"chat_id": chat_id}, {"$set": {"delay": delay}}, upsert=True)

def is_free_user(chat_id: int, user_id: int) -> bool:
    return bool(free_users_collection.find_one({"chat_id": chat_id, "user_id": user_id}))

async def delete_media(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    try:
        await context.bot.delete_message(job.chat_id, job.data)
    except Exception as e:
        print(f"Failed to delete message {job.data}: {e}")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    user_id = message.from_user.id
    username = message.from_user.mention_html()

    if is_sudo(user_id) or is_free_user(chat_id, user_id):
        return

    delay_time = get_delete_delay(chat_id) * 60
    context.job_queue.run_once(delete_media, delay_time, chat_id=chat_id, name=f"media_{message.message_id}", data=message.message_id)
    
    keyboard = [[InlineKeyboardButton("Support 💬", url="https://t.me/deadlineTechSupport"),
                 InlineKeyboardButton("Updates 📢", url="https://t.me/deadlineTech")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    reply_msg = await message.reply_text(f"⚠️ {username}, your media will be deleted in {delay_time // 60} minutes!", reply_markup=reply_markup, parse_mode="HTML")
    
    # Schedule deletion of the bot's reply message after 30 seconds
    context.job_queue.run_once(delete_media, 30, chat_id=chat_id, name=f"reply_{reply_msg.message_id}", data=reply_msg.message_id)

async def set_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allow only admins to set media deletion delay."""
    message = update.message
    user_id = message.from_user.id
    chat_id = message.chat_id

    if not await is_admin(update, user_id):
        await message.reply_text("❌ Only admins can set the delete delay.")
        return

    if len(context.args) != 1 or not context.args[0].isdigit():
        await message.reply_text("❌ Please specify a valid number of minutes. Example: /delay 60")
        return

    delay = int(context.args[0])
    if delay < 10:
        await message.reply_text("❌ Delay time must be at least 10 minutes.")
        return

    set_delete_delay(chat_id, delay)
    await message.reply_text(f"✅ Media deletion delay is now set to {delay} minutes.")

async def free_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allow admins to exempt a user from media deletion."""
    message = update.message
    chat_id = message.chat_id
    requester_id = message.from_user.id
    user_id = message.reply_to_message.from_user.id if message.reply_to_message else None

    # Ensure only admins can use this command
    if not (await is_admin(update, requester_id)):
        await message.reply_text("❌ Only admins can use this command.")
        return

    if not user_id:
        await message.reply_text("❌ Reply to a user's message to free them from media deletion.")
        return

    free_users_collection.update_one(
        {"chat_id": chat_id, "user_id": user_id}, {"$set": {"exempt": True}}, upsert=True
    )
    await message.reply_text("✅ User has been exempted from media deletion.")

async def unfree_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allow admins to remove exemption from media deletion."""
    message = update.message
    chat_id = message.chat_id
    requester_id = message.from_user.id
    user_id = message.reply_to_message.from_user.id if message.reply_to_message else None

    # Ensure only admins can use this command
    if not (await is_admin(update, requester_id)):
        await message.reply_text("❌ Only admins can use this command.")
        return

    if not user_id:
        await message.reply_text("❌ Reply to a user's message to unfree them.")
        return

    free_users_collection.delete_one({"chat_id": chat_id, "user_id": user_id})
    await message.reply_text("✅ User will now have their media deleted again.")

async def is_admin(update: Update, user_id: int) -> bool:
    """Check if a user is an admin."""
    chat = update.effective_chat
    try:
        member = await chat.get_member(user_id)
        return member.status in [ChatMember.OWNER, ChatMember.ADMINISTRATOR]
    except Exception:
        return False  # Assume non-admin if an error occurs

def add_gmuted_user(user_id: int):
    """Add a user to the global mute list."""
    gmute_collection.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)

def remove_gmuted_user(user_id: int):
    """Remove a user from the global mute list."""
    gmute_collection.delete_one({"user_id": user_id})

def is_gmuted(user_id: int) -> bool:
    """Check if a user is globally muted."""
    return gmute_collection.find_one({"user_id": user_id}) is not None

async def gmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Globally mute a user (only sudo users can do this)."""
    message = update.message
    user_id = message.from_user.id
    
    if not is_sudo(user_id):
        await message.reply_text("❌ Only sudo users can use this command.")
        return
    
    if not context.args:
        await message.reply_text("❌ Please specify a user ID or mention a user.")
        return
    
    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await message.reply_text("❌ Invalid user ID. Please provide a valid numeric ID.")
        return
    
    add_gmuted_user(target_user_id)
    await message.reply_text(f"✅ User `{target_user_id}` has been globally muted.", parse_mode="Markdown")

async def ungmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a user from the global mute list (only sudo users)."""
    message = update.message
    user_id = message.from_user.id

    if not is_sudo(user_id):
        await message.reply_text("❌ Only sudo users can use this command.")
        return
    
    if not context.args:
        await message.reply_text("❌ Please specify a user ID to unmute.")
        return
    
    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await message.reply_text("❌ Invalid user ID. Please provide a valid numeric ID.")
        return

    if not is_gmuted(target_user_id):
        await message.reply_text(f"ℹ️ User `{target_user_id}` is not globally muted.", parse_mode="Markdown")
        return

    remove_gmuted_user(target_user_id)
    await message.reply_text(f"✅ User `{target_user_id}` has been globally unmuted.", parse_mode="Markdown")

async def delete_gmuted_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete messages from globally muted users and send a blacklist warning with a support button."""
    message = update.message
    user = message.from_user
    user_id = user.id
    user_mention = f"[@{user.username}](tg://user?id={user_id})" if user.username else f"[User](tg://user?id={user_id})"

    if is_gmuted(user_id):
        try:
            await message.delete()
            keyboard = [[InlineKeyboardButton("📩 Contact Support", url=f"https://t.me/deadlineTechSupport")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await message.reply_text(
                f"🚫 {user_mention}, **you are blacklisted from using this bot.**\n"
                "❓ If you believe this is a mistake, contact support.",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        except Exception as e:
            print(f"Failed to delete message from {user_id}: {e}")

# Main function
def main():
    """Run the bot"""
    TOKEN = "7990928549:AAHdWiDCZwVv32LG_Sob1gf6qd8IpZVbi9M"

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("auth", auth))
    app.add_handler(CommandHandler("unauth", unauth))
    app.add_handler(CommandHandler("Edev", add_sudo_command))
    app.add_handler(CommandHandler("deldev", del_sudo_command))
    app.add_handler(CommandHandler("authlist", authlist))
    app.add_handler(CommandHandler("devlist", sudolist))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, delete_edited_messages))
    app.add_handler(CommandHandler("delay", set_delay, filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("free", free_user, filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("unfree", unfree_user, filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("gmute", gmute, filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("ungmute", ungmute, filters=filters.ChatType.GROUPS))
    app.add_handler(MessageHandler(filters.ALL, delete_gmuted_messages))  # Delete messages from muted users
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.ATTACHMENT | filters.AUDIO | filters.ANIMATION | filters.Sticker.ALL,
        handle_media
    )) 
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()







