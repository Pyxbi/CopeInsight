from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# CHECKPOINT 1
print("Script started...")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message when the /start command is issued."""
    # CHECKPOINT 4
    print("'/start' command received!")
    await update.message.reply_text('Hello! I am your Crypto Trade Tracker Bot. Ready for action!')

def main():
    """Start the bot."""
    # CHECKPOINT 2
    print("Main function started...")
    application = Application.builder().token("8232151989:AAGpddeDvGdY_PyxVQToGDexJ-oYCriDBoI").build()

    application.add_handler(CommandHandler("start", start))

    # CHECKPOINT 3
    print("Bot is starting to poll for updates... (This is where it connects)")
    # This is the line that connects to Telegram. It will run forever.
    application.run_polling()

if __name__ == '__main__':
    main()