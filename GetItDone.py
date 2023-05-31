# This example requires the 'message_content' intent.

import discord
import os
import sqlite3
from discord.ext import commands, tasks
from dotenv import load_dotenv
import re

# for dates
from typing import Optional
import dateparser

# imports for Canvas assignments
import Assignments
import datetime
from pytz import UTC  # timezone - might not need this
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

# colors
INCOMPLETE = 0xF1C40F
SUCCESS = 0x1DB954

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
    channel = discord.utils.get(guild.channels, name='bot-commands')
    embed = discord.Embed(
        title="👋 Welcome to Get It Done!",
        description="This bot organizes group work for teams to work more efficiently and effectively.\n"+
                    "Here's a brief overview of the channels:",
        colour=discord.Colour.dark_green()
    )
    embed.add_field(
        name="#general",
        value="Channel for general group communications",
        inline=False
    )
    embed.add_field(
        name="#reminders",
        value="Channel used by the bot to send daily and weekly reminders of upcoming deadlines and progress",
        inline=False
    )
    embed.add_field(
        name="#to-do",
        value="Channel used by bot to keep track of completed and incompleted to-do's. This is where the new to-do's will be created.",
        inline=False
    )
    embed.add_field(
        name="#assignments",
        value="Channel used by bot to keep track of course completed and incompleted assignments.",
        inline=False
    )
    embed.add_field(
        name="#bot-commands",
        value="Channel for interacting with the bot.",
        inline=False
    )
    embed.add_field(
        name="/help",
        value="Command to view all commands in detail",
        inline=False
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

    # sends success message in bot channel
    embed_todo = discord.Embed(
        title=f"To-do: {todo}",
        description=f"{user.mention}\n Due {duedate_format}\n"
        + "React with ✅ if complete",
        color=INCOMPLETE,
    )
    sql_date = duedate.strftime("%Y-%m-%d %H:%M:%S")
    query = f"INSERT INTO Todos(Description, Deadline, UserID, GuildID) VALUES ('{todo}', '{sql_date}', {user.id}, {user.guild.id})"
    print(query)
    cur.execute(query)
    con.commit()

    # sends todo info in todo channel
    todo_channel = discord.utils.get(interaction.guild.channels, name="to-do")
    embed_bot = discord.Embed(
        title=f"Success!",
        description=f"New to-do listed in {todo_channel.mention}!\n",
        color=SUCCESS,
    )
    await interaction.response.send_message(embed=embed_bot)
    await todo_channel.send(embed=embed_todo)


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


@bot.tree.command(name="to-dos", description="Shows a user's incomplete to-dos")
@discord.app_commands.describe(user="Whose to-dos to view, defaults to you")
async def get_todos(interaction: discord.Interaction,
                    user: Optional[discord.Member]):
    '''
    Bot response to requesting all to-dos for a user
    ''' 
    if user is not None:
      user_id = user.id
    else:
      user_id = interaction.user.id
    query = f"SELECT * FROM Todos WHERE completed=0 AND UserID={user_id} ORDER BY Deadline ASC"\


    embed=discord.Embed(
      title=f'Your To-Dos:',
      description=f'{user.mention}',
      color=INCOMPLETE)

    i = 0
    for row in cur.execute(query):
        i += 1
        date = dateparser.parse(str(row[2]))
        embed.add_field(
            name=row[1], value="Due " + date.strftime("%m/%d %I:%M%p"), inline=False
        )
    if i == 0:
        embed.color=SUCCESS
        embed.description = f"No to-dos!"
    await interaction.response.send_message(embed=embed)


# ----- Assignments -----

# consider catching error if link is invalid
@bot.tree.command(name="import")
@discord.app_commands.describe(
    link="Canvas calendar link",
    class_code="Class code - ex. cse481p"
)
async def import_assignments_request(
    interaction: discord.Interaction,
    link: str, 
    class_code: str):
    """
    Import assignments from Canvas calendar
    """
    guild_id = interaction.guild.id
    num_assignments = Assignments.import_assignments(guild_id, link, class_code)

    if num_assignments == 0:
        await interaction.channel.send("No new assignments!")
    else: 
        await print_import_assignments_request_response(
            interaction, num_assignments, class_code
        )


async def print_import_assignments_request_response(
    interaction: discord.Interaction, 
    num_assignments: int,
    class_code: str
):
    """
    Bot response to print success message after importing assignments
    """
    assignments_channel = discord.utils.get(interaction.guild.channels, name='assignments')

    await post_assignments(assignments_channel)

    embed = discord.Embed(
        title=f'Success! Imported {num_assignments} assignments from {class_code}',
        description=f'{num_assignments} assignments are listed in {assignments_channel.mention}!',
        color=SUCCESS,
    )

    await interaction.channel.send(embed=embed)


# make sure to check for duplicates 
async def post_assignments(assignments_channel):
    """
    Post a list of all assignments in #assignments channel
    """
    query = "SELECT * FROM Assignments"

    for row in cur.execute(query):
        title = row[1]
        link = row[2]
        due_date = row[3]

        embed = discord.Embed(
            type='rich',
            title=f'{title}',
            color=INCOMPLETE
        )
        embed.add_field(
            name=f'{link}',
            value=f'Due {due_date}',
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
    todo_channel = discord.utils.get(guild.channels, name="to-do")
    channel = bot.get_channel(payload.channel_id)
    
    message = await channel.fetch_message(payload.message_id)
    embed = message.embeds[0]

    # make sure that this happens only when we use the check reaction in the assignments/to-do channel
    if payload.emoji.name == "✅" and (
        channel == assignments_channel or channel == todo_channel
    ):
        completed_embed = discord.Embed(
            type="rich", title=f"COMPLETED: {embed.title}", color=SUCCESS
        )

        if channel == todo_channel:
            completed_embed.description = embed.description
            todo = embed.title.split("To-do: ")[1]
            completed_embed.title = f"COMPLETED: {todo}"
        else:
            completed_embed.add_field(
                name=f"{embed.fields[0].name}",
                value=f"{embed.fields[0].value}",
                inline=False,
            )

        await message.edit(embed=completed_embed)

    if channel == todo_channel:
        embed.description = embed.description.split("\n")[0]
        user_id = re.findall("\d+", embed.description)[0]
        todo = embed.title.split("To-do: ")[1]
        query = f"UPDATE Todos SET Completed = 1 WHERE UserID={user_id} AND Description='{todo}'"
        cur.execute(query)
        con.commit()
    else:
        query = f"UPDATE Assignments SET Completed=1 WHERE GuildID={payload.guild_id} AND Url='{embed.fields[0].name}'"
        cur.execute(query)
        con.commit()
        await message.edit(embed=completed_embed)


@bot.event
async def on_raw_reaction_remove(payload):
    """
    Changes that happen when we remove emoji reactions 
    """
    guild = bot.get_guild(payload.guild_id)
    assignments_channel = discord.utils.get(guild.channels, name="assignments")
    todo_channel = discord.utils.get(guild.channels, name="to-do")
    channel = bot.get_channel(payload.channel_id)
    
    message = await channel.fetch_message(payload.message_id)
    embed = message.embeds[0]

    # make sure that this happens only when we remove the check reaction in the assignments/to-do channel
    if payload.emoji.name == "✅" and (
        channel == assignments_channel or channel == todo_channel
    ):
        title = embed.title.split("COMPLETED: ")[1]

        reversed_embed = discord.Embed(type="rich", title=f"{title}", color=INCOMPLETE)
        if channel == todo_channel:
            reversed_embed.description = embed.description
            reversed_embed.title = "To-do: " + reversed_embed.title
        else:
            reversed_embed.add_field(
                name=f"{embed.fields[0].name}",
                value=f"{embed.fields[0].value}",
                inline=False,
            )

        await message.edit(embed=reversed_embed)

    if channel == todo_channel:
        # remark to-do as incomplete
        embed.description = embed.description.split("\n")[0]
        user_id = re.findall("\d+", embed.description)[0]
        todo = embed.title.split("COMPLETED: ")[1]
        query = f"UPDATE Todos SET Completed = 0 WHERE UserID={user_id} AND Description='{todo}'"
        cur.execute(query)
        con.commit()
    else:
        query = f"UPDATE Assignments SET Completed=0 WHERE GuildID={payload.guild_id} AND Url='{embed.fields[0].name}'"
        cur.execute(query)
        con.commit()
        await message.edit(embed=reversed_embed)


# ------------------ reminders --------------------------
utc = datetime.timezone.utc
sched_time = datetime.time(hour=7, minute=0, tzinfo=utc)  # 7h00 UTC = 0h00 PDT

@tasks.loop(time=sched_time)
async def send_update():
    """
    Send updates at 12AM Pacific for both assignments and to-dos
    """
    time_now = datetime.datetime.now(datetime.timezone.utc)
    for guild in bot.guilds:
        # Send reminders for assignments
        channel = discord.utils.get(guild.channels, name="reminders")
        query_ass = f"SELECT * FROM Assignments WHERE GuildID={guild.id} AND Completed=0 ORDER BY Deadline ASC"
        # Check that assignments are <= 24 hours due
        for row in cur.execute(query_ass):
            due_date = dateparser.parse(str(row[3]))
            if due_date.month != time_now.month or due_date.day != time_now.day:
                break
            embed = discord.Embed(
                type='rich',
                title=f'{row[1]}',
                color=INCOMPLETE
            )
            embed.add_field(
                name=f'{row[2]}',
                value=f'Due {row[3]}',
                inline=False
            )
            await channel.send(("Hey @everyone, this assignment is due soon! Make sure to mark it as complete in #assignments once you're done."))
            await channel.send(embed=embed)
            
        # Send reminders for to-dos
        query_todo = f"SELECT * FROM Todos WHERE GuildID={guild.id} AND Completed=0 ORDER BY Deadline ASC"
        for row in cur.execute(query_todo):
            due_date = dateparser.parse(str(row[2]))
            date_format = due_date.strftime("%m/%d %I:%M%p")
            if due_date.month != time_now.month or due_date.day != time_now.day:
                break
            embed = discord.Embed(
                type='rich',
                title=f'{row[1]}',
                color=INCOMPLETE
            )
            embed.add_field(
                name="",
                value=f'Due {date_format}',
                inline=False
            )
            await channel.send(f"Hey <@{row[4]}>, you have a to-do due soon! Make sure to mark it as complete in #to-do once you're done.")
            await channel.send(embed=embed)


@bot.tree.command(name="remind")
@discord.app_commands.describe(user="Who to remind")
async def remind(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.send_message("Sent reminder!", ephemeral=True)
    embed = discord.Embed(title="Reminder!", description=f"You have an upcoming to-do: ", color=INCOMPLETE)

    # get user's upcoming to-do with nearest deadline
    query = f"SELECT * FROM Todos WHERE completed=0 AND UserID={user.id} ORDER BY Deadline ASC"

    i = 0
    for row in cur.execute(query):
        i += 1
        date = dateparser.parse(str(row[2]))
        embed.add_field(
            name=row[1], value="Due " + date.strftime("%m/%d %I:%M%p"), inline=False
        )
        break
    
    # if no upcoming to-dos
    if (i == 0):
        return
    else:
        await user.send(embed=embed)

    await user.send(embed=embed)

bot.run(TOKEN)
