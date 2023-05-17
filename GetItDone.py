# This example requires the 'message_content' intent.

import discord
import os
import sqlite3
# from discord import app_commmands
from discord.ext import commands
from dotenv import load_dotenv

# imports for getting Canvas assignments
# import requests
# from icalendar import Calendar
from datetime import datetime # might not need this
# from pytz import UTC # timezone - might not need this
import time
from typing import Tuple

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

@bot.tree.command(name="setup")
async def intro_setup(interaction: discord.Interaction):
    await interaction.response.defer()
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
    await template_category.create_text_channel(name="general")
    await template_category.create_text_channel(name="reminder")
    await template_category.create_text_channel(name="to-do")
    await template_category.create_text_channel(name="bot")
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
        name="/import [canvas link]",
        value = "📝 Import all assignments from a Canvas calendar feed link",
        inline=False
    )
    await interaction.followup.send(embed=embed)
    # await interaction.followup.send(
    #     "👋 Welcome to **Get It Done**!\n"
    #     "This bot organizes group work for teams to work more efficiently and effectively.\n"
    #     "Some commands you should know:\n\n"

    #     "**/new [@user] [task] [date]**\n"
    #     "🏷️ Assign a new **[task]** to a **[user]**, due by **[date]**\n\n"

    #     "**/remind [@user] [task]**\n"
    #     "🔔 Anonymously remind a **[user]** of their **[task]** that’s due soon\n"

    #     "**/import [canvas link] [class code]**\n"
    #     "📝 Import all assignments from a Canvas calendar feed link\n\n"

    #     "/help\n"
    #     "🔍 View all commands"
    # )

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
        value = "Bot DMs specified user of a task assigned to them and its deadline",
        inline=False
    )
    embed.add_field(
        name="/import [canvas link]",
        value = "To import assignment deadlines from canvas" +
                "Bot will send out reminders (3 days?) before the deadline",
        inline=False
    )
    embed.add_field(
        name="/assignments",
        value = "To view all (imported) assignments that haven’t passed yet",
        inline=False
    )
    embed.add_field(
        name="/tasks ([@user])",
        value = "[@user] - view the incomplete tasks of a specific user\n" +
                "Otherwise all incomplete tasks will be shown",
        inline=False
    )
    embed.add_field(
        name="/help",
        value = "To view all commands",
        inline=False
    )
    await interaction.response.send_message(embed=embed)



# # ----- Importing Canvas Assignments -----

# headers = ['BEGIN', 'UID', 'DTEND', 'SUMMARY', 'URL', 'END']


# # maybe if we have time we can allow assignments to be edited - like changing title or due date
# class Assignment:
#     '''
#     each assignment has a unique ID, title, url, and deadline
#     '''
#     def __init__(self, uid, title, url, due_date):
#         self.uid = uid
#         self.title = title
#         self.url = url
#         self.due_date = due_date

#     def set_title(self, title):
#         self.title = title

#     def get_title(self):
#         return self.title

#     def set_url(self, url):
#         self.url = url

#     def get_url(self):
#         return self.url

#     def set_due_date(self, due_date):
#         self.due_date = due_date

#     def get_due_date(self):
#         return self.due_date

#     def __repr__(self):
#         return "ASSIGNMENT:", self.get_title, "URL:", self.get_url, "DEADLINE:", self.due_date


# # global variables, since they will be referred to in any context
# assignments = []
# class_code = ''


# def get_class_code(*args: Tuple):
#     '''
#     get class code, with no spaces
#     '''
#     class_code = ''
#     for arg in args[1:]:
#         class_code += arg.lower()


# def import_assignments(*args: Tuple):
#     '''
#     method to parse Canvas link request to add all assignments to a global list
#     assumes args = [link], [class code, which might have spaces]
#     '''

#     # canvas_link = requests.get('https://canvas.uw.edu/feeds/calendars/user_qkZr6adOTXT0f39gFbhD5WxQXVyLliTHGaHkcE4d.ics').text
#     canvas_link = requests.get(args[0]).text

#     # class_code = 'CSE481P'
#     # get class code from user's request, with no spaces
#     class_code = get_class_code(args)

#     # Fields we are saving for each assignment
#     title = '' # assignment title in summary
#     due_date = '' # deadline in python dt format
#     uid = '' # assignment ID in uid
#     url = '' # assignment Canvas url

#     # loop through the calendar request and create assignment items for each event-assignment
#     # add them to global list of assignments
#     gcal = Calendar.from_ical(canvas_link)
#     for component in gcal.walk():
#         if component.name == "VEVENT":
#             uid = component.get('uid')

#             # only get assignments
#             if 'assignment' in uid:
#                 title = component.get('summary')

#                 # detect class code in title
#                 title_and_classcode = title.replace(' ', '').lower()

#                 # detect if class code of assignment matches the class of the user's request
#                 if class_code in title_and_classcode:
#                     # get title
#                     title_arr = title.split(' [')
#                     title = title_arr[0]

#                     # get due date
#                     due_date = component.get('dtend').dt

#                     # get url
#                     url = component.get('url')

#                     # make id to just be a number
#                     uid_split = component.get('uid').split('-')
#                     uid = uid_split[-1]

#                     # create a new assignment and add it to the list of assignments
#                     assignments.append(Assignment(uid, title, url, due_date))
#                     # print(title)
#                     # print(due_date)
#                     # print(url)
#                     # print(uid)
#                     # print('\n')

#     # cse481p should have 21 assignments
#     # print(len(assignments))
#     return assignments


# def format_time(due_date):
#     '''
#     Format assignment due date in the required format for Discord embedded messages
#     '''
#     # in canvas: 20230606T183000Z
#     # need: 2023-06-06T18:00:00.000Z
#     indices = [0,4,6,11,13]
#     date_str = ''
#     prev_index_value = 0
#     for num in indices:
#         date_str += due_date[prev_index_value:num]
#         if num == 4 or num == 6:
#             date_str += '-'
#         elif num == 11 or 13:
#             date_str += ':'
#         prev_index_value = num
#     date_str += '00.000Z'
#     return date_str


# @bot.tree.command(name='import')
# async def import_assignments_request(interaction: discord.Interaction, *args: Tuple):
#     '''
#     Bot request to import assignments from Canvas
#     args should contain Canvas URL and class code
#     EX: /import https://canvas.uw.edu/... cse481p
#     '''
#     assignments = import_assignments(*args)
#     class_code = get_class_code(*args)
#     await print_import_assignments_request_response(interaction, assignments, class_code)


# async def print_import_assignments_request_response(interaction: discord.Interaction,
#                                                     assignments_list, class_code):
#     '''
#     Bot response to print success message after importing assignments
#     '''
#     embed=discord.Embed(
#         title=f'Success! Imported {len(assignments_list)} assignments from {class_code}',
#         description='Use /assignments to view all assignments.',
#         color=0x1DB954)
#     await interaction.channel.send(embed=embed)


# @bot.tree.command(name='assignments')
# async def get_assignments_request(interaction: discord.Interaction):
#     '''
#     Bot request to get a list of all assignments
#     /assignments
#     '''
#     assignments = import_assignments()
#     if len(assignments) > 0:
#         await print_get_assignments_request_response(interaction, assignments)
#     await interaction.channel.send('No assignments')


# async def print_get_assignments_request_response(interaction: discord.Interaction, assignments: list):
#     '''
#     Bot response that loops through assignment list and sends individual messages with embedded assignments
#     If we have time it would be cool to change the color associated with each assignment as it's finished?
#     '''
#     for assgn in assignments:
#         embed = discord.Embed(
#             type='rich',
#             title=f'{assgn.get_title()}',
#             description='Use /assignments to view all assignments.',
#             color=0xFF5733,
#             timestamp=f'{format_time(assgn.get_due_date())}',
#             url={assgn.get_url()})
#         embed.set_footer(text=f'{assgn.get_uid()}')
#         await interaction.channel.respond(embed=embed)
#         time.sleep(2)


bot.run(TOKEN)