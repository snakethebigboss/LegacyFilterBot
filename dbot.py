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

# Bot setup
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.message_content = True
bot = commands.Bot(command_prefix="/" ,intents=intents)
tree = bot.tree

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
    c.execute('''
        CREATE TABLE IF NOT EXISTS endorsements (
            endorser_id INTEGER,
            endorsed_id INTEGER,
            timestamp DATETIME,
            PRIMARY KEY (endorser_id, endorsed_id)
        )
    ''')
    conn.commit()

@bot.event
async def on_ready():
    print(f"{bot.user} is connected!")
    init_db()
    daily_check.start()  # Start the daily task
    await tree.sync()
    # test 

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


# basic ping pong command
@tree.command(name="ping", description="Respond with 'pong'")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong")

# Random number generator
@tree.command(name="random", description="Generate a random number")
async def random(interaction: discord.Interaction, min: int, max: int):
    import random
    await interaction.response.send_message(random.randint(min, max))

# command to show all names on db
@tree.command(name="show", description="Show all members in the database") 
async def show(interaction: discord.Interaction):
    if not interaction.channel.name == "endorsements":
        await interaction.response.send_message("This command cannot be used here.")
        return
    
    # If the database is empty
    c.execute("SELECT * FROM members")
    if not c.fetchall():
        await interaction.response.send_message("No members are being tracked.")
        return
    
    c.execute("SELECT * FROM members")
    records = c.fetchall()
    message = ""
    for record in records:
        user_id = record[0]
        daykick = record[1]
        endorse = record[2]
        user = await bot.fetch_user(user_id)
        message += f"Username: {user.name}, Days: {daykick}, Endorsements: {endorse}\n"

    await interaction.response.send_message(message)


# command to show statistics of a user
@tree.command(name="stats", description="Show stats of a user")
async def stats(interaction: discord.Interaction, username: str):
    if not interaction.channel.name == "endorsements":
        await interaction.response.send_message("This command cannot be used here.")
        return
    
    target_member = discord.utils.get(interaction.guild.members, name=username)
    if not target_member:
        await interaction.response.send_message(f"User {username} not found.")
        return

    c.execute("SELECT endorse, daykick FROM members WHERE user_id = ?", (target_member.id,))
    record = c.fetchone()

    if not record:
        await interaction.response.send_message(f"User {username} is not being tracked.")
        return

    endorse, daykick = record

    # Fetch endorsers
    c.execute("SELECT endorser_id FROM endorsements WHERE endorsed_id = ?", (target_member.id,))
    endorsers = c.fetchall()
    endorser_names = []
    for endorser in endorsers:
        endorser_user = await bot.fetch_user(endorser[0])
        endorser_names.append(endorser_user.name)

    endorser_list = ", ".join(endorser_names) if endorser_names else "No endorsements yet"

    await interaction.response.send_message(
        f"Stats for {username}:\n"
        f"Endorsements: {endorse}\n"
        f"Days left to socialize: {daykick}\n"
        f"Endorsed by: {endorser_list}"
    )



# Command to manually set daykick of a user
@tree.command(name="setdaykick", description="Set DAYKICK of a user")
async def setdaykick(interaction: discord.Interaction, username: str, daykick: int):
    if not interaction.channel.name == "endorsements":
        await interaction.response.send_message("This command cannot be used here.")
        return
    
    #Check if they are either an officer or founder
    if discord.utils.get(interaction.user.roles, name=OFFICER_ROLE) or discord.utils.get(interaction.user.roles, name=FOUNDER_ROLE):
        pass
    else:
        await interaction.response.send_message("You do not have permission to use this command.")
        return
    
    target_member = discord.utils.get(interaction.guild.members, name=username)
    if not target_member:
        await interaction.response.send_message(f"User {username} not found.")
        return

    c.execute("SELECT endorse FROM members WHERE user_id = ?", (target_member.id,))
    record = c.fetchone()

    if not record:
        await interaction.response.send_message(f"User {username} is not being tracked.")
        return

    c.execute("UPDATE members SET daykick = ? WHERE user_id = ?", (daykick, target_member.id))
    conn.commit()
    await interaction.response.send_message(f"Changed days left of {username} to {daykick}.")
    print(f"Changed DAYKICK of {username} to {daykick}.")



# Endorse command
@tree.command(name="endorse", description="Endorse a user")
async def endorse(interaction: discord.Interaction, username: str):
    if not interaction.channel.name == "endorsements":
        await interaction.response.send_message("This command cannot be used here.")
        return

    target_member = discord.utils.get(interaction.guild.members, name=username)
    if not target_member:
        await interaction.response.send_message(f"User {username} not found.")
        return
    
    # Check cooldown period
    c.execute("SELECT timestamp FROM endorsements WHERE endorsed_id = ? ORDER BY timestamp DESC LIMIT 1", (target_member.id,))
    last_endorsement = c.fetchone()
    if last_endorsement:
        last_endorsement_time = datetime.strptime(last_endorsement[0], '%Y-%m-%d %H:%M:%S')
        if datetime.now() < last_endorsement_time + timedelta(days=5):
            await interaction.response.send_message(f"User {username} is on cooldown and cannot receive endorsements yet.")
            return


    # Update database
    c.execute("SELECT endorse, daykick FROM members WHERE user_id = ?", (target_member.id,))
    record = c.fetchone()

    if not record:
        await interaction.response.send_message(f"User {username} is not being tracked.")
        return

    endorse, daykick = record
    endorse += 1
    daykick += 14
    c.execute("UPDATE members SET endorse = ?, daykick = ? WHERE user_id = ?", 
              (endorse, daykick, target_member.id))
    conn.commit()

    # Track the endorsement
    c.execute("INSERT INTO endorsements (endorser_id, endorsed_id, timestamp) VALUES (?, ?, ?)", 
              (interaction.user.id, target_member.id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()

    await interaction.response.send_message(f"Endorsed {username}. Current endorsements: {endorse}, days left to socialize: {daykick}")

    # Check if ENDORSE reaches 6
    if endorse >= 5:
        guest_role = discord.utils.get(interaction.guild.roles, name=GUEST_ROLE)
        regular_role = discord.utils.get(interaction.guild.roles, name=REGULAR_ROLE)

        await target_member.remove_roles(guest_role)
        await target_member.add_roles(regular_role)

        # Remove from database
        c.execute("DELETE FROM members WHERE user_id = ?", (target_member.id,))
        c.execute("DELETE FROM endorsements WHERE endorsed_id = ? OR endorser_id = ?", (target_member.id, target_member.id))
        conn.commit()

        await interaction.response.send_message(f"{username} has been promoted to Regular!")

    # If Endorsement is 6 and they do not have guest role, remove them from the database
    if endorse >= 5: 
        guest_role = discord.utils.get(interaction.guild.roles, name=GUEST_ROLE)
        if guest_role not in target_member.roles:
            c.execute("DELETE FROM members WHERE user_id = ?", (target_member.id,))
            c.execute("DELETE FROM endorsements WHERE endorsed_id = ? OR endorser_id = ?", (target_member.id, target_member.id))
            conn.commit()
            print(f"Removed {username} from the database for already being accepted into community.")



# Manually add an endorsement to a user, it takes the user and the endorser as arguments
@tree.command(name="addendorsement", description="Manually add an endorsement to a user")
async def addendorsement(interaction: discord.Interaction, username: str, endorser: str):
    if not interaction.channel.name == "endorsements":
        await interaction.response.send_message("This command cannot be used here.")
        return

    #Check if they are either an officer or founder
    if discord.utils.get(interaction.user.roles, name=OFFICER_ROLE) or discord.utils.get(interaction.user.roles, name=FOUNDER_ROLE):
        pass
    else:
        await interaction.response.send_message("You do not have permission to use this command.")
        return

    target_member = discord.utils.get(interaction.guild.members, name=username)
    if not target_member:
        await interaction.response.send_message(f"User {username} not found.")
        return

    endorser_member = discord.utils.get(interaction.guild.members, name=endorser)
    if not endorser_member:
        await interaction.response.send_message(f"User {endorser} not found.")
        return

    # Update database
    c.execute("SELECT endorse, daykick FROM members WHERE user_id = ?", (target_member.id,))
    record = c.fetchone()

    if not record:
        await interaction.response.send_message(f"User {username} is not being tracked.")
        return

    endorse, daykick = record
    endorse += 1
    daykick += 14
    c.execute("UPDATE members SET endorse = ?, daykick = ? WHERE user_id = ?", 
              (endorse, daykick, target_member.id))
    conn.commit()

    # Track the endorsement
    c.execute("INSERT INTO endorsements (endorser_id, endorsed_id, timestamp) VALUES (?, ?, ?)", 
              (endorser_member.id, target_member.id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )
    conn.commit()

    await interaction.response.send_message(f"Endorsed {username} by {endorser}. Current endorsements: {endorse}, days left to socialize: {daykick}")

    # # Check if ENDORSE reaches 5
    # if endorse >= 5:
    #     guest_role = discord.utils.get(interaction.guild.roles, name=GUEST_ROLE)
    #     regular_role = discord.utils.get(interaction.guild.roles, name=REGULAR_ROLE)

    #     await target_member.remove_roles(guest_role)
    #     await target_member.add_roles(regular_role)

    #     # Remove from the database
    #     c.execute("DELETE FROM members WHERE user_id = ?", (target_member.id,))
    #     c.execute("DELETE FROM endorsements WHERE endorsed_id = ? OR endorser_id = ?", (target_member.id, target_member.id))
    #     conn.commit()
    #     await interaction.response.send_message(f"{username} has been promoted to Regular!")



# Command to manually add a user to the database
@tree.command(name="adduser", description="Add a user to the database")
async def adduser(interaction: discord.Interaction, username: str):
    if not interaction.channel.name == "endorsements":
        await interaction.response.send_message("This command cannot be used here.")
        return

    #Check if they are either an officer or founder
    if discord.utils.get(interaction.user.roles, name=OFFICER_ROLE) or discord.utils.get(interaction.user.roles, name=FOUNDER_ROLE):
        pass
    else:
        await interaction.response.send_message("You do not have permission to use this command.")
        return

    target_member = discord.utils.get(interaction.guild.members, name=username)
    if not target_member:
        await interaction.response.send_message(f"User {username} not found.")
        return

    c.execute("INSERT OR IGNORE INTO members (user_id, daykick, endorse) VALUES (?, ?, ?)", 
              (target_member.id, 31, 0))
    conn.commit()
    await interaction.response.send_message(f"Added {username} to the database.")
    print(f"Added {username} to the database.")

# Command to manually remove a user from the database
@tree.command(name="removeuser", description="Remove a user from the database")
async def removeuser(interaction: discord.Interaction, username: str):
    if not interaction.channel.name == "endorsements":
        await interaction.response.send_message("This command cannot be used here.")
        return

    #Check if they are either an officer or founder
    if discord.utils.get(interaction.user.roles, name=OFFICER_ROLE) or discord.utils.get(interaction.user.roles, name=FOUNDER_ROLE):
        pass
    else:
        await interaction.response.send_message("You do not have permission to use this command.")
        return

    target_member = discord.utils.get(interaction.guild.members, name=username)
    if not target_member:
        await interaction.response.send_message(f"User {username} not found.")
        return

    c.execute("DELETE FROM members WHERE user_id = ?", (target_member.id,))
    c.execute("DELETE FROM endorsements WHERE endorsed_id = ? OR endorser_id = ?", (target_member.id, target_member.id))
    conn.commit()
    await interaction.response.send_message(f"Removed {username} from the database.")
    print(f"Removed {username} from the database.")

    # Manually clears all data from the databases


@tree.command(name="cleardb", description="Clear all data from the databases")
async def cleardb(interaction: discord.Interaction):
    if not interaction.channel.name == "endorsements":
        await interaction.response.send_message("This command cannot be used here.")
        return

    #Check if they are either an officer or founder
    if discord.utils.get(interaction.user.roles, name=FOUNDER_ROLE):
        pass
    else:
        await interaction.response.send_message("You do not have permission to use this command.")
        return
    
    # Asks for confirmation
    await interaction.response.send_message("Are you sure you want to clear all data from the databases? Type 'yes' to confirm.")
    response = await bot.wait_for("message", check=lambda m: m.author == interaction.user)
    if response.content.lower() != "yes":
        await interaction.response.send_message("Cancelled.")
        return

    c.execute("DELETE FROM members")
    c.execute("DELETE FROM endorsements")
    conn.commit()
    await interaction.response.send_message("Cleared all data from the databases.")
    print("Cleared all data from the databases.")


# # Command to show all commands
# @bot.command(name="showcommands")
# async def showcommands(interaction):
#     await interaction.response.send_message(
#         "Available commands:\n"
#         "!ping: Respond with 'pong'\n"
#         "!show: Show all members in the database\n"
#         "!stats <username>: Show stats of a user\n"
#         "!setdaykick <username> <daykick>: Set DAYKICK of a user\n"
#         "!endorse <username>: Endorse a user\n"
#         "!adduser <username>: Add a user to the database\n"
#         "!removeuser <username>: Remove a user from the database"
#     )


@tasks.loop(hours=24)
async def daily_check():
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
            c.execute("DELETE FROM endorsements WHERE endorsed_id = ? OR endorser_id = ?", (user_id, user_id))
        else:
            c.execute("UPDATE members SET daykick = ? WHERE user_id = ?", (daykick, user_id))
            c.execute("DELETE FROM endorsements WHERE endorsed_id = ? OR endorser_id = ?", (user_id, user_id))

        # Check if daykick = 0 and they do not have guest role, remove them from the database
        if daykick <= 0:
            member = guild.get_member(user_id)
            if member:
                guest_role = discord.utils.get(guild.roles, name=GUEST_ROLE)
                if guest_role not in member.roles:
                    c.execute("DELETE FROM members WHERE user_id = ?", (user_id,))
                    c.execute("DELETE FROM endorsements WHERE endorsed_id = ? OR endorser_id = ?", (user_id, user_id))
                    print(f"Removed {member.name} from the database for already being accepted into community.")

    #Check if the user is no longer in the server and remove them from the database
    c.execute("SELECT user_id FROM members")
    members = c.fetchall()
    for user_id in members:
        member = guild.get_member(user_id[0])
        if not member:
            c.execute("DELETE FROM members WHERE user_id = ?", (user_id[0],))
            c.execute("DELETE FROM endorsements WHERE endorsed_id = ? OR endorser_id = ?", (user_id[0], user_id[0]))
            print(f"Removed {user_id[0]} from the database for no longer being in the server.")

    conn.commit()
    print(f"Daily check completed at {now}.")
    await channel.send(f"Daily check completed at {now}.")

 
# Run the bot
bot.run(TOKEN)

