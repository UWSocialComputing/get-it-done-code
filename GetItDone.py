# This example requires the 'message_content' intent.

import discord
import os
import sqlite3
from discord.ext import commands, tasks
from dotenv import load_dotenv

# for dates
from typing import Optional
import dateparser

# imports for Canvas assignments
import Assignments
import datetime
import time

# for reminders
from asyncio import sleep as s
from backports.zoneinfo import ZoneInfo

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
con = sqlite3.connect("data.db")
cur = con.cursor()
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
        send_update.start()
    except Exception as e:
        print(e)


@bot.event
async def on_guild_join(guild):
    """
    Upon joining a new guild (server), the bot will:
    1. Add the guild and its users to the database
    2. Setup the bot channels
    3. Send a welcome message
    """
    # Update database
    member_ids = [member.id for member in guild.members if not member.bot]
    query_u = "INSERT OR IGNORE INTO Users VALUES "
    query_ug = "INSERT OR IGNORE INTO UserGuild VALUES "
    for i, mid in enumerate(member_ids):
        print(mid)
        query_u += f"({mid})"
        query_ug += f"({mid},{guild.id})"
        if i < len(member_ids) - 1:
            query_u += ","
            query_ug += ","
    print(query_u)
    print(query_ug)
    cur.execute(f"INSERT OR IGNORE INTO Guilds VALUES ({guild.id})")
    cur.execute(query_u)
    cur.execute(query_ug)
    con.commit()

    # Create channels
    template_category = await guild.create_category(name="Get It Done")
    await template_category.create_text_channel(name="general")
    await template_category.create_text_channel(name="reminders")
    await template_category.create_text_channel(name="to-do")
    await template_category.create_text_channel(name="assignments")
    await template_category.create_text_channel(name="bot-commands")

    # Send welcome message
    channel = discord.utils.get(guild.channels, name="bot-commands")
    embed = discord.Embed(
        title="👋 Welcome to Get It Done!",
        description="This bot organizes group work for teams to work more efficiently and effectively.\n"
        + "Here's a brief overview of the channels:",
        colour=discord.Colour.dark_green(),
    )
    embed.add_field(
        name="#general", value="Channel for general group communications", inline=False
    )
    embed.add_field(
        name="#reminders",
        value="Channel used by the bot to send daily and weekly reminders of upcoming deadlines and progress",
        inline=False,
    )
    embed.add_field(
        name="#to-do",
        value="Channel used by bot to keep track of completed and incompleted to-do's. This is where the new to-do's will be created.",
        inline=False,
    )
    embed.add_field(
        name="#assignments",
        value="Channel used by bot to keep track of course completed and incompleted assignments.",
        inline=False,
    )
    embed.add_field(
        name="#bot-commands",
        value="Channel for interacting with the bot.",
        inline=False,
    )
    embed.add_field(
        name="/help", value="Command to view all commands in detail", inline=False
    )
    await channel.send(embed=embed)


@bot.event
async def on_member_join(member):
    """
    Adds new member to database
    """
    print(member.name)
    cur.execute(f"INSERT OR IGNORE INTO Users VALUES ({member.id})")
    cur.execute(
        f"INSERT OR IGNORE INTO UserGuild VALUES ({member.id},{member.guild.id})"
    )
    con.commit()


@bot.tree.command(name="help")
async def help(interaction: discord.Interaction):
    """
    Give user list and explanation of commands
    """
    embed = discord.Embed(
        title="How to Get It Done",
        description="Here is a list of commands you can use:",
        colour=discord.Colour.dark_green(),
    )
    embed.add_field(
        name="/new [@user] [to-do] [date] [time]",
        value="[@user] - Who will complete the to-do\n"
        + "[to-do] - Brief description of to-do\n"
        + "[date] - Due date in MM/DD format\n"
        + "[time] - Optional, defaults to 11:59 PM\n"
        + "Bot sends out a 24-hr reminder before due date\n"
        + "React to the bot message to mark complete \n",
        inline=False,
    )
    embed.add_field(
        name="/remind [@user] [to-do]",
        value="Bot DMs user to remind them of their to-do and due date",
        inline=False,
    )
    embed.add_field(
        name="/import [canvas link] [class code]",
        value="Imports assignment deadlines from a Canvas calendar link\n"
        + "Bot sends a 24-hr reminder before due date \n"
        + "React to the bot message to mark complete \n"
        + "Ex: /import https://canvas.uw.edu/feeds/calendars/user_qkZr6adOTXT0f39gFbhD5WxQXVyLliTHGaHkcE4d.ics cse481p",
        inline=False,
    )
    embed.add_field(
        name="/assignments",
        value="Shows all upcoming Canvas assignments",
        inline=False,
    )
    embed.add_field(
        name="/todos ([@user])",
        value="Shows a user's incompleted to-dos (if user unspecified, defaults to you)\n",
        inline=False,
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)


# ----- To-Dos ------------

# commands.greedy if we eventually want to allow multiple users
@bot.tree.command(name="new", description="Creates and assigns a new to-do")
@discord.app_commands.describe(
    user="Who will complete the to-do",
    todo="Brief description of to-do",
    date="Due date in MM/DD format",
    time="Optional, defaults to 11:59 PM",
)
async def create_todo(
    interaction: discord.Interaction,
    user: discord.Member,
    todo: str,
    date: str,
    time: Optional[str],
):
    """
    Bot response to /new, creating and assigning new to-do
    """
    # include space for parser
    if time is None:
        time = " 11:59 PM"
    else:
        time = " " + time
    duedate = dateparser.parse(date + time)
    duedate_format = duedate.strftime("%m/%d %I:%M%p")

    embed = discord.Embed(
        title=f"To-do: {todo}",
        description=f"Assigned to {user.mention}\n Due {duedate_format}\n"
        + "React with ✅ if complete",
        color=0x1DB954,
    )
    sql_date = duedate.strftime("%Y-%m-%d %H:%M:%S")
    query = f"INSERT INTO Todos(Description, Deadline, UserID, GuildID) VALUES ('{todo}', '{sql_date}', {user.id}, {user.guild.id})"
    print(query)
    cur.execute(query)
    con.commit()

    await interaction.response.send_message("Created new to-do!", ephemeral=True)

    # check guild's channels to get specific channel id
    guild = interaction.guild
    channel_id = -1
    for c in guild.channels:
        if c.name == "to-do":
            channel_id = c.id
    channel = bot.get_channel(channel_id)
    await channel.send(embed=embed)

    # wait for reaction to mark complete
    def check(reaction, user):
        return str(reaction.emoji) == "✅"

    await bot.wait_for("reaction_add", check=check)
    # set completed bit to 1 in db; eventually use taskid
    query = f"UPDATE Todos SET Completed = 1 WHERE UserID={user.id} AND Description='{todo}'"
    cur.execute(query)
    con.commit()
    await channel.send(f'Completed to-do "{todo}!"')


@bot.tree.command(name="clear", description="clear")
async def clear_todos(interaction: discord.Interaction):
    """
    Clears all user to-dos (for testing)
    """
    user_id = interaction.user.id
    query = f"DELETE FROM Todos WHERE UserID={user_id}"
    cur.execute(query)
    con.commit()
    await interaction.response.send_message("deleted")


@bot.tree.command(name="todos", description="Show your incomplete to-dos")
async def get_todos(interaction: discord.Interaction):
    """
    Bot response to requesting all todos for a user
    """
    user_id = interaction.user.id
    query = f"SELECT * FROM Todos WHERE completed=0 AND UserID={user_id} ORDER BY Deadline ASC"
    print(query)

    for row in cur.execute(query):
        print(row[1])
        print(row[2])

    embed = discord.Embed(title=f"Your To-Dos:", color=0xF1C40F)

    i = 0
    for row in cur.execute(query):
        i += 1
        date = dateparser.parse(str(row[2]))
        embed.add_field(
            name=row[1], value="Due " + date.strftime("%m/%d %I:%M%p"), inline=False
        )
    if i == 0:
        embed.description = f"No to-dos!"
    await interaction.response.send_message(embed=embed)


# ----- Assignments -----

# consider catching error if link is invalid
@bot.tree.command(name="import")
@discord.app_commands.describe(
    link="Canvas calendar link", class_code="Class code - ex. cse481p"
)
async def import_assignments_request(
    interaction: discord.Interaction, link: str, class_code: str
):
    """
    Import assignments from Canvas calendar
    """
    guild_id = interaction.guild
    num_assignments = Assignments.import_assignments(guild_id, link, class_code)

    if num_assignments == 0:
        await interaction.channel.send("No new assignments!")
    else:
        await print_import_assignments_request_response(
            interaction, num_assignments, class_code
        )


async def print_import_assignments_request_response(
    interaction: discord.Interaction, num_assignments: int, class_code: str
):
    """
    Bot response to print success message after importing assignments
    """
    assignments_channel = discord.utils.get(
        interaction.guild.channels, name="assignments"
    )

    await post_assignments(assignments_channel)

    embed = discord.Embed(
        title=f"Success! Imported {num_assignments} assignments from {class_code}",
        description=f"{num_assignments} assignments are listed in {assignments_channel.mention}!\n"
        + "React with ✅ to an assignment if complete",
        color=0x1DB954,
    )

    await interaction.channel.send(embed=embed)


async def post_assignments(assignments_channel):
    """
    Post a list of all assignments in #assignments channel
    """
    query = "SELECT * FROM Assignments"

    for row in cur.execute(query):
        title = row[1]
        link = row[2]
        due_date = row[3]

        embed = discord.Embed(type="rich", title=f"{title}", color=0xFF5733)
        embed.add_field(
            name=f"{link}",
            value=f"Due {due_date}",
            inline=False,
        )
        await assignments_channel.send(embed=embed, silent=True)


@bot.event
async def on_raw_reaction_add(payload):
    """
    Changes that happen when we add emoji reactions
    """
    guild = bot.get_guild(payload.guild_id)
    assignments_channel = discord.utils.get(guild.channels, name="assignments")
    channel = bot.get_channel(payload.channel_id)

    message = await channel.fetch_message(payload.message_id)
    embed = message.embeds[0]

    # make sure that this happens only when we use the check reaction in the assignments channel
    if payload.emoji.name == "✅" and channel == assignments_channel:
        completed_embed = discord.Embed(
            type="rich", title=f"COMPLETED: {embed.title}", color=0x1DB954
        )
        completed_embed.add_field(
            name=f"{embed.fields[0].name}",
            value=f"{embed.fields[0].value}",
            inline=False,
        )

        await message.edit(embed=completed_embed)


@bot.event
async def on_raw_reaction_remove(payload):
    """
    Changes that happen when we remove emoji reactions
    """
    guild = bot.get_guild(payload.guild_id)
    assignments_channel = discord.utils.get(guild.channels, name="assignments")
    channel = bot.get_channel(payload.channel_id)

    message = await channel.fetch_message(payload.message_id)
    embed = message.embeds[0]

    # make sure that this happens only when we remove the check reaction in the assignments channel
    if payload.emoji.name == "✅" and channel == assignments_channel:
        title = embed.title.split("COMPLETED: ")[1]

        reversed_embed = discord.Embed(type="rich", title=f"{title}", color=0xFF5733)
        reversed_embed.add_field(
            name=f"{embed.fields[0].name}",
            value=f"{embed.fields[0].value}",
            inline=False,
        )

        await message.edit(embed=reversed_embed)


# ------------------ reminders --------------------------
utc = datetime.timezone.utc
time = datetime.time(hour=8, minute=0, tzinfo=utc)  # 8h00 PST = 15h00 UTC


# @bot.event
# async def on_ready():
#  send_update.start()


@tasks.loop(time=time)
async def send_update():
    """
    Send updates at 8AM PST
    """

    # TODO: Search database for assignments and send reminders to their respective servers
    if datetime.datetime.today().weekday() == 2:
        # channel = bot.get_channel(REMINDER_CH.id)
        # await bot.change_presence(activity=discord.Game("online"))
        # await channel.send("weekly updates")
        print("hi")

    # channel = bot.get_channel(REMINDER_CH.id)
    # await bot.change_presence(activity=discord.Game("online"))
    # await channel.send("daily updates")


@bot.tree.command(name="remind")
@discord.app_commands.describe(user="Who to remind", msg="msg to send")
async def remind(interaction: discord.Interaction, user: discord.Member, msg: str):
    embed = discord.Embed(title="Reminder!", description=f"{msg}", color=0x1DB954)

    await user.send(embed=embed)


bot.run(TOKEN)
