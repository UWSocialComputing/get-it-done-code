# This example requires the 'message_content' intent.

import discord
import os
import sqlite3
# from discord import app_commmands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
# con = sqlite3.conntect("database.db")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith('.'):
        await message.channel.send('Hello!')

@bot.tree.command(name="hello")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message("HI")

@bot.tree.command(name="help")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(
        "**COMMANDS**\n\n"

        "**/new [@user] [task] [date]**\n"
        "   **[@user]** - to assign the task to\n"
        "   **[task]** - the task\n"
        "   **[date]** - the date to complete the task by, format: mm/dd/yy\n"
        "   Bot sends out a 24-hr reminder before deadline\n"
        "   React to the bot message to mark complete \n\n"

        "**/remind [@user] [task]**\n"
        "   Bot DMs specified user of a task assigned to them and its deadline\n\n"

        "**/import [canvas link]**\n"
        "   To import assignment deadlines from canvas\n"
        "   Bot will send out reminders (3 days?) before the deadline\n\n"

        "**/assignments**\n"
        "   To view all (imported) assignments that haven’t passed yet\n\n"

        "**/tasks [@user]**\n"
        "   To view the incomplete tasks of a specific user\n\n"

        "**/help**\n" +
        "   Get all commands"
        )

bot.run(TOKEN)