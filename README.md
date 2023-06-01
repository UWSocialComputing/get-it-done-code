# Get It Done

![image](https://github.com/UWSocialComputing/get-it-done-code/assets/68497574/002ae829-9810-4c09-8c18-ad2a9dc82efa)

## How to Run:
To run, install:

`pip install -r requirements.txt`

Plus some other packages possibly. If you run the file and there is an error, the terminal will tell you what package is still missing.

You'll want to have a file called `.env` that contains the field `DISCORD_TOKEN=token`.
You can get a Discord bot token by creating a bot through the Discord Developer Portal (https://discord.com/developers/docs/intro).
For privacy reasons our specific `.env` for the official Get It Done bot is not included in this repository.
Or, you can contact one of us directly for possible access to our specific Get It Done token (really only applies to CSE 481P instructors).

Since our code assumes the `.db` (database) file is named `data.db`, you can rename `data_empty.db` to `data.db`. `data_empty.db` comes with all of the
database tables premade and empty.

Finally, run:

`python GetItDone.py`

To invite our Get It Done to your server, use this link! It may not be running, as we currently need to run it locally on one of our machines, but feel free to ask us to host it.

https://discord.com/api/oauth2/authorize?client_id=1106299423883005982&permissions=8&scope=applications.commands%20bot

Enjoy! We hope you can get it done with Get It Done 🐸
