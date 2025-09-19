import os
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Replace with your admin IDs (can be one or multiple)
ADMIN_IDS = [6363616486,1883435286]  # Add your admin IDs here
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Conversation states
NAME, PRICE, CATEGORY = range(3)
EDIT_ITEM, EDIT_FIELD, EDIT_VALUE = range(3, 6)
ADD_CATEGORY = 6

# Database setup
def init_db():
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    
    # Create items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT NOT NULL,
            added_date TEXT NOT NULL
        )
    ''')
    
    # Create categories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')
    
    # Insert default categories if they don't exist
    default_categories = ['Electronics', 'Clothing', 'Food', 'Books', 'Furniture']
    for category in default_categories:
        try:
            cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (category,))
        except:
            pass
    
    conn.commit()
    conn.close()

# Check if user is admin
def is_admin(user_id):
    return user_id in ADMIN_IDS

# Get all categories from database
def get_categories():
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM categories ORDER BY name")
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return categories

# Add a new category to database
def add_category(category_name):
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO categories (name) VALUES (?)", (category_name,))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False  # Category already exists
    conn.close()
    return success

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
🛍️ *Welcome to Sami Shopping* 🛍️

Browse products, compare prices, and find what you're looking for with ease!

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
• Edit existing products
• Delete products
• Manage categories
• View store statistics
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
        [InlineKeyboardButton("✏️ Edit Products", callback_data='edit_items')],
        [InlineKeyboardButton("🗑️ Delete Products", callback_data='delete_items')],
        [InlineKeyboardButton("📂 Manage Categories", callback_data='manage_categories')],
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
        "💰 Please enter the product price in ETB:",
        parse_mode='Markdown'
    )
    
    return PRICE

# Get product price
async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text)
        context.user_data['item_price'] = price
        
        # Show categories as buttons
        categories = get_categories()
        keyboard = []
        for category in categories:
            keyboard.append([InlineKeyboardButton(category, callback_data=f'cat_{category}')])
        keyboard.append([InlineKeyboardButton("➕ Add New Category", callback_data='add_new_category')])
        
        await update.message.reply_text(
            "📂 Please select a category or add a new one:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return CATEGORY
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid price format. Please enter a valid number:",
            parse_mode='Markdown'
        )
        return PRICE

# Handle category selection
async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'add_new_category':
        await context.bot.send_message(
            query.message.chat_id,
            "📂 Please enter the new category name:",
            parse_mode='Markdown'
        )
        return ADD_CATEGORY
    else:
        category = query.data.replace('cat_', '')
        await save_product(context, category, query.message.chat_id)
        return ConversationHandler.END

# Add new category
async def add_new_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category_name = update.message.text
    success = add_category(category_name)
    
    if success:
        await save_product(context, category_name, update.message.chat_id)
    else:
        await update.message.reply_text(
            "❌ This category already exists. Please select a category from the list:",
            parse_mode='Markdown'
        )
        # Show categories again
        categories = get_categories()
        keyboard = []
        for category in categories:
            keyboard.append([InlineKeyboardButton(category, callback_data=f'cat_{category}')])
        keyboard.append([InlineKeyboardButton("➕ Add New Category", callback_data='add_new_category')])
        
        await update.message.reply_text(
            "📂 Please select a category:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CATEGORY
    
    return ConversationHandler.END

# Save product to database
async def save_product(context, category, chat_id):
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
    
    await context.bot.send_message(
        chat_id,
        f"✅ *Product Added Successfully!*\n\n• Name: {name}\n• Price: {price:.2f} ETB\n• Category: {category}",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Edit products - show list
async def edit_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price, category FROM items ORDER BY name")
    items = cursor.fetchall()
    conn.close()

    if not items:
        keyboard = [[InlineKeyboardButton("🔙 Back to Admin Panel", callback_data='admin_panel')]]
        await context.bot.send_message(
            query.message.chat_id,
            "📭 No products available to edit.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await context.bot.delete_message(query.message.chat_id, query.message.message_id)
        return

    response = "✏️ *Select a product to edit:*\n\n"
    keyboard = []
    
    for item in items:
        response += f"• {item[1]} - {item[2]:.2f} ETB ({item[3]})\n"
        keyboard.append([InlineKeyboardButton(
            f"✏️ {item[1]}", callback_data=f'edit_{item[0]}')])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Admin Panel", callback_data='admin_panel')])
    
    await context.bot.send_message(
        query.message.chat_id,
        response,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await context.bot.delete_message(query.message.chat_id, query.message.message_id)
    
    return EDIT_ITEM

# Edit a specific product
async def edit_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    product_id = query.data.replace('edit_', '')
    context.user_data['edit_product_id'] = product_id
    
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, price, category FROM items WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    conn.close()
    
    if not product:
        await query.message.reply_text("❌ Product not found.")
        return ConversationHandler.END
    
    response = f"✏️ *Editing Product:*\n\n• Name: {product[0]}\n• Price: {product[1]:.2f} ETB\n• Category: {product[2]}\n\nSelect what you want to edit:"
    
    keyboard = [
        [InlineKeyboardButton("📝 Name", callback_data='edit_field_name')],
        [InlineKeyboardButton("💰 Price", callback_data='edit_field_price')],
        [InlineKeyboardButton("📂 Category", callback_data='edit_field_category')],
        [InlineKeyboardButton("🔙 Back to Products", callback_data='edit_items')]
    ]
    
    await context.bot.send_message(
        query.message.chat_id,
        response,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await context.bot.delete_message(query.message.chat_id, query.message.message_id)
    
    return EDIT_FIELD

# Handle field selection for editing
async def edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    field = query.data.replace('edit_field_', '')
    context.user_data['edit_field'] = field
    
    if field == 'category':
        # Show categories as buttons
        categories = get_categories()
        keyboard = []
        for category in categories:
            keyboard.append([InlineKeyboardButton(category, callback_data=f'edit_cat_{category}')])
        
        await context.bot.send_message(
            query.message.chat_id,
            "📂 Select a new category:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return EDIT_VALUE
    else:
        field_name = "name" if field == "name" else "price"
        await context.bot.send_message(
            query.message.chat_id,
            f"📝 Enter the new {field_name}:",
            parse_mode='Markdown'
        )
        await context.bot.delete_message(query.message.chat_id, query.message.message_id)
        return EDIT_VALUE

# Handle category selection for editing
async def edit_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    new_value = query.data.replace('edit_cat_', '')
    await update_product_field(context, new_value, query.message.chat_id)
    return ConversationHandler.END

# Handle text input for editing
async def edit_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_value = update.message.text
    field = context.user_data['edit_field']
    
    if field == 'price':
        try:
            new_value = float(new_value)
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid price format. Please enter a valid number:",
                parse_mode='Markdown'
            )
            return EDIT_VALUE
    
    await update_product_field(context, new_value, update.message.chat_id)
    return ConversationHandler.END

# Update product field in database
async def update_product_field(context, new_value, chat_id):
    product_id = context.user_data['edit_product_id']
    field = context.user_data['edit_field']
    
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    
    if field == 'name':
        cursor.execute("UPDATE items SET name = ? WHERE id = ?", (new_value, product_id))
    elif field == 'price':
        cursor.execute("UPDATE items SET price = ? WHERE id = ?", (new_value, product_id))
    elif field == 'category':
        cursor.execute("UPDATE items SET category = ? WHERE id = ?", (new_value, product_id))
    
    conn.commit()
    conn.close()
    
    # Clear user data
    context.user_data.clear()
    
    keyboard = [
        [InlineKeyboardButton("✏️ Edit Another Product", callback_data='edit_items')],
        [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
    ]
    
    await context.bot.send_message(
        chat_id,
        f"✅ Product updated successfully!",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Delete products - show list
async def delete_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price, category FROM items ORDER BY name")
    items = cursor.fetchall()
    conn.close()

    if not items:
        keyboard = [[InlineKeyboardButton("🔙 Back to Admin Panel", callback_data='admin_panel')]]
        await context.bot.send_message(
            query.message.chat_id,
            "📭 No products available to delete.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await context.bot.delete_message(query.message.chat_id, query.message.message_id)
        return

    response = "🗑️ *Select a product to delete:*\n\n"
    keyboard = []
    
    for item in items:
        response += f"• {item[1]} - {item[2]:.2f} ETB ({item[3]})\n"
        keyboard.append([InlineKeyboardButton(
            f"🗑️ {item[1]}", callback_data=f'delete_{item[0]}')])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Admin Panel", callback_data='admin_panel')])
    
    await context.bot.send_message(
        query.message.chat_id,
        response,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await context.bot.delete_message(query.message.chat_id, query.message.message_id)

# Delete a specific product
async def delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    product_id = query.data.replace('delete_', '')
    
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM items WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    
    keyboard = [
        [InlineKeyboardButton("🗑️ Delete Another Product", callback_data='delete_items')],
        [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
    ]
    
    await context.bot.send_message(
        query.message.chat_id,
        "✅ Product deleted successfully!",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await context.bot.delete_message(query.message.chat_id, query.message.message_id)

# Manage categories
async def manage_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    categories = get_categories()
    
    response = "📂 *Current Categories:*\n\n"
    for category in categories:
        response += f"• {category}\n"
    
    keyboard = [
        [InlineKeyboardButton("➕ Add New Category", callback_data='add_category_direct')],
        [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data='admin_panel')]
    ]
    
    await context.bot.send_message(
        query.message.chat_id,
        response,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await context.bot.delete_message(query.message.chat_id, query.message.message_id)

# Add category directly
async def add_category_direct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await context.bot.send_message(
        query.message.chat_id,
        "📂 Please enter the new category name:",
        parse_mode='Markdown'
    )
    await context.bot.delete_message(query.message.chat_id, query.message.message_id)
    
    return ADD_CATEGORY

# Add new category directly
async def add_category_direct_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category_name = update.message.text
    success = add_category(category_name)
    
    if success:
        await update.message.reply_text(
            f"✅ Category '{category_name}' added successfully!",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"❌ Category '{category_name}' already exists.",
            parse_mode='Markdown'
        )
    
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
    
    cursor.execute("SELECT SUM(price) FROM items")
    total_value = cursor.fetchone()[0] or 0
    
    conn.close()
    
    response = "📊 *Store Statistics:*\n\n"
    response += f"• Total Products: {total_items}\n"
    response += f"• Total Inventory Value: {total_value:.2f} ETB\n"
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

# Cancel conversation
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Operation cancelled.")
    return ConversationHandler.END

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
    elif query.data == 'edit_items':
        await edit_items(update, context)
    elif query.data.startswith('edit_'):
        await edit_product(update, context)
    elif query.data.startswith('edit_field_'):
        await edit_field(update, context)
    elif query.data.startswith('edit_cat_'):
        await edit_category(update, context)
    elif query.data == 'delete_items':
        await delete_items(update, context)
    elif query.data.startswith('delete_'):
        await delete_product(update, context)
    elif query.data == 'manage_categories':
        await manage_categories(update, context)
    elif query.data == 'add_category_direct':
        await add_category_direct(update, context)

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
        response += f"• *{item[0]}* - {item[1]:.2f} ETB ({item[2]})\n"

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
        response += f"• *{item[0]}* - {item[1]:.2f} ETB ({item[2]})\n"

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
    categories = get_categories()

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
            f"📂 {category}", callback_data=f'category_{category}')])
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
        response += f"• *{item[0]}* - {item[1]:.2f} ETB\n"

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
        response += f"• *{item[0]}* - {item[1]:.2f} ETB ({item[2]})\n"

    keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]]
    await update.message.reply_text(response, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data['awaiting_search'] = False

# Start callback for back button
async def start_callback(query, context):
    welcome_text = """
🛍️ *Welcome to Sami Shopping* 🛍️

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
    add_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_item, pattern='^add_item$')],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
            CATEGORY: [CallbackQueryHandler(handle_category, pattern='^(cat_|add_new_category)')],
            ADD_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_new_category)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Add conversation handler for editing items
    edit_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_field, pattern='^edit_field_')],
        states={
            EDIT_VALUE: [
                CallbackQueryHandler(edit_category, pattern='^edit_cat_'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_value)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Add conversation handler for adding categories directly
    category_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_category_direct, pattern='^add_category_direct$')],
        states={
            ADD_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_category_direct_handler)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(add_conv_handler)
    app.add_handler(edit_conv_handler)
    app.add_handler(category_conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
