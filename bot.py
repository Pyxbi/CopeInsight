import logging
import requests
import functools
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from config import ADMIN_ID, COINGECKO_URL, TELEGRAM_BOT_API_KEY
import database as db

# --- CONFIGURATION ---
# Replace with your Bot Token from BotFather
BOT_TOKEN = TELEGRAM_BOT_API_KEY
# Replace with your Telegram User ID
ADMIN = ADMIN_ID 

# CoinGecko API for fetching crypto prices
COINGECKO_API_URL = COINGECKO_URL


# You can expand this list with more coins. Find IDs on the CoinGecko website.
COIN_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "DOGE": "dogecoin",
}

# --- SETUP ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

# --- HELPER FUNCTIONS & DECORATORS ---

def admin_only(func):
    """Decorator to restrict command access to the admin in a channel/group."""
    @functools.wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        # Use effective_ properties to handle both messages and channel posts
        user = update.effective_user
        chat = update.effective_chat
        message = update.effective_message

        # A safeguard in case the update is unusual (e.g., a poll update)
        if not user or not chat or not message:
            logging.warning("Admin decorator received an update without user, chat, or message info.")
            return

        # # 1. Check if the user is the admin
        # if user.id != ADMIN_ID:
        #     await message.reply_text("Sorry, this command is for the admin only.")
        #     return

        # 2. Check if the command is in a public channel/group
        if chat.type == 'private':
            await message.reply_text("Please use trade management commands in the main channel.")
            return

        # If all checks pass, run the original command function
        return await func(update, context, *args, **kwargs)
    return wrapped

def private_chat_only(func):
    """Decorator to ensure a command is only used in a private chat."""
    @functools.wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.message.chat.type != 'private':
            await update.message.reply_text("This command is only available in a private message with me.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

async def get_crypto_price(ticker: str) -> float | None:
    """Fetches the current price of a cryptocurrency from CoinGecko."""
    coingecko_id = COIN_MAP.get(ticker.upper())
    if not coingecko_id:
        return None
    
    params = {"ids": coingecko_id, "vs_currencies": "usd"}
    try:
        response = requests.get(COINGECKO_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        return data[coingecko_id]["usd"]
    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed: {e}")
        return None

# --- ADMIN COMMANDS (Channel/Group) ---

@admin_only
async def new_trade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Opens a new spot or futures trade. /new_spot BTC 118000 0.1"""
    # Get the command used, e.g., "/new_spot"
    command = update.effective_message.text.split()[0]
    trade_type = "SPOT" if "spot" in command else "FUTURES"
    
    try:
        # CORRECTED: Unpack only the 3 arguments provided after the command.
        ticker, price_str, size_str = context.args
        price = float(price_str)
        size = float(size_str)
    except (ValueError, IndexError):
        # CORRECTED: The error message now shows the full, correct command format.
        await update.effective_message.reply_text(
            f"❌ Invalid format. Use: {command} [ticker] [price] [size]"
        )
        return

    # Check if a trade for this coin is already open
    if db.get_open_trade_by_ticker(ticker, trade_type):
        await update.effective_message.reply_text(f"⚠️ A {trade_type} trade for ${ticker.upper()} is already open.")
        return

    # Get the link to the original message
    post_link = update.effective_message.link

    db.add_trade(ticker, trade_type, price, size, post_link)
    await update.effective_message.reply_text(
        f"✅ New {trade_type} trade opened for ${ticker.upper()}.\n"
        f"Entry Price: ${price:,.2f}\n"
        f"Size: {size}"
    )

@admin_only
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Adds to an existing position (DCA). /buy spot BTC 0.5 65000"""
    try:
        trade_type, ticker, amount_str, price_str = context.args
        amount = float(amount_str)
        price = float(price_str)
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid format. Use: /buy [type] [ticker] [amount] [price]")
        return

    trade = db.get_open_trade_by_ticker(ticker, trade_type)
    if not trade:
        await update.message.reply_text(f"🤷 No open {trade_type.upper()} trade found for ${ticker.upper()}.")
        return

    # Calculate new average price (DCA)
    old_avg_price = trade['average_entry_price']
    old_size = trade['total_position_size']
    
    new_total_size = old_size + amount
    new_avg_price = ((old_avg_price * old_size) + (price * amount)) / new_total_size
    
    db.dca_update_trade(trade['id'], new_avg_price, new_total_size)
    
    await update.message.reply_text(
        f"🟢 Bought more ${ticker.upper()} ({trade_type.upper()}).\n"
        f"New Average Entry: ${new_avg_price:,.2f}\n"
        f"New Total Size: {new_total_size}"
    )

@admin_only
async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sells a portion of the position. /sell spot BTC 50 72000"""
    try:
        trade_type, ticker, percent_str, price_str = context.args
        percent_to_sell = int(percent_str)
        price = float(price_str)
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid format. Use: /sell [type] [ticker] [percent] [price]")
        return
        
    if not 0 < percent_to_sell <= 100:
        await update.message.reply_text("❌ Percentage must be between 1 and 100.")
        return

    trade = db.get_open_trade_by_ticker(ticker, trade_type)
    if not trade:
        await update.message.reply_text(f"🤷 No open {trade_type.upper()} trade for ${ticker.upper()}.")
        return
        
    if percent_to_sell > trade['remaining_percent']:
        await update.message.reply_text(f"❌ Cannot sell {percent_to_sell}%. Only {trade['remaining_percent']}% remaining.")
        return

    new_remaining_percent = trade['remaining_percent'] - percent_to_sell
    db.sell_update_trade(trade['id'], new_remaining_percent)

    pnl = ((price - trade['average_entry_price']) / trade['average_entry_price']) * 100
    
    response = (
        f"💰 Sold {percent_to_sell}% of ${ticker.upper()} at ${price:,.2f} for a ~{pnl:.2f}% profit.\n"
        f"{new_remaining_percent}% of the position remains open."
    )
    if new_remaining_percent == 0:
        response = f"💰 Closed final part of ${ticker.upper()} at ${price:,.2f} for a ~{pnl:.2f}% profit. Position is now fully closed."

    await update.message.reply_text(response)


@admin_only
async def close(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Closes the entire remaining position. /close spot BTC 71000"""
    try:
        trade_type, ticker, price_str = context.args
        price = float(price_str)
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid format. Use: /close [type] [ticker] [price]")
        return

    trade = db.get_open_trade_by_ticker(ticker, trade_type)
    if not trade:
        await update.message.reply_text(f"🤷 No open {trade_type.upper()} trade for ${ticker.upper()}.")
        return

    pnl = ((price - trade['average_entry_price']) / trade['average_entry_price']) * 100
    db.close_trade(trade['id'])

    await update.message.reply_text(
        f"❌ Trade Closed for ${ticker.upper()} ({trade_type.upper()}).\n"
        f"Closed at: ${price:,.2f}\n"
        f"Final PNL: {pnl:.2f}%"
    )

# --- USER COMMANDS (Private Chat) ---

@private_chat_only
async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows all open Spot and Futures positions."""
    command = update.message.text.split()[0].lower() # /portfolio, /portfolio_spot, etc
    
    all_positions = db.get_all_open_positions()
    if not all_positions:
        await update.message.reply_text("The admin has no open positions right now. 🤷‍♂️")
        return

    spot_positions = [p for p in all_positions if p['trade_type'] == 'SPOT']
    futures_positions = [p for p in all_positions if p['trade_type'] == 'FUTURES']

    response_parts = []
    
    # Generate Spot Portfolio
    if 'spot' in command or 'all' in command:
        if spot_positions:
            response_parts.append("--- 🟢 Admin's Open Spot Positions 🟢 ---")
            for pos in spot_positions:
                current_price = await get_crypto_price(pos['coin_ticker'])
                if current_price:
                    pnl = ((current_price - pos['average_entry_price']) / pos['average_entry_price']) * 100
                    pnl_str = f"{pnl:+.2f}%"
                    price_str = f"${current_price:,.2f}"
                    emoji = "📈" if pnl >= 0 else "📉"
                else:
                    pnl_str = "N/A"
                    price_str = "Price Error"
                    emoji = "⚠️"

                pos_str = (
                    f"{emoji} Coin: ${pos['coin_ticker']} ({pos['remaining_percent']}% Remaining)\n"
                    f"   Entry: ${pos['average_entry_price']:,.2f} (Avg)\n"
                    f"   Current: {price_str}\n"
                    f"   PNL: {pnl_str}\n"
                    f"   Post: [Original Call]({pos['post_link']})"
                )
                response_parts.append(pos_str)
        elif 'spot' in command:
             response_parts.append("No open Spot positions found.")

    # Generate Futures Portfolio
    if 'futures' in command or 'all' in command:
        if futures_positions:
            response_parts.append("\n--- 🔵 Admin's Open Futures Positions 🔵 ---")
            for pos in futures_positions:
                current_price = await get_crypto_price(pos['coin_ticker'])
                if current_price:
                    pnl = ((current_price - pos['average_entry_price']) / pos['average_entry_price']) * 100
                    pnl_str = f"{pnl:+.2f}%"
                    price_str = f"${current_price:,.2f}"
                    emoji = "📈" if pnl >= 0 else "📉"
                else:
                    pnl_str = "N/A"
                    price_str = "Price Error"
                    emoji = "⚠️"
                
                # Note: Futures don't have remaining % in this schema, so it's always 100% until closed
                pos_str = (
                    f"{emoji} Coin: ${pos['coin_ticker']}\n"
                    f"   Entry: ${pos['average_entry_price']:,.2f}\n"
                    f"   Current: {price_str}\n"
                    f"   PNL: {pnl_str}\n"
                    f"   Post: [Original Call]({pos['post_link']})"
                )
                response_parts.append(pos_str)
        elif 'futures' in command:
             response_parts.append("No open Futures positions found.")

    if not response_parts:
        # This case handles when /portfolio is called but there's nothing to show
        await update.message.reply_text("No matching open positions found. 🤷‍♂️")
        return

    await update.message.reply_text("\n\n".join(response_parts), parse_mode='Markdown', disable_web_page_preview=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """A simple start command to greet the user."""
    await update.message.reply_text(
        "👋 Welcome to the Admin Trade Tracker!\n\n"
        "I help track the admin's crypto trades.\n"
        "To see the current portfolio, send me one of these commands:\n"
        "🔹 /portfolio_all - View all open positions\n"
        "🔹 /portfolio_spot - View only Spot positions\n"
        "🔹 /portfolio_futures - View only Futures positions"
    )

# --- MAIN BOT APPLICATION ---

def main() -> None:
    """Start the bot."""
    # Initialize the database on startup
    db.init_db()

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # --- Register Command Handlers ---
    # Admin commands
    application.add_handler(CommandHandler("new_spot", new_trade))
    application.add_handler(CommandHandler("new_future", new_trade))
    application.add_handler(CommandHandler("buy", buy))
    application.add_handler(CommandHandler("sell", sell))
    application.add_handler(CommandHandler("close", close))

    # User commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler(["portfolio", "portfolio_all"], portfolio))
    application.add_handler(CommandHandler("portfolio_spot", portfolio))
    application.add_handler(CommandHandler("portfolio_futures", portfolio))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()