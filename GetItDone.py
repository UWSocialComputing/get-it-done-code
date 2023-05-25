# This example requires the 'message_content' intent.

import discord
import os
import sqlite3
from discord.ext import commands, tasks
from dotenv import load_dotenv

# imports for getting Canvas assignments
import requests
from icalendar import Calendar
import datetime
from pytz import UTC # timezone - might not need this
import time

# for reminders
from asyncio import sleep as s
from zoneinfo import ZoneInfo

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
con = sqlite3.connect("data.db")
cur = con.cursor()

intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)

# --- channels ID for organization ---
GENERAL_CH = discord.TextChannel
REMINDER_CH = discord.TextChannel
TODO_CH = discord.TextChannel
BOT = discord.TextChannel

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

@bot.event
async def on_guild_join(guild):
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
    # End update database

@bot.event
async def on_member_join(member):
    print(member.name)
    cur.execute(f"INSERT OR IGNORE INTO Users VALUES ({member.id})")
    cur.execute(f"INSERT OR IGNORE INTO UserGuild VALUES ({member.id},{member.guild.id})")
    con.commit()

@bot.tree.command(name="setup")
async def intro_setup(interaction: discord.Interaction):
    await interaction.response.defer()
    global GENERAL_CH
    global REMINDER_CH
    global TODO_CH
    global BOT

    guild = interaction.guild
    for category in guild.categories:
        if category.name == "test":
            channels = category.channels
            for channel in channels:
                try:
                    await channel.delete()
                except AttributeError:
                    pass
            await category.delete()
            break

    template_category = await guild.create_category(name="new-test")
    GENERAL_CH = await template_category.create_text_channel(name="general")
    REMINDER_CH = await template_category.create_text_channel(name="reminder")
    TODO_CH = await template_category.create_text_channel(name="to-do")
    BOT = await template_category.create_text_channel(name="bot")
    print(REMINDER_CH.id)
    embed = discord.Embed(
        title="👋 Welcome to Get It Done!",
        description="This bot organizes group work for teams to work more efficiently and effectively.\n"+
                    "Some commands you should know:",
        colour=discord.Colour.dark_green()
    )
    embed.add_field(
        name="/new [@user] [task] [date]",
        value = "🏷️ Assign a new [task] to a [user], due by [date]",
        inline=False
    )
    embed.add_field(
        name="/remind [@user] [task]",
        value = "🔔 Anonymously remind a [user] of their [task] that’s due soon",
        inline=False
    )
    embed.add_field(
        name="/import [canvas link] [class code]",
        value = "📝 Import all assignments from a Canvas calendar feed link",
        inline=False
    )
    embed.add_field(
        name="/help",
        value = "To view all commands in detail",
        inline=False
    )
    # await interaction.followup.send(embed=embed)

# A temp command to undo changes made by intro_setup()
@bot.tree.command(name="undo")
async def undo(interaction: discord.Interaction):
    await interaction.response.defer()
    guild = interaction.guild
    for category in guild.categories:
        if category.name == "new-test":
            channels = category.channels
            for channel in channels:
                try:
                    await channel.delete()
                except AttributeError:
                    pass
            await category.delete()
            break

    template_category = await guild.create_category(name="test")
    await template_category.create_text_channel(name="1")
    await template_category.create_text_channel(name="2")
    await interaction.followup.send("Sucessfully undid changes made by /setup")

@bot.tree.command(name="hello")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message("HI")

@bot.tree.command(name="help")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="How to use Get It Done",
        description="Here is a list of commands that you can use:",
        colour=discord.Colour.dark_green()
    )
    embed.add_field(
        name="/new [@user] [task] [date]",
        value = "[@user] - assign the task to\n" +
                "[task] - the task\n" +
                "[date] - the date to complete the task by, format: mm/dd/yy\n" +
                "Bot sends out a 24-hr reminder before deadline\n" +
                "React to the bot message to mark complete \n\n",
        inline=False
    )
    embed.add_field(
        name="/remind [@user] [task]",
        value = "Bot DMs user to remind them of their todo and deadline",
        inline=False
    )
    embed.add_field(
        name="/import [canvas link] [class code]",
        value = "To import assignment deadlines from Canvas \n" +
                "Bot will send out reminder 24 hours before the deadline \n" +
                "Ex: /import https://canvas.uw.edu/feeds/calendars/user_qkZr6adOTXT0f39gFbhD5WxQXVyLliTHGaHkcE4d.ics cse481p",
        inline=False
    )
    embed.add_field(
        name="/assignments",
        value = "To view all upcoming (imported) assignments",
        inline=False
    )
    embed.add_field(
        # name="/todos ([@user])",
        # value = "[@user] - view the incomplete to-dos of a specific user\n" +
        #         "Otherwise all incomplete to-dos will be shown",
        name="/todos",
        value = "View your incomplete to-dos",
        inline=False
    )
    await interaction.response.send_message(embed=embed)

# ----- To-Dos ------------

# commands.greedy if we eventually want to allow multiple users
@bot.tree.command(name="new", description="Creates and assigns a new to-do")
@discord.app_commands.describe(member="Who will complete to-do",
                               todo="Brief description of to-do",
                               date="Date in MM-DD format")
async def create_todo(interaction:discord.Interaction,
                      member: discord.Member,
                      todo: str, date: str):
    '''
    Bot response to creating and assigning new todo; updates database
    '''
    mocked_date = datetime.date.today() + datetime.timedelta(days=2)
    embed=discord.Embed(
      title=f'Created new to-do: {todo}',
      description=f'Assigned to {member.mention}, due by {mocked_date}\n' +
                  'React with ✅ if complete',
      color=0x1DB954)
    sql_date = mocked_date.strftime('%Y-%m-%d %H:%M:%S')
    print(sql_date)
    query = f"INSERT INTO Todos(Description, Deadline, UserID, GuildID) VALUES ('{todo}', {mocked_date}, {member.id}, {member.guild.id})"
    print(query)
    cur.execute(query)
    con.commit()
    await interaction.response.send_message(embed=embed)

    # wait for reaction to mark complete
    def check(reaction, user):
        return str(reaction.emoji) == '✅'

    await bot.wait_for("reaction_add", check=check)
    # set completed bit to 1 in db; eventually use taskid
    query = f"UPDATE Todos SET Completed = 1 WHERE UserID={member.id} AND Description='{todo}'"
    cur.execute(query)
    con.commit()
    await interaction.followup.send(f'Completed to-do "{todo}!"')

@bot.tree.command(name="clear", description="clear")
async def get_todos(interaction: discord.Interaction):
    '''
    Clears all user tasks (for testing)
    '''
    user_id = interaction.user.id
    query = f"DELETE FROM Todos WHERE UserID={user_id}"
    cur.execute(query)
    con.commit()
    await interaction.response.send_message('deleted')

# @bot.event
# async def on_reaction_add(reaction, user):
#     if reaction.message.author.bot and 'Created new to-do' in reaction.message.embeds[0].title:
#         if reaction.emoji == '✅':
#           # set completed bit to 1 in db
#           # query = f"UPDATE Todos(Description, Deadline, UserID, GuildID) SET Completed = 1 WHERE UserID=user_id AND TodoID=todo_id"
#           # cur.execute(query)
#           # con.commit()
#           await reaction.message.channel.send(f'Completed to-do! {reaction.message.embeds[0].description}')

# future: add (optional?) name param
@bot.tree.command(name="todos", description="Show your incomplete to-dos")
async def get_todos(interaction: discord.Interaction):
    '''
    Bot response to requesting all todos for a user
    '''
    user_id = interaction.user.id
    query = f"SELECT * FROM Todos WHERE completed=0 AND UserID={user_id} ORDER BY Deadline ASC"
    print(query)

    for row in cur.execute(query):
        print(row[1])
        print(row[2])

    embed=discord.Embed(
      title=f'Your To-Dos:',
      color=0xf1c40f)

    for row in cur.execute(query):
        embed.add_field(
          name=row[1],
          value='Due by ' + str(row[2]),
          inline=False
    )
    await interaction.response.send_message(embed=embed)

# ----- Importing Canvas Assignments -----

headers = ['BEGIN', 'UID', 'DTEND', 'SUMMARY', 'URL', 'END']


# maybe if we have time we can allow assignments to be edited - like changing title or due date
# we could also create a color field or boolean and change it once it's been completed, instead of going into the embed every time
class Assignment:
    '''
    each assignment has a unique ID, title, url, and deadline
    '''
    def __init__(self, uid, title, url, due_date):
        self.uid = uid
        self.title = title
        self.url = url
        self.due_date = due_date

    def get_uid(self):
        return self.uid

    def set_title(self, title):
        self.title = title

    def get_title(self):
        return self.title

    def set_url(self, url):
        self.url = url

    def get_url(self):
        return self.url

    def set_due_date(self, due_date):
        self.due_date = due_date

    def get_due_date(self):
        return self.due_date

    def __repr__(self):
        return "ASSIGNMENT:", self.get_title, "URL:", self.get_url, "DEADLINE:", self.due_date


# global variables, since they will be referred to in any context
assignments = [] # will have to store these in the database so we can refer back to them
class_code = ''


def get_link(all_args):
    '''
    parse user input arguments to get Canvas calendar link
    '''
    all_args = all_args.split(' ')
    return all_args[0]


def get_class_code(all_args):
    '''
    get desired class code from user input, with no spaces
    '''
    class_code = ''
    all_args = all_args.split(' ')

    for i in range(1, len(all_args)):
        class_code += all_args[i].lower()

    return class_code


def import_assignments(args):
    '''
    method to parse Canvas calendar link request to add all assignments to a global list
    assumes args = [link] [class code, which might have spaces]
    '''
    # sample link: https://canvas.uw.edu/feeds/calendars/user_qkZr6adOTXT0f39gFbhD5WxQXVyLliTHGaHkcE4d.ics
    canvas_calendar_link = requests.get(get_link(args)).text

    # sample class code: CSE481P
    class_code = get_class_code(args)

    # Fields we are saving for each assignment
    title = '' # assignment title in summary
    due_date = '' # deadline in python dt format
    uid = '' # assignment ID in uid
    url = '' # assignment Canvas url

    # loop through the calendar request and create assignment items for each event-assignment
    # & add them to global list of assignments
    gcal = Calendar.from_ical(canvas_calendar_link)
    for component in gcal.walk():
        if component.name == "VEVENT":
            uid = component.get('uid')

            # only get assignments
            if 'assignment' in uid:
                title = component.get('summary')

                # detect class code in assignment title
                title_and_classcode = title.replace(' ', '').lower()

                # detect if class code of assignment matches the class code of the user's request
                if class_code in title_and_classcode:
                    # get title w/o class code
                    title_arr = title.split(' [')
                    title = title_arr[0]

                    # get due date as a datetime object
                    due_date = component.get('dtend').dt

                    # start forming assignment page url
                    # this is just for UW canvas, but to make it universal we could parse the Canvas calendar URL to get only this part
                    url = 'https://canvas.uw.edu/courses/'

                    # get the course ID from the assignment's url
                    course_id = component.get('url').split('course')[1].split('&')[0].replace('_', '')
                    url += course_id
                    url += '/assignments/'

                    # make id to just be a number
                    uid = uid.split('-')[-1]

                    # add assignment id to complete canvas assignment url
                    url += uid

                    # create a new assignment and add it to the list of assignments
                    assignments.append(Assignment(uid, title, url, due_date))

    # cse481p should have 21 assignments
    return assignments


# fix this so we can create reminders
# maybe keep all assignments in the database and do some math on time to get all assignments in the coming week (+ 7 days) for the weekly upcoming overview and send reminders 24hrs in advance of a deadline
def format_time(due_date):
    '''
    Format assignment due date in the required format for Discord embedded messages
    * doesn't work rn
    '''
    # in canvas: 20230606T183000Z
    # need: 2023-06-06T18:00:00.000Z

    # date_time = now.strftime("%m/%d/%Y, %H:%M:%S")
    # print("date and time:",date_time)
    return datetime.datetime.strptime(str(due_date), '%Y-%m-%d %H:%M:%S%z')
    # return due_date.strftime('%Y-%m-%d T%H:%M:%S.000Z')

    # indices = [0,4,6,11,13]
    # date_str = ''
    # prev_index_value = 0
    # for num in indices:
    #     date_str += due_date[prev_index_value:num]
    #     if num == 4 or num == 6:
    #         date_str += '-'
    #     elif num == 11 or 13:
    #         date_str += ':'
    #     prev_index_value = num
    # date_str += '00.000Z'
    # return date_str


# maybe rename args so it's helpful for the user when using the command
@bot.tree.command(name="import")
async def import_assignments_request(interaction: discord.Interaction,
                                     args: str):
    '''
    Bot request to import assignments from Canvas calendar.
    args should contain Canvas calendar URL and class code.
    EX: /import https://canvas.uw.edu/... cse481p
    '''
    assignments = import_assignments(args)
    class_code = get_class_code(args)
    await print_import_assignments_request_response(interaction, assignments, class_code)


# right now the class code has no spaces and is .lower() like cse481p - maybe find a way to keep how the user entered the class code like CSE 481 P or CSE 481P
async def print_import_assignments_request_response(interaction: discord.Interaction,
                                                    assignments_list: list, class_code: str):
    '''
    Bot response to print success message after importing assignments
    '''
    embed=discord.Embed(
        title=f'Success! Imported {len(assignments_list)} assignments from {class_code}',
        description='Use /assignments to view all assignments.',
        color=0x1DB954)
    await interaction.channel.send(embed=embed)


@bot.tree.command(name="assignments")
async def get_assignments_request(interaction: discord.Interaction):
    '''
    Bot request to get a list of all assignments
    '''
    # assignments = import_assignments()
    # will have to refer back to the database for list of assignments
    if len(assignments) > 0:
        await print_get_assignments_request_response(interaction, assignments)
    else:
        await interaction.channel.send('No assignments')


# rn we are showing the assignment ID but it could also just be used internally. not sure if we should keep this so we can refer to assignments in future functions?
# want to show the relative time deadline in the timestamp of the embed, but there's an issue with the datetime object we're passing through - could just be how canvas datetime formatted differently than how datetime is expected as an argument
async def print_get_assignments_request_response(interaction: discord.Interaction,
                                                 assignments: list):
    '''
    Bot response that loops through assignment list and sends individual messages with embedded assignments
    If we have time it would be cool to change the color associated with each assignment as it's finished?
    '''

    embed = discord.Embed(
            type='rich',
            title="All Assignments",
            color=0xFF5733,
    )
    for assgn in assignments:
        embed.add_field(
            name=f'{assgn.get_title()}',
            value=f'Due Date: {format_time(assgn.get_due_date())} \n [Link]({assgn.get_url()})',
            inline=False
        )
    await interaction.channel.send(embed=embed)
    time.sleep(2)


# ------------------ reminders --------------------------
utc = datetime.timezone.utc
time = datetime.time(hour=0, minute=50, tzinfo=utc)  # 8h00 PST = 15h00 UTC

@bot.event
async  def on_ready():
    send_update.start()

@tasks.loop(time=time)
async def send_update():
    '''
    Send updates at 8AM PST
    '''
    if datetime.datetime.today().weekday() == 2:
        channel = bot.get_channel(REMINDER_CH.id)
        await bot.change_presence(activity=discord.Game('online'))
        await channel.send('weekly updates')

    channel = bot.get_channel(REMINDER_CH.id)
    await bot.change_presence(activity=discord.Game('online'))
    await channel.send('daily updates')


@bot.tree.command(name="remind")
@discord.app_commands.describe(user="Who to remind",
                               msg="msg to send")
async def remind(interaction: discord.Interaction, user: discord.Member, msg: str):
    embed=discord.Embed(
        title="Reminder!",
        description=f'{msg}',
        color=0x1DB954)

    await user.send(embed=embed)

bot.run(TOKEN)
