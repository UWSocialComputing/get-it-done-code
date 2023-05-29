import discord
import sqlite3
import requests
from icalendar import Calendar
import datetime
from pytz import UTC  # timezone - might not need this
import time

con = sqlite3.connect("data.db")
cur = con.cursor()

# ----- Importing Canvas Assignments -----

headers = ['BEGIN', 'UID', 'DTEND', 'SUMMARY', 'URL', 'END']


# maybe if we have time we can allow assignments to be edited - like changing title or due date
# we could also create a color field or boolean and change it once it's been completed, instead of going into the embed every time

def import_assignments(
        guild_id, 
        link: str, 
        class_code: str):
    '''
    Method to parse Canvas calendar link request to add all assignments to database
    '''
    # sample link: https://canvas.uw.edu/feeds/calendars/user_qkZr6adOTXT0f39gFbhD5WxQXVyLliTHGaHkcE4d.ics
    canvas_calendar_link = requests.get(link).text

    # Fields to save for each assignment
    title = '' # assignment title in SUMMARY
    due_date = '' # deadline in python dt format
    uid = '' # assignment ID in UID
    url = '' # assignment Canvas url
    num_assignments = 0

    # loop through the calendar request and create assignment items for each event-assignment
    # & add them to database
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

                    # increment num of assignments
                    num_assignments += 1

                    # create query - consider duplicate assignments 
                    query = f"INSERT INTO Assignments(Name, Url, Deadline, GuildId) VALUES('{title}', '{url}', '{due_date}', '{guild_id}')"
                    cur.execute(query)
                    con.commit()

    return num_assignments


# # fix this so we can create reminders
# # maybe keep all assignments in the database and do some math on time to get all assignments in the coming week (+ 7 days) for the weekly upcoming overview and send reminders 24hrs in advance of a deadline
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
