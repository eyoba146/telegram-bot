from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)
from datetime import datetime

# Replace with your Telegram user ID (you can get it from @userinfobot)
ADMIN_ID = 123456789  

# Storage for items (use SQLite for persistence later)
items = []

# --- ADMIN COMMANDS ---

async def add_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to add items.")
        return
    
    if len(context.args) < 3:
        await update.message.reply_text("Usage: /add <name> <price> <type>")
        return
    
    name = context.args[0]
    price = context.args[1]
    category = context.args[2]
    time_added = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    items.append({"name": name, "price": price, "type": category, "time": time_added})
    await update.message.reply_text(f"✅ Added {name} (${price}) in {category} at {time_added}")

# --- USER COMMANDS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📋 List Items", callback_data="list")],
        [InlineKeyboardButton("🔎 Search", callback_data="search")],
        [InlineKeyboardButton("🔠 Sort A-Z", callback_data="sort")],
        [InlineKeyboardButton("📂 Filter by Type", callback_data="filter")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👋 Welcome! Choose an option:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "list":
        if not items:
            await query.edit_message_text("📭 No items available.")
            return
        text = "\n".join([f"{i+1}. {item['name']} - ${item['price']} ({item['type']})"
                          for i, item in enumerate(items)])
        await query.edit_message_text(f"📋 Items:\n{text}")
    
    elif query.data == "sort":
        sorted_items = sorted(items, key=lambda x: x["name"])
        text = "\n".join([f"{i+1}. {item['name']} - ${item['price']} ({item['type']})"
                          for i, item in enumerate(sorted_items)])
        await query.edit_message_text(f"🔠 Sorted A-Z:\n{text}")
    
    elif query.data == "filter":
        categories = list(set([item["type"] for item in items]))
        if not categories:
            await query.edit_message_text("📭 No categories yet.")
            return
        keyboard = [[InlineKeyboardButton(cat, callback_data=f"cat_{cat}")] for cat in categories]
        await query.edit_message_text("📂 Choose category:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data.startswith("cat_"):
        cat = query.data.split("_", 1)[1]
        filtered = [item for item in items if item["type"] == cat]
        if not filtered:
            await query.edit_message_text(f"📂 No items found in {cat}.")
            return
        text = "\n".join([f"{i+1}. {item['name']} - ${item['price']}" for i, item in enumerate(filtered)])
        await query.edit_message_text(f"📂 {cat}:\n{text}")
    
    elif query.data == "search":
        await query.edit_message_text("🔎 Send me a search term (just type it here).")
        context.user_data["search_mode"] = True

async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("search_mode"):
        query = update.message.text.lower()
        results = [item for item in items if query in item["name"].lower()]
        if results:
            text = "\n".join([f"{i+1}. {item['name']} - ${item['price']} ({item['type']})"
                              for i, item in enumerate(results)])
            await update.message.reply_text(f"🔎 Search results:\n{text}")
        else:
            await update.message.reply_text("❌ No items found.")
        context.user_data["search_mode"] = False

def main():
    app = Application.builder().token("YOUR_TELEGRAM_BOT_TOKEN").build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_item))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler))
    
    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
