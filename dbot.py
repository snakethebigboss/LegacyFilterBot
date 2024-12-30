# dbot.py

import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import sqlite3
from datetime import datetime, timedelta
from typing import Final    

load_dotenv()
TOKEN: Final[str]= os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('DISCORD_GUILD_ID')
GUEST_ROLE = "Guest"
REGULAR_ROLE = "Regular"
EXOPERATIVE_ROLE = "Ex-Operative"
ELITE_ROLE = "Elite"
OPERATIVE_ROLE = "Operative"
OFFICER_ROLE = "Officer"
FOUNDER_ROLE = "Founder"
# print(TOKEN)
# -----------------------------------------------------------
# client = discord.Client(intents=discord.Intents.default())

# # Startup
# @client.event
# async def on_ready():
#     print(f"{client.user} has connected to Discord!")

# # When a new member joins
# @client.event
# async def on_member_join(member):
#     await member.create_dm()
#     await member.dm_channel.send(
#         f"Hi {member.name}, Welcome to the server! Please read the rules. If you have any questions, feel free to ask any Operative+."
#     )

# client.run(TOKEN)
# -----------------------------------------------------------
# Bot setup
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.message_content = True
bot = commands.Bot(command_prefix="!" ,intents=intents)

# Database connection
conn = sqlite3.connect("members.db")
c = conn.cursor()

# Initialize database
def init_db():
    c.execute('''
        CREATE TABLE IF NOT EXISTS members (
            user_id INTEGER PRIMARY KEY,
            daykick INTEGER,
            endorse INTEGER
        )
    ''')
    conn.commit()

@bot.event
async def on_ready():
    print(f"{bot.user} is connected!")
    init_db()
    daily_check.start()  # Start the daily task

@bot.event
async def on_member_join(member):
    # if member.guild.id != GUILD_ID:
    #     return
    
    # Send a welcome message
    await member.create_dm()
    await member.dm_channel.send(
        f"Hi {member.name}, Welcome to the server! Please read the rules. If you have any questions, feel free to ask any Operative+."
    )

    # Assign "Guest" role
    guest_role = discord.utils.get(member.guild.roles, name=GUEST_ROLE)
    await member.add_roles(guest_role)

    # Add to database
    c.execute("INSERT OR IGNORE INTO members (user_id, daykick, endorse) VALUES (?, ?, ?)", 
              (member.id, 31, 0))
    conn.commit()
    print(f"Added {member.name} to the database.")

# Exception handler for nonexistent commands
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Command not found. Type !showcommands to see all available commands.")


# basic ping pong command
@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("pong")

# command to show all names on db
@bot.command(name="show")
async def show(ctx):
    if not ctx.channel.name == "endorsements":
        await ctx.send("This command cannot be used here.")
        return
    
    #Check if they are either an officer or founder
    # if discord.utils.get(ctx.author.roles, name=OFFICER_ROLE) or discord.utils.get(ctx.author.roles, name=FOUNDER_ROLE):
    #     pass
    # else:
    #     await ctx.send("You do not have permission to use this command.")
    #     return
    

    c.execute("SELECT * FROM members")
    records = c.fetchall()
    for record in records:
        user_id = record[0]
        daykick = record[1]
        endorse = record[2]
        user = await bot.fetch_user(user_id)
        await ctx.send(f"Username: {user.name}, DAYKICK: {daykick}, ENDORSE: {endorse}")

# command to show statistics of a user
@bot.command(name="stats")
async def stats(ctx, username: str):
    if not ctx.channel.name == "endorsements":
        await ctx.send("This command cannot be used here.")
        return
    
    #Check if they are either an officer or founder
    # if discord.utils.get(ctx.author.roles, name=OFFICER_ROLE) or discord.utils.get(ctx.author.roles, name=FOUNDER_ROLE):
    #     pass
    # else:
    #     await ctx.send("You do not have permission to use this command.")
    #     return
    
    target_member = discord.utils.get(ctx.guild.members, name=username)
    if not target_member:
        await ctx.send(f"User {username} not found.")
        return

    c.execute("SELECT endorse, daykick FROM members WHERE user_id = ?", (target_member.id,))
    record = c.fetchone()

    if not record:
        await ctx.send(f"User {username} is not being tracked.")
        return

    endorse, daykick = record
    await ctx.send(f"Stats for {username}: Endorsements = {endorse}, Days Till Removal={daykick}")



# Command to manually set daykick of a user
@bot.command(name="setdaykick")
async def setdaykick(ctx, username: str, daykick: int):
    if not ctx.channel.name == "endorsements":
        await ctx.send("This command cannot be used here.")
        return
    
    #Check if they are either an officer or founder
    if discord.utils.get(ctx.author.roles, name=OFFICER_ROLE) or discord.utils.get(ctx.author.roles, name=FOUNDER_ROLE):
        pass
    else:
        await ctx.send("You do not have permission to use this command.")
        return
    
    target_member = discord.utils.get(ctx.guild.members, name=username)
    if not target_member:
        await ctx.send(f"User {username} not found.")
        return

    c.execute("SELECT endorse FROM members WHERE user_id = ?", (target_member.id,))
    record = c.fetchone()

    if not record:
        await ctx.send(f"User {username} is not being tracked.")
        return

    c.execute("UPDATE members SET daykick = ? WHERE user_id = ?", (daykick, target_member.id))
    conn.commit()
    await ctx.send(f"Changed days left of {username} to {daykick}.")
    print(f"Changed DAYKICK of {username} to {daykick}.")


# Endorse command
@bot.command(name="endorse")
async def endorse(ctx, username: str):
    if not ctx.channel.name == "endorsements":
        await ctx.send("This command cannot be used here.")
        return

    target_member = discord.utils.get(ctx.guild.members, name=username)
    if not target_member:
        await ctx.send(f"User {username} not found.")
        return

    # Update database
    c.execute("SELECT endorse, daykick FROM members WHERE user_id = ?", (target_member.id,))
    record = c.fetchone()

    if not record:
        await ctx.send(f"User {username} is not being tracked.")
        return

    endorse, daykick = record
    endorse += 1
    daykick += 30
    c.execute("UPDATE members SET endorse = ?, daykick = ? WHERE user_id = ?", 
              (endorse, daykick, target_member.id))
    conn.commit()

    await ctx.send(f"Endorsed {username}. Current endorsements: {endorse}, days left to socialize: {daykick}")

    # Check if ENDORSE reaches 5
    if endorse >= 5:
        guest_role = discord.utils.get(ctx.guild.roles, name=GUEST_ROLE)
        regular_role = discord.utils.get(ctx.guild.roles, name=REGULAR_ROLE)

        await target_member.remove_roles(guest_role)
        await target_member.add_roles(regular_role)

        # Remove from database
        c.execute("DELETE FROM members WHERE user_id = ?", (target_member.id,))
        conn.commit()

        await ctx.send(f"{username} has been promoted to Regular!")

    # If Endorsement is 5 and they do not have guest role, remove them from the database
    if endorse >= 5:
        guest_role = discord.utils.get(ctx.guild.roles, name=GUEST_ROLE)
        if guest_role not in target_member.roles:
            c.execute("DELETE FROM members WHERE user_id = ?", (target_member.id,))
            conn.commit()
            print(f"Removed {username} from the database for already being accepted into community.")

# Command to manually add a user to the database
@bot.command(name="adduser")
async def adduser(ctx, username: str):
    if not ctx.channel.name == "endorsements":
        await ctx.send("This command cannot be used here.")
        return

    #Check if they are either an officer or founder
    if discord.utils.get(ctx.author.roles, name=OFFICER_ROLE) or discord.utils.get(ctx.author.roles, name=FOUNDER_ROLE):
        pass
    else:
        await ctx.send("You do not have permission to use this command.")
        return

    target_member = discord.utils.get(ctx.guild.members, name=username)
    if not target_member:
        await ctx.send(f"User {username} not found.")
        return

    c.execute("INSERT OR IGNORE INTO members (user_id, daykick, endorse) VALUES (?, ?, ?)", 
              (target_member.id, 31, 0))
    conn.commit()
    await ctx.send(f"Added {username} to the database.")
    print(f"Added {username} to the database.")

# Command to manually remove a user from the database
@bot.command(name="removeuser")
async def removeuser(ctx, username: str):
    if not ctx.channel.name == "endorsements":
        await ctx.send("This command cannot be used here.")
        return

    #Check if they are either an officer or founder
    if discord.utils.get(ctx.author.roles, name=OFFICER_ROLE) or discord.utils.get(ctx.author.roles, name=FOUNDER_ROLE):
        pass
    else:
        await ctx.send("You do not have permission to use this command.")
        return

    target_member = discord.utils.get(ctx.guild.members, name=username)
    if not target_member:
        await ctx.send(f"User {username} not found.")
        return

    c.execute("DELETE FROM members WHERE user_id = ?", (target_member.id,))
    conn.commit()
    await ctx.send(f"Removed {username} from the database.")
    print(f"Removed {username} from the database.")

# Command to show all commands
@bot.command(name="showcommands")
async def showcommands(ctx):
    await ctx.send(
        "Available commands:\n"
        "!ping: Respond with 'pong'\n"
        "!show: Show all members in the database\n"
        "!stats <username>: Show stats of a user\n"
        "!setdaykick <username> <daykick>: Set DAYKICK of a user\n"
        "!endorse <username>: Endorse a user\n"
        "!adduser <username>: Add a user to the database"
    )


@tasks.loop(hours=24)
async def daily_check():
    #GUILD_ID = os.getenv('DISCORD_GUILD_ID')
    #guild = bot.get_guild(GUILD_ID)
    guild = bot.get_guild(484885872236560385)
    channel = discord.utils.get(guild.channels, name="endorsements")
    now = datetime.now()

    c.execute("SELECT user_id, daykick FROM members")
    members = c.fetchall()


    for user_id, daykick in members:
        daykick -= 1

        # Tag Officers and Founders when a user has 5 days left
        if daykick == 5:
            member = guild.get_member(user_id)
            channel = discord.utils.get(guild.channels, name="endorsements")
            if member:
                guest_role = discord.utils.get(guild.roles, name=GUEST_ROLE)
                if guest_role in member.roles:
                    await channel.send(f"{member.name} has 5 days left to socialize. @Officers @Founders")

        if daykick <= 0:
            member = guild.get_member(user_id)
            channel = discord.utils.get(guild.channels, name="endorsements")
            if member:
                guest_role = discord.utils.get(guild.roles, name=GUEST_ROLE)
                if guest_role in member.roles:
                    await member.kick(reason="Failed to gain endorsements in time.")
                    print(f"Kicked {member.name} for not being social enough.")
                    #Tags Officers and Founders that the user was kicked
                    await channel.send(f"{member.name} was kicked for not being social enough. @Officers @Founders")
            c.execute("DELETE FROM members WHERE user_id = ?", (user_id,))
        else:
            c.execute("UPDATE members SET daykick = ? WHERE user_id = ?", (daykick, user_id))

        # Check if daykick = 0 and they do not have guest role, remove them from the database
        if daykick <= 0:
            member = guild.get_member(user_id)
            if member:
                guest_role = discord.utils.get(guild.roles, name=GUEST_ROLE)
                if guest_role not in member.roles:
                    c.execute("DELETE FROM members WHERE user_id = ?", (user_id,))
                    print(f"Removed {member.name} from the database for already being accepted into community.")

    #Check if the user is no longer in the server and remove them from the database
    c.execute("SELECT user_id FROM members")
    members = c.fetchall()
    for user_id in members:
        member = guild.get_member(user_id[0])
        if not member:
            c.execute("DELETE FROM members WHERE user_id = ?", (user_id[0],))
            print(f"Removed {user_id[0]} from the database for no longer being in the server.")

    conn.commit()
    print(f"Daily check completed at {now}.")
    await channel.send(f"Daily check completed at {now}.")

 
# Run the bot
bot.run(TOKEN)

