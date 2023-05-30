import discord
import sqlite3
import requests
from icalendar import Calendar
from datetime import datetime, timezone

con = sqlite3.connect("data.db")
cur = con.cursor()

# ----- Importing Canvas Assignments -----

headers = ["BEGIN", "UID", "DTEND", "SUMMARY", "URL", "END"]


# maybe if we have time we can allow assignments to be edited - like changing title or due date
# we could also create a color field or boolean and change it once it's been completed, instead of going into the embed every time

def import_assignments(
        guild_id, 
        link: str, 
        class_code: str):
    """
    Method to parse Canvas calendar link request to add all assignments to database
    """
    # sample link: https://canvas.uw.edu/feeds/calendars/user_qkZr6adOTXT0f39gFbhD5WxQXVyLliTHGaHkcE4d.ics
    canvas_calendar_link = requests.get(link).text

    # Fields to save for each assignment
    title = "" # assignment title in SUMMARY
    due_date = "" # deadline in python dt format
    uid = "" # assignment ID in UID
    url = "" # assignment Canvas url
    num_assignments = 0

    # loop through the calendar request and create assignment items for each event-assignment
    # & add them to database
    gcal = Calendar.from_ical(canvas_calendar_link)
    for component in gcal.walk():
        if component.name == "VEVENT":
            uid = component.get("uid")

            # only get assignments
            if "assignment" in uid:
                title = component.get("summary")

                # detect class code in assignment title
                title_and_classcode = title.replace(" ", "").lower()

                # detect if class code of assignment matches the class code of the user's request
                if class_code in title_and_classcode:
                    # get title w/o class code
                    title_arr = title.split(" [")
                    title = title_arr[0]

                    # get due date as a datetime object and convert to local timezone, then format
                    due_date = component.get("dtend").dt.replace(tzinfo=timezone.utc).astimezone(tz=None)
                    due_date = due_date.strftime("%m/%d %I:%M%p")

                    # start forming assignment page url
                    # this is just for UW canvas, but to make it universal we could parse the Canvas calendar URL to get only this part
                    url = "https://canvas.uw.edu/courses/"

                    # get the course ID from the assignment's url
                    course_id = (
                        component.get("url")
                        .split("course")[1]
                        .split("&")[0]
                        .replace("_", "")
                    )
                    url += course_id
                    url += "/assignments/"

                    # make id to just be a number
                    uid = uid.split("-")[-1]

                    # add assignment id to complete canvas assignment url
                    url += uid

                    # detect duplicate assignments
                    detect_duplicates_query = (
                        f"SELECT * FROM Assignments WHERE Url LIKE '%{uid}%'"
                    )
                    cur.execute(detect_duplicates_query)
                    row = cur.fetchone()
                    if row == None:
                        # increment num of assignments
                        num_assignments += 1

                        # create insert query
                        query = f"INSERT INTO Assignments(Name, Url, Deadline, GuildId) VALUES('{title}', '{url}', '{due_date}', '{guild_id}')"
                        cur.execute(query)
                        con.commit()
    return num_assignments
