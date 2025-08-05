# Admin Trade Tracker Telegram Bot 📈

A powerful yet simple Telegram bot designed to help channel admins log their cryptocurrency trades and allow community members to easily track their performance. It keeps the main channel clean by providing portfolio details via private message.

This bot solves the common problem of trade calls getting lost in a busy chat. Members can instantly check an admin's open positions, entry prices, and live Profit & Loss (PNL) without asking.

# ✨ Core Features
- Spot & Futures Separation: Tracks Spot and Futures trades independently

- Position Management: Supports Dollar-Cost Averaging (DCA) with /buy and taking partial profits with /sell.

- Real-time PNL: Automatically calculates and displays the live Profit & Loss for all open positions using the CoinGecko API.

- Private Portfolio View: Users query the bot in a direct message to see the portfolio, preventing spam in the main channel.

- Admin-Only Controls: Only the designated channel admin can execute trade management commands

- Persistent Storage: Uses an SQLite database to remember all trades, so no data is lost if the bot restarts.

# 🚀 Getting Started
Follow these steps to get your own instance of the trade tracker bot up and running.

1. Prerequisites
Python 3.8 or higher.

A Telegram account.

2. Installation & Setup
Download the Code:
Download the project files (bot.py, database.py, requirements.txt) into a new folder on your machine.

## Install Dependencies:

pip install -r requirements.txt
Create Your Bot on Telegram:

Open Telegram and talk to the @BotFather.

Use the /newbot command to create a bot.

BotFather will give you a unique Bot Token. Copy it.

Get Your Admin User ID:

Talk to a bot like @userinfobot.

It will provide you with your numeric Telegram User ID. Copy it.

Configure the Bot:

Open the bot.py file.

Find the configuration section and replace the placeholder values with your own Bot Token and Admin ID.

Python

## --- CONFIGURATION ---
BOT_TOKEN = "YOUR_BOT_TOKEN" 
ADMIN_ID = YOUR_ADMIN_ID # Should be a number, not a string
4. Run the Bot
Once configured, run the bot from your terminal:

Bash

python bot.py
Your bot is now live! Add it to your channel as an administrator.

# 🤖 How to Use
Interaction is split between the admin (in the public channel) and users (in private messages).

Admin Commands (Channel Only)
These commands can only be executed by the configured ADMIN_ID in a group or channel.

## Command	Description	Example
/new_spot [t] [p] [s]	Opens a new spot trade.	/new_spot BTC 68000 0.1
/new_future [t] [p] [s]	Opens a new futures trade.	/new_future ETH 3500 1.5
/buy [type] [t] [a] [p]	Adds to a position (DCA).	/buy spot BTC 0.05 65000
/sell [type] [t] [%] [p]	Sells a percentage of the position.	/sell spot BTC 50 72000
/close [type] [t] [p]	Closes the entire remaining position.	/close spot BTC 71000


### Arguments:

[t]: Ticker (e.g., BTC)

[p]: Price (e.g., 68000.50)

[s]: Size/Amount (e.g., 0.1)

[a]: Amount to add

[%]: Percentage to sell (1-100)

[type]: spot or future
