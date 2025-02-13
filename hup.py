import random
import pymongo
import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

# Telegram Bot Token
TOKEN = "7470264967:AAHTssrBhJ2IyNOpzdCGMTlaANqf8B2Je-k"

# MongoDB Connection
client = pymongo.MongoClient("mongodb+srv://botmaker9675208:botmaker9675208@cluster0.sc9mq8b.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["battle_game"]
players_collection = db["players"]

# Game Data Storage
game_data = {}

# Weapons List
weapons = {
    "sword": {"name": "Sword", "power": 15, "cost": 200},
    "axe": {"name": "Axe", "power": 20, "cost": 300},
    "spear": {"name": "Spear", "power": 25, "cost": 400}
}

class Player:
    def __init__(self, user_id, name, gold=0, weapon=None):
        self.user_id = user_id
        self.name = name
        self.gold = gold
        self.weapon = weapon  
        self.base_strength = random.randint(60, 90)
        self.special_attack = 1  

    def fight(self, opponent, use_special):
        my_weapon_bonus = self.weapon["power"] if self.weapon else 0
        my_power = self.base_strength + my_weapon_bonus + (20 if use_special and self.special_attack > 0 else 0)
        opp_weapon_bonus = opponent.weapon["power"] if opponent.weapon else 0
        opp_power = opponent.base_strength + opp_weapon_bonus

        if use_special and self.special_attack > 0:
            self.special_attack -= 1

        return self if my_power > opp_power else opponent

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "⚔ **Welcome to Battle Game!** ⚔\n\n"
        "🔥 Earn gold, buy weapons, and fight in battles!\n\n"
        "🎮 **Commands:**\n"
        "🆕 `/newgame solo` – Play against a bot\n"
        "🆕 `/newgame multiplayer` – Start a team battle\n"
        "👥 `/join` – Join a multiplayer battle\n"
        "⚔ `/fight` – Start the fight\n"
        "🏆 `/result` – See who won\n"
        "💰 `/gold` – Check your balance\n"
        "🛒 `/shop` – View weapons\n"
        "💵 `/buy <weapon>` – Purchase weapons\n"
        "🎁 `/daily` – Claim 10 gold daily"
    )

async def daily(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    player = players_collection.find_one({"user_id": user_id})

    today = str(datetime.date.today())

    if player and player.get("last_daily") == today:
        await update.message.reply_text("❌ You already claimed your daily bonus today!")
        return

    if not player:
        players_collection.insert_one({"user_id": user_id, "name": update.effective_user.first_name, "gold": 100, "last_daily": today})
    else:
        players_collection.update_one({"user_id": user_id}, {"$inc": {"gold": 10}, "$set": {"last_daily": today}})

    await update.message.reply_text("💰 **You claimed 10 gold!** Use `/shop` to buy weapons.")

async def gold(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    player = players_collection.find_one({"user_id": user_id})
    
    if not player:
        await update.message.reply_text("💰 You have **0 gold**.")
    else:
        await update.message.reply_text(f"💰 You have **{player['gold']} gold**.")

async def shop(update: Update, context: CallbackContext):
    shop_text = "🛒 **Weapon Shop** 🛒\n\n"
    for key, weapon in weapons.items():
        shop_text += f"🗡 **{weapon['name']}** - 💰 {weapon['cost']} gold (+{weapon['power']} Power)\n"

    shop_text += "\n💰 Earn gold by fighting or use `/daily` for a free bonus!"
    await update.message.reply_text(shop_text)

async def buy(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    args = context.args

    if not args:
        await update.message.reply_text("Usage: `/buy <weapon_name>`")
        return

    weapon_name = args[0].lower()
    if weapon_name not in weapons:
        await update.message.reply_text("❌ Weapon not found! Use `/shop` to see available weapons.")
        return

    weapon = weapons[weapon_name]
    player = players_collection.find_one({"user_id": user_id})

    if not player or player["gold"] < weapon["cost"]:
        await update.message.reply_text("❌ You don't have enough gold!")
        return

    players_collection.update_one({"user_id": user_id}, {"$inc": {"gold": -weapon["cost"]}, "$set": {"weapon": weapon}})
    await update.message.reply_text(f"✅ You bought a **{weapon['name']}**! Power: +{weapon['power']}")

async def fight(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in game_data:
        await update.message.reply_text("Start a game first with `/newgame solo` or `/newgame multiplayer`!")
        return

    game = game_data[chat_id]
    player = players_collection.find_one({"user_id": user_id})

    if not player:
        await update.message.reply_text("❌ You need to start a game first using `/newgame solo`!")
        return

    player_obj = Player(user_id, player["name"], player["gold"], player.get("weapon"))
    bot = Player(0, "Bot Fighter")

    use_special_player = random.choice([True, False])
    use_special_bot = random.choice([True, False])

    winner = player_obj.fight(bot, use_special_player)
    round_winner = player_obj.name if winner == player_obj else "Bot Fighter"

    if winner == player_obj:
        new_gold = random.randint(5, 15)
        players_collection.update_one({"user_id": user_id}, {"$inc": {"gold": new_gold}})
        await update.message.reply_text(f"🏆 **{player_obj.name} won!**\n💰 Earned {new_gold} gold!")
    else:
        await update.message.reply_text(f"❌ You lost! Try again.")

async def newgame(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    args = context.args

    if not args or args[0] not in ["solo", "multiplayer"]:
        await update.message.reply_text("Please specify: `/newgame solo` or `/newgame multiplayer`.")
        return

    mode = args[0]
    game_data[chat_id] = {"mode": mode}

    await update.message.reply_text(f"✅ **{mode.capitalize()} battle started!** Type `/fight` to begin.")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("newgame", newgame))
    app.add_handler(CommandHandler("fight", fight))
    app.add_handler(CommandHandler("gold", gold))
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("daily", daily))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
