import os
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Replace with your admin IDs (can be one or multiple)
ADMIN_IDS = [123456789, 987654321]  # Add your admin IDs here
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Conversation states
NAME, PRICE, CATEGORY = range(3)

# Database setup
def init_db():
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT NOT NULL,
            added_date TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Check if user is admin
def is_admin(user_id):
    return user_id in ADMIN_IDS

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
🛍️ *Welcome to ShopEasy - Your Personal Shopping Assistant!* 🛍️

Discover amazing products, compare prices, and find exactly what you're looking for with ease!

✨ *Features:*
• 📋 Browse our complete product catalog
• 🔍 Search for specific items
• 🔠 Sort products alphabetically
• 📂 Filter by category

Use the menu below to start exploring! 👇
    """
    
    # Add admin note if user is admin
    if is_admin(update.effective_user.id):
        welcome_text += "\n\n👑 *You have admin privileges!* Use /admin to access admin panel."
    
    keyboard = [
        [InlineKeyboardButton("📋 Browse All Products", callback_data='list')],
        [InlineKeyboardButton("🔍 Search Products", callback_data='search')],
        [InlineKeyboardButton("🔠 Sort A-Z", callback_data='sort')],
        [InlineKeyboardButton("📂 Filter by Category", callback_data='filter')]
    ]
    
    # Add admin button if user is admin
    if is_admin(update.effective_user.id):
        keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data='admin_panel')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send as new message instead of editing
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)
    return ConversationHandler.END

# Admin panel command
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 You are not authorized to use this command.")
        return
    
    # If called from callback query
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        chat_id = query.message.chat_id
        message_id = query.message.message_id
    else:
        chat_id = update.message.chat_id
        message_id = None
        
    admin_text = """
🛠️ *Admin Panel* 🛠️

Welcome to the admin dashboard! Here's what you can do:

• Add new products
• View store statistics
• Manage inventory
    """
    
    # Get some stats for the admin
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM items")
    total_items = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT category) FROM items")
    total_categories = cursor.fetchone()[0]
    conn.close()
    
    admin_text += f"\n📊 *Current Stats:*\n• Total Products: {total_items}\n• Categories: {total_categories}"
    
    keyboard = [
        [InlineKeyboardButton("➕ Add New Product", callback_data='add_item')],
        [InlineKeyboardButton("📊 View Statistics", callback_data='stats')],
        [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await context.bot.send_message(chat_id, admin_text, parse_mode='Markdown', reply_markup=reply_markup)
        await context.bot.delete_message(chat_id, message_id)
    else:
        await update.message.reply_text(admin_text, parse_mode='Markdown', reply_markup=reply_markup)

# Start adding item process
async def start_add_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await context.bot.send_message(
        query.message.chat_id,
        "➕ *Adding New Product*\n\nPlease enter the product name:",
        parse_mode='Markdown'
    )
    
    # Delete the previous message
    await context.bot.delete_message(query.message.chat_id, query.message.message_id)
    
    return NAME

# Get product name
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['item_name'] = update.message.text
    
    await update.message.reply_text(
        "💰 Please enter the product price:",
        parse_mode='Markdown'
    )
    
    return PRICE

# Get product price
async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text)
        context.user_data['item_price'] = price
        
        await update.message.reply_text(
            "📂 Please enter the product category:",
            parse_mode='Markdown'
        )
        
        return CATEGORY
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid price format. Please enter a valid number:",
            parse_mode='Markdown'
        )
        return PRICE

# Get product category and save
async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category = update.message.text
    name = context.user_data['item_name']
    price = context.user_data['item_price']
    added_date = datetime.now().isoformat()

    # Save to database
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO items (name, price, category, added_date) VALUES (?, ?, ?, ?)",
        (name, price, category, added_date)
    )
    conn.commit()
    conn.close()

    # Clear user data
    context.user_data.clear()

    keyboard = [
        [InlineKeyboardButton("➕ Add Another Product", callback_data='add_item')],
        [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
    ]
    
    await update.message.reply_text(
        f"✅ *Product Added Successfully!*\n\n• Name: {name}\n• Price: ${price:.2f}\n• Category: {category}",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ConversationHandler.END

# Cancel conversation
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Operation cancelled.")
    return ConversationHandler.END

# Stats command for admin
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        chat_id = query.message.chat_id
        message_id = query.message.message_id
    else:
        if not is_admin(update.effective_user.id):
            await update.message.reply_text("🚫 You are not authorized to use this command.")
            return
        chat_id = update.message.chat_id
        message_id = None
        
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM items")
    total_items = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT category) FROM items")
    total_categories = cursor.fetchone()[0]
    
    cursor.execute("SELECT category, COUNT(*) FROM items GROUP BY category")
    categories = cursor.fetchall()
    conn.close()
    
    response = "📊 *Store Statistics:*\n\n"
    response += f"• Total Products: {total_items}\n"
    response += f"• Categories: {total_categories}\n\n"
    response += "📂 *Items by Category:*\n"
    
    for category, count in categories:
        response += f"• {category}: {count} items\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Admin Panel", callback_data='admin_panel')]]
    
    if update.callback_query:
        await context.bot.send_message(chat_id, response, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        await context.bot.delete_message(chat_id, message_id)
    else:
        await update.message.reply_text(response, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# Button callback handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'list':
        await list_items(query, context)
    elif query.data == 'sort':
        await sort_items(query, context)
    elif query.data == 'filter':
        await filter_categories(query, context)
    elif query.data == 'search':
        await search_request(query, context)
    elif query.data.startswith('category_'):
        category = query.data.split('_', 1)[1]
        await show_category_items(query, context, category)
    elif query.data == 'back_to_menu':
        await start_callback(query, context)
    elif query.data == 'back_to_categories':
        await filter_categories(query, context)
    elif query.data == 'admin_panel':
        await admin_panel(update, context)
    elif query.data == 'add_item':
        await start_add_item(update, context)
    elif query.data == 'stats':
        await stats(update, context)

# List all items
async def list_items(query, context):
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, price, category FROM items")
    items = cursor.fetchall()
    conn.close()

    if not items:
        keyboard = [[InlineKeyboardButton("🏠 Back to Main Menu", callback_data='back_to_menu')]]
        await context.bot.send_message(
            query.message.chat_id,
            "📭 Our catalog is currently empty. Check back soon for new products!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await context.bot.delete_message(query.message.chat_id, query.message.message_id)
        return

    response = "📦 *All Products:*\n\n"
    for item in items:
        response += f"• *{item[0]}* - ${item[1]:.2f} ({item[2]})\n"

    keyboard = [
        [InlineKeyboardButton("🔄 Sort A-Z", callback_data='sort')],
        [InlineKeyboardButton("📂 Filter by Category", callback_data='filter')],
        [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
    ]
    
    await context.bot.send_message(
        query.message.chat_id,
        response,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await context.bot.delete_message(query.message.chat_id, query.message.message_id)

# Sort items A-Z
async def sort_items(query, context):
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, price, category FROM items ORDER BY name")
    items = cursor.fetchall()
    conn.close()

    if not items:
        keyboard = [[InlineKeyboardButton("🏠 Back to Main Menu", callback_data='back_to_menu')]]
        await context.bot.send_message(
            query.message.chat_id,
            "📭 Our catalog is currently empty. Check back soon for new products!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await context.bot.delete_message(query.message.chat_id, query.message.message_id)
        return

    response = "🔠 *Products Sorted A-Z:*\n\n"
    for item in items:
        response += f"• *{item[0]}* - ${item[1]:.2f} ({item[2]})\n"

    keyboard = [
        [InlineKeyboardButton("📋 View All Products", callback_data='list')],
        [InlineKeyboardButton("📂 Filter by Category", callback_data='filter')],
        [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
    ]
    
    await context.bot.send_message(
        query.message.chat_id,
        response,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await context.bot.delete_message(query.message.chat_id, query.message.message_id)

# Show categories for filtering
async def filter_categories(query, context):
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM items")
    categories = cursor.fetchall()
    conn.close()

    if not categories:
        keyboard = [[InlineKeyboardButton("🏠 Back to Main Menu", callback_data='back_to_menu')]]
        await context.bot.send_message(
            query.message.chat_id,
            "📭 No categories available yet. Check back soon!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await context.bot.delete_message(query.message.chat_id, query.message.message_id)
        return

    keyboard = []
    for category in categories:
        keyboard.append([InlineKeyboardButton(
            f"📂 {category[0]}", callback_data=f'category_{category[0]}')])
    keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')])

    await context.bot.send_message(
        query.message.chat_id,
        "📂 *Select a category:*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await context.bot.delete_message(query.message.chat_id, query.message.message_id)

# Show items in specific category
async def show_category_items(query, context, category):
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, price, category FROM items WHERE category = ?",
        (category,)
    )
    items = cursor.fetchall()
    conn.close()

    if not items:
        keyboard = [
            [InlineKeyboardButton("📂 Back to Categories", callback_data='back_to_categories')],
            [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
        ]
        await context.bot.send_message(
            query.message.chat_id,
            f"📭 No products found in '{category}' category. Check back soon!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await context.bot.delete_message(query.message.chat_id, query.message.message_id)
        return

    response = f"📂 *Products in {category}:*\n\n"
    for item in items:
        response += f"• *{item[0]}* - ${item[1]:.2f}\n"

    keyboard = [
        [InlineKeyboardButton("📂 Back to Categories", callback_data='back_to_categories')],
        [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
    ]
    
    await context.bot.send_message(
        query.message.chat_id,
        response,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await context.bot.delete_message(query.message.chat_id, query.message.message_id)

# Search request handler
async def search_request(query, context):
    await context.bot.send_message(
        query.message.chat_id,
        "🔍 What would you like to search for? Please type your search term:"
    )
    context.user_data['awaiting_search'] = True
    await context.bot.delete_message(query.message.chat_id, query.message.message_id)

# Handle search messages
async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_search'):
        return

    search_term = update.message.text.lower()
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, price, category FROM items WHERE LOWER(name) LIKE ?",
        (f'%{search_term}%',)
    )
    items = cursor.fetchall()
    conn.close()

    if not items:
        keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]]
        await update.message.reply_text(
            f"🔍 No products found matching '{search_term}'. Try different keywords or browse our full catalog!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data['awaiting_search'] = False
        return

    response = f"🔍 *Search results for '{search_term}':*\n\n"
    for item in items:
        response += f"• *{item[0]}* - ${item[1]:.2f} ({item[2]})\n"

    keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]]
    await update.message.reply_text(response, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data['awaiting_search'] = False

# Start callback for back button
async def start_callback(query, context):
    welcome_text = """
🛍️ *Welcome to ShopEasy - Your Personal Shopping Assistant!* 🛍️

Discover amazing products, compare prices, and find exactly what you're looking for with ease!

✨ *Features:*
• 📋 Browse our complete product catalog
• 🔍 Search for specific items
• 🔠 Sort products alphabetically
• 📂 Filter by category

Use the menu below to start exploring! 👇
    """
    
    # Add admin note if user is admin
    if is_admin(query.from_user.id):
        welcome_text += "\n\n👑 *You have admin privileges!* Use /admin to access admin panel."
    
    keyboard = [
        [InlineKeyboardButton("📋 Browse All Products", callback_data='list')],
        [InlineKeyboardButton("🔍 Search Products", callback_data='search')],
        [InlineKeyboardButton("🔠 Sort A-Z", callback_data='sort')],
        [InlineKeyboardButton("📂 Filter by Category", callback_data='filter')]
    ]
    
    # Add admin button if user is admin
    if is_admin(query.from_user.id):
        keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data='admin_panel')])
    
    await context.bot.send_message(
        query.message.chat_id,
        welcome_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await context.bot.delete_message(query.message.chat_id, query.message.message_id)

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    # Add conversation handler for adding items
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_item, pattern='^add_item$')],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
            CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_category)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
