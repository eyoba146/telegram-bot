import os
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Replace with your admin IDs (can be one or multiple)
ADMIN_IDS = [6363616486]  # Add your admin IDs here
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

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

# Admin command handler
async def add_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 You are not authorized to use this command.")
        return

    try:
        name = context.args[0]
        price = float(context.args[1])
        category = ' '.join(context.args[2:])
        added_date = datetime.now().isoformat()

        conn = sqlite3.connect('items.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO items (name, price, category, added_date) VALUES (?, ?, ?, ?)",
            (name, price, category, added_date)
        )
        conn.commit()
        conn.close()

        await update.message.reply_text("✅ Item added successfully!")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Usage: /add <name> <price> <category>")

# Admin panel command
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 You are not authorized to use this command.")
        return
        
    admin_text = """
🛠️ *Admin Panel* 🛠️

Welcome to the admin dashboard! Here's what you can do:

• /add <name> <price> <category> - Add a new product
• /stats - View store statistics
• /broadcast - Send message to all users (coming soon)
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
    
    await update.message.reply_text(admin_text, parse_mode='Markdown')

# Stats command for admin
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 You are not authorized to use this command.")
        return
        
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
    
    await update.message.reply_text(response, parse_mode='Markdown')

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
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)

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
        await query.message.reply_text("🔍 What would you like to search for? Please type your search term:")
        context.user_data['awaiting_search'] = True
    elif query.data.startswith('category_'):
        category = query.data.split('_', 1)[1]
        await show_category_items(query, context, category)
    elif query.data == 'back_to_menu':
        await start_callback(query, context)
    elif query.data == 'back_to_categories':
        await filter_categories(query, context)

# List all items
async def list_items(query, context):
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, price, category FROM items")
    items = cursor.fetchall()
    conn.close()

    if not items:
        keyboard = [[InlineKeyboardButton("🏠 Back to Main Menu", callback_data='back_to_menu')]]
        await query.message.edit_text(
            "📭 Our catalog is currently empty. Check back soon for new products!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    response = "📦 *All Products:*\n\n"
    for item in items:
        response += f"• *{item[0]}* - ${item[1]:.2f} ({item[2]})\n"

    keyboard = [
        [InlineKeyboardButton("🔄 Sort A-Z", callback_data='sort')],
        [InlineKeyboardButton("📂 Filter by Category", callback_data='filter')],
        [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
    ]
    await query.message.edit_text(response, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# Sort items A-Z
async def sort_items(query, context):
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, price, category FROM items ORDER BY name")
    items = cursor.fetchall()
    conn.close()

    if not items:
        keyboard = [[InlineKeyboardButton("🏠 Back to Main Menu", callback_data='back_to_menu')]]
        await query.message.edit_text(
            "📭 Our catalog is currently empty. Check back soon for new products!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    response = "🔠 *Products Sorted A-Z:*\n\n"
    for item in items:
        response += f"• *{item[0]}* - ${item[1]:.2f} ({item[2]})\n"

    keyboard = [
        [InlineKeyboardButton("📋 View All Products", callback_data='list')],
        [InlineKeyboardButton("📂 Filter by Category", callback_data='filter')],
        [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
    ]
    await query.message.edit_text(response, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# Show categories for filtering
async def filter_categories(query, context):
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM items")
    categories = cursor.fetchall()
    conn.close()

    if not categories:
        keyboard = [[InlineKeyboardButton("🏠 Back to Main Menu", callback_data='back_to_menu')]]
        await query.message.edit_text(
            "📭 No categories available yet. Check back soon!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    keyboard = []
    for category in categories:
        keyboard.append([InlineKeyboardButton(
            f"📂 {category[0]}", callback_data=f'category_{category[0]}')])
    keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')])

    await query.message.edit_text(
        "📂 *Select a category:*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

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
        await query.message.edit_text(
            f"📭 No products found in '{category}' category. Check back soon!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    response = f"📂 *Products in {category}:*\n\n"
    for item in items:
        response += f"• *{item[0]}* - ${item[1]:.2f}\n"

    keyboard = [
        [InlineKeyboardButton("📂 Back to Categories", callback_data='back_to_categories')],
        [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
    ]
    await query.message.edit_text(response, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

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
    await query.message.edit_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_item))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
