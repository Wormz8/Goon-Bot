import discord
from discord.ext import commands, tasks
import sqlite3
import datetime
import os
import pytz

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

conn = sqlite3.connect("activity.db")
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    last_active TEXT
)''')
conn.commit()

GOONING_THRESHOLD_SECONDS = 86400
EST = pytz.timezone("America/New_York")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    schedule_gooning_announcement.start()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = message.author.id
    timestamp = datetime.datetime.now(datetime.UTC)

    cursor.execute("INSERT INTO users (user_id, last_active) VALUES (?, ?) "
                   "ON CONFLICT(user_id) DO UPDATE SET last_active = ?",
                   (user_id, timestamp.isoformat(), timestamp.isoformat()))
    conn.commit()

    await bot.process_commands(message)

@tasks.loop(minutes=1)
async def schedule_gooning_announcement():
    now_utc = datetime.datetime.now(datetime.UTC)
    now_est = now_utc.astimezone(EST)

    if now_est.hour == 12 and now_est.minute == 0:
        await announce_gooning_users()

async def announce_gooning_users():
    now = datetime.datetime.now(datetime.UTC)
    
    cursor.execute("SELECT user_id, last_active FROM users")
    users = cursor.fetchall()

    guild = bot.guilds[0]
    general_channel = discord.utils.get(guild.text_channels, name="general")

    if general_channel:
        gooning_users = []
        for user in users:
            user_id, last_active = user
            last_active_time = datetime.datetime.fromisoformat(last_active).replace(tzinfo=datetime.UTC)
            gooning_duration = now - last_active_time

            if gooning_duration.total_seconds() >= GOONING_THRESHOLD_SECONDS:
                gooning_users.append((user_id, format_time(gooning_duration)))

        if gooning_users:
            message = "**📢 Daily Gooning Report:**\n"
            for user_id, time_str in gooning_users:
                member = guild.get_member(user_id)
                if member:
                    message += f"🟡 {member.display_name} - Gooning for {time_str}\n"
                else:
                    message += f"🔴 (Unknown User) - Gooning for {time_str}\n"

            await general_channel.send(message)
        else:
            await general_channel.send("✅ No users are currently Gooning!")

def format_time(duration):
    total_seconds = int(duration.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    time_parts = []
    if days > 0:
        time_parts.append(f"{days} days")
    if hours > 0:
        time_parts.append(f"{hours} hours")
    if minutes > 0:
        time_parts.append(f"{minutes} minutes")
    if seconds > 0:
        time_parts.append(f"{seconds} seconds")

    return ", ".join(time_parts)

@bot.command()
async def gooning(ctx):
    now = datetime.datetime.now(datetime.UTC)
    
    cursor.execute("SELECT user_id, last_active FROM users")
    users = cursor.fetchall()

    gooning_users = []

    for user in users:
        user_id, last_active = user
        last_active_time = datetime.datetime.fromisoformat(last_active).replace(tzinfo=datetime.UTC)
        gooning_duration = now - last_active_time

        if gooning_duration.total_seconds() >= GOONING_THRESHOLD_SECONDS:
            gooning_users.append((user_id, format_time(gooning_duration)))

    if not gooning_users:
        await ctx.send("No users are currently Gooning!")
        return

    message = "**📢 Gooning Report:**\n"
    for user_id, time_str in gooning_users:
        member = ctx.guild.get_member(user_id)

        if member:
            message += f"🟡 {member.display_name} - Gooning for {time_str}\n"
        else:
            message += f"🔴 (Unknown User) - Gooning for {time_str}\n"

    await ctx.send(message)

bot.run("BOT_TOKEN")
