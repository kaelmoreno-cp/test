import discord
from discord.ext import commands
import random
import time
import os
import re

from google.cloud import firestore

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "stock.json"
os.environ['GCLOUD_PROJECT'] = "stock-checker-d04b9"

description = '''Bot'''

bot = commands.Bot(command_prefix='!', description=description)

raids = {}

def _get_fc(user):
    db = firestore.Client()
    fc =  db.collection(u'friend_codes').document(str(user)).get().to_dict()
    db._firestore_api.transport._channel.close()
    return fc

def _set_fc(user, fc, fc_name):
    db = firestore.Client()
    db.collection(u'friend_codes').document(str(user)).set({ u'fc': fc, u'name': fc_name })
    db._firestore_api.transport._channel.close()

def _log(message):
    print(time.strftime("%Y %b %d %H:%M:%S") + ": " + str(message))

def _check_role(user, role):
    if not isinstance(user, discord.member.Member):
        return False

    return role in [r.name for r in user.roles]

async def _async_check_role(role, ctx):
    if not _check_role(ctx.author, role):
        await ctx.send("Hey " + ctx.author.mention + "! ⛔️Only " + role + " can do this!")
        return False

    return True

async def _async_check_channel(name, ctx):
    if not isinstance(ctx.channel, discord.channel.TextChannel) or ctx.channel.name != name:
        await ctx.send("Hey " + ctx.author.mention + "! Please enter your command in #" + name + "!")
        return False

    return True

async def _async_check_dm(ctx):
    if not isinstance(ctx.channel, discord.channel.DMChannel):
        await ctx.send("Hey " + ctx.author.mention + "! Please enter your command in DM to Looker!")
        return False

    return True

async def _async_check_raid_name(raid_name, ctx):
    if raid_name not in raids:
        await ctx.send("Hey " + ctx.author.mention + "! " + raid_name + " raid does not exist!")
        return False
    
    return True

async def _async_check_host(raid_name, ctx):
    if raids[raid_name]["host"] != ctx.author.id:
        await ctx.send("Hey " + ctx.author.mention + "! Only Person in Command can do this")
        return False

    return True

async def _async_check_host_or_vanya(raid_name, ctx):
    if raids[raid_name]["host"] != ctx.author.id and not _check_role(ctx.author, "Vanya"):
        await ctx.send("Hey " + ctx.author.mention + "! Only Person in Command can do this")
        return False

    return True

async def _async_check_fc(ctx):
    if _get_fc(ctx.author) == None:
        await ctx.send("Hey " + ctx.author.mention + "! You don't have your Friend Code registered. Please register first!")
        return False
    
    return True

async def _async_parse_raid_name(ctx):
    s = ctx.message.content.split()

    if len(s) < 2:
        await ctx.send("Wrong command!")
        return None

    return " ".join(s[1:])

async def _async_parse_raid_name_and_capacity(ctx):
    s = ctx.message.content.split()

    if len(s) < 3:
        await ctx.send("Wrong command!")
        return None, None

    raid_name = " ".join(s[1:-1])
    capacity = s[-1]

    if not capacity.isdigit():
        await ctx.send("Wrong command!")
        return None, None

    return raid_name, int(capacity)

async def _send_large_message(message, ctx):
    single_message = ""
    for p in message.split("\n"):
        if len(single_message) + len(p) > 1900:
            await ctx.send(single_message)
            single_message = ""
        single_message += p + "\n"
    
    if single_message != "":
        await ctx.send(single_message)

async def _next(ctx, raid_name):
    code = "".join(random.sample([str(x) for x in range(10)], 4))

    host = bot.get_user(raids[raid_name]["host"])

    if not host:
        del raids[raid_name]
        await ctx.send("Person in Command is not here, " + raid_name + " raid will be closed!")
        return

    # !host will check if user has fc
    host_fc = _get_fc(host)

    selected_users = []
    raids[raid_name]["current_users"] = []

    i = 0
    while len(raids[raid_name]["queue"]) > 0 and i < 3:
        user_id = raids[raid_name]["queue"].pop(0)
        user = bot.get_user(user_id)
        if user:
            try:
                await user.send("Your code is " + code + ".\nPlease add this FC " + host_fc["fc"] + " (" + host_fc["name"] + "). Good luck! Please thank the host \"Thanks @host\"!\n\nPlease remember to remove the host from your switch friend list.\n\nYou will never be able to get into the raid again without requeuing.\n*\n*\n*")
                message_sent = True
            except:
                message_sent = False
            
            if message_sent:
                _log("Sent code " + code + " to " + user.name)
                # !join will check if user has fc
                user_fc = _get_fc(user)
                selected_users.append(user_fc["fc"] + " (" + user_fc["name"] + ")")
                raids[raid_name]["current_users"].append(user_id)
                i += 1
            else:
                await ctx.send("Attention!!!\n" + user.mention + "\n\nYou are being skipped right now because Looker cannot send you Direct Message!\n\nPlease check your setting!\n\nThank you!")

    await host.send("Your code is " + code + ".\nPlease check your Friend Request and accept\n" + "\n".join(selected_users) + "\nDon't forget to remove them right away after they get into the raid. Thank you for hosting!\n*\n*\n*")
    
    raids[raid_name]["raid_n"] += 1
    raids[raid_name]["raid_is_up"] = False

@bot.event
async def on_ready():
    _log('Logged in as')
    _log(bot.user.name)
    _log(bot.user.id)
    _log('------')

@bot.command()
async def host(ctx):
    raid_name, capacity = await _async_parse_raid_name_and_capacity(ctx)

    if not raid_name or not capacity or \
            not await _async_check_channel("shiny-queue-zone", ctx) or \
            not await _async_check_role("Shiny Raid Host", ctx) or \
            not await _async_check_fc(ctx):
        return
    
    if capacity < 21:
        await ctx.send("Sorry " + ctx.author.mention + ", the minimum capacity for Looker is 21 or 7 raids.")
        return

    raids[raid_name] = {
        "host": ctx.author.id,
        "queue": [],
        "capacity": capacity,
        "started": False,
        "raid_n": 1,
        "raid_is_up": False,
        "current_users": [],
        "queue_size_when_started": None
    }

    await ctx.send("@here get ready for " + raid_name + " raid!")

    _log(str(ctx.author) + " hosted " + raid_name + " raid with capacity " + str(capacity))

@bot.command()
async def join(ctx):
    raid_name = await _async_parse_raid_name(ctx)

    if not raid_name or \
            not await _async_check_channel("shiny-queue-zone", ctx) or \
            not await _async_check_raid_name(raid_name, ctx) or \
            not await _async_check_fc(ctx):
        return
    
    if len(raids[raid_name]["queue"]) == raids[raid_name]["capacity"]:
        await ctx.send("Sorry " + ctx.author.mention + ", " + raid_name + " raid is full!")
        return

    if ctx.author.id == raids[raid_name]["host"]:
        await ctx.send("Hey " + ctx.author.mention + "! You are already in! You are the host!")
        return

    for _raid_name in raids:
        if ctx.author.id in raids[_raid_name]["queue"]:
            await ctx.send("Hey " + ctx.author.mention + "! You have already joined " + _raid_name + "!")
            return
    
    if raids[raid_name]["started"]:
        await ctx.send("Hey " + ctx.author.mention + "! You are too late, " + raid_name + " raid has already started!")
        return
    
    raids[raid_name]["queue"].append(ctx.author.id)
    await ctx.send(ctx.author.mention + " has joined " + raid_name + " raid! There are " + str(len(raids[raid_name]["queue"]) - 1) + " people before you!")

    _log(str(ctx.author) + " joined " + raid_name + " raid")

@bot.command()
async def leave(ctx):
    raid_name = await _async_parse_raid_name(ctx)
    
    if not raid_name or \
            not await _async_check_raid_name(raid_name, ctx):
        return

    user = ctx.author

    if ctx.author.id == raids[raid_name]["host"]:
        await ctx.send("Hey " + ctx.author.mention + "! You are the host, you cannot leave. Pause or close the raid!")
        return

    if ctx.author.id not in raids[raid_name]["queue"]:
        await ctx.send("Hey " + ctx.author.mention + "! You didn't join to begin with!")
        return

    if raids[raid_name]["started"]:
        await ctx.send("Hey " + ctx.author.mention + "! The raid has started! You may not leave the raid!")
        return
    
    raids[raid_name]["queue"].remove(ctx.author.id)
    await ctx.send("Hey " + ctx.author.mention + "! You has been removed from the queue!")

    _log(str(ctx.author) + " has been removed from the " + raid_name + " raid")

@bot.command()
async def start(ctx):
    raid_name = await _async_parse_raid_name(ctx)

    if not raid_name or \
            not await _async_check_channel("shiny-raid-zone", ctx) or \
            not await _async_check_role("Shiny Raid Host", ctx) or \
            not await _async_check_raid_name(raid_name, ctx) or \
            not await _async_check_host(raid_name, ctx):
        return

    if raids[raid_name]["started"]:
        await ctx.send(raid_name + " raid has already started!")
        return
    
    if len(raids[raid_name]["queue"]) == 0:
        del raids[raid_name]
        await ctx.send("It's an unfortunate event.\nNo one is joining.\nRaid has been closed.")
        return

    raids[raid_name]["started"] = True
    raids[raid_name]["queue_size_when_started"] = len(raids[raid_name]["queue"])

    _log(raid_name + " raid has started!")

    await _next(ctx, raid_name)

    message = "Attention!\n"

    for user_id in raids[raid_name]["current_users"]:
        user = bot.get_user(user_id)
        if user:
            message += user.mention + "\n"

    message += "Looker has sent you the FC and Raid Code!\nPlease add the FC ASAP and use that raid code when your raid is up!"

    await ctx.send(message)

@bot.command()
async def next(ctx):
    raid_name = await _async_parse_raid_name(ctx)

    if not raid_name or \
            not await _async_check_channel("shiny-raid-zone", ctx) or \
            not await _async_check_role("Shiny Raid Host", ctx) or \
            not await _async_check_raid_name(raid_name, ctx) or \
            not await _async_check_host(raid_name, ctx):
        return

    if not raids[raid_name]["started"]:
        await ctx.send("Hey " + ctx.author.mention + "! " + raid_name + " raid has not started yet!")
        return

    if not raids[raid_name]["raid_is_up"]:
        await ctx.send("Hey " + ctx.author.mention + "! Not yet! Let them in your raid first!")
        return

    _log("Next " + raid_name + " raid is up!")

    await _next(ctx, raid_name)

    message = "Attention!\n"

    for user_id in raids[raid_name]["current_users"]:
        user = bot.get_user(user_id)
        if user:
            message += user.mention + "\n"

    message += "Looker has sent you the FC and Raid Code!\nPlease add the FC ASAP and use that raid code when your raid is up!"

    await ctx.send(message)

@bot.command()
async def up(ctx):
    raid_name = await _async_parse_raid_name(ctx)

    if not raid_name or \
            not await _async_check_channel("shiny-raid-zone", ctx) or \
            not await _async_check_role("Shiny Raid Host", ctx) or \
            not await _async_check_raid_name(raid_name, ctx) or \
            not await _async_check_host(raid_name, ctx):
        return

    raids[raid_name]["raid_is_up"] = True

    message = "Attention!\n"

    for user_id in raids[raid_name]["current_users"]:
        user = bot.get_user(user_id)
        if user:
            message += user.mention + "\n"

    message += "Your raid is up! Please enter ASAP!\nRefresh your internet connection or restart the game if you can't see the stamp!"

    give_candies = None
    give_candies_to = None

    if len(raids[raid_name]["queue"]) == 0:
        if raids[raid_name]["queue_size_when_started"] >= 60:
            give_candies = 25
            give_candies_to = raids[raid_name]["host"]
        elif raids[raid_name]["queue_size_when_started"] >= 30:
            give_candies = 10
            give_candies_to = raids[raid_name]["host"]

        message += "\n\n" + raid_name + " raid has finished!\nThank you for joining!\nSee you again next time!"
        _log(raid_name + " raid has finished!")

        del raids[raid_name]

    await ctx.send(message)

    if give_candies:
        user = bot.get_user(give_candies_to)
        if user:
            await ctx.send("!give " + str(give_candies) + " " + user.mention)

@bot.command(name='pause')
async def pauseraid(ctx):
    raid_name = await _async_parse_raid_name(ctx)

    if not raid_name or \
            not await _async_check_channel("shiny-raid-zone", ctx) or \
            not await _async_check_role("Shiny Raid Host", ctx) or \
            not await _async_check_raid_name(raid_name, ctx) or \
            not await _async_check_host(raid_name, ctx):
        return

    message = "The host will be taking a short break.\n"
    
    for user_id in raids[raid_name]["queue"]:
        user = bot.get_user(user_id)
        if user:
            message += user.mention + "\n"

    message += "\nPlease wait for your turn until further notice!"

    await ctx.send(message)

@bot.command(name='continue')
async def continueraid(ctx):
    raid_name = await _async_parse_raid_name(ctx)

    if not raid_name or \
            not await _async_check_channel("shiny-raid-zone", ctx) or \
            not await _async_check_role("Shiny Raid Host", ctx) or \
            not await _async_check_raid_name(raid_name, ctx) or \
            not await _async_check_host(raid_name, ctx):
        return

    message = raid_name + " raid will now continue, please make sure you are ready!\n"
    
    for user_id in raids[raid_name]["queue"]:
        user = bot.get_user(user_id)
        if user:
            message += user.mention + "\n"
    
    await ctx.send(message)

@bot.command()
async def close(ctx):
    raid_name = await _async_parse_raid_name(ctx)

    if not raid_name or \
            not await _async_check_channel("shiny-raid-zone", ctx) or \
            not await _async_check_role("Shiny Raid Host", ctx) or \
            not await _async_check_raid_name(raid_name, ctx) or \
            not await _async_check_host_or_vanya(raid_name, ctx):
        return

    if len(raids[raid_name]["queue"]) == 0:
        del raids[raid_name]
        await ctx.send("Oh!\nNo one is joining your raid!\nThe raid has been closed.")
        return

    message = "Oh no!\nThe host needs to go!\n\nTo all people left in the queue!\n\n"

    for user_id in raids[raid_name]["queue"]:
        user = bot.get_user(user_id)
        if user:
            message += user.mention + "\n"

    message += "\nWe are really sorry to inform you, the raid needs to stop!\n\nIt is an unfortunate event.\nPlease join again next time.\nThank you!"
    
    await ctx.send(message)

    del raids[raid_name]

    _log(raid_name + " raid has finished!")

@bot.command()
async def queueposition(ctx):
    if not await _async_check_dm(ctx):
        return

    in_queue = False

    message = ""
    for raid_name in raids:
        if ctx.author.id in raids[raid_name]["queue"]:
            in_queue = True
            if message != "":
                message += "\n"
            message += "You are currently in " + raid_name + " raid!\nYour queue number is " + \
                        str(raids[raid_name]["queue"].index(ctx.author.id) + 1) + ".\n"

    if in_queue:
        message += "\n"
        message += "Kindly wait patiently for your turn!"
    else:
        message += "You are not registered in any raid."

    await ctx.send(message)
    
@bot.command()
async def raidqueue(ctx):
    if not await _async_check_channel("shiny-queue-zone", ctx) or \
            not await _async_check_role("Shiny Raid Host", ctx):
        return
    
    if len(raids) == 0:
        await ctx.send("No ongoing raids right now!")
        return
    
    message = ""
    for raid_name in raids:
        admin = bot.get_user(raids[raid_name]["host"])

        message += raid_name
        
        if admin:
            message += " is being hosted by " + admin.mention + "!"

        message += "\n\n"
        message += "Currently in queue:\n\n"

        seq = 0
        raid_n = raids[raid_name]["raid_n"]

        for user_id in raids[raid_name]["queue"]:
            user = bot.get_user(user_id)
            if user:
                if seq == 0:
                    if raid_n != raids[raid_name]["raid_n"]:
                        message += "\n"
                    message += "  " + raid_name + " raid " + str(raid_n) + "\n"
                message += "  " + user.mention + "\n"
                seq += 1
                if seq == 3:
                    seq = 0
                    raid_n += 1

        message += "\n"
        message += "Please do not DM the host and do not send FR to the host when it is not your turn!\n\nKindly wait patiently for your turn!\nLooker will find you and give you the code!\nTo check your current position, please DM Looker,\n!queueposition\n*\n*\n*\n"

    await _send_large_message(message, ctx)

@bot.command()
async def kick(ctx):
    if not await _async_check_channel("shiny-queue-zone", ctx) or \
            not await _async_check_role("Shiny Raid Host", ctx):
        return

    if len(ctx.message.mentions) == 0:
        await ctx.send("Wrong command!")

    kick_user = ctx.message.mentions[0]
    kicked = False

    for raid_name in raids:
        if kick_user.id in raids[raid_name]["queue"]:
            raids[raid_name]["queue"].remove(kick_user.id)
            kicked = True
    
    if kicked:
        await ctx.send("Sorry " + kick_user.mention + ", please give others chance to enter the raid.")
    else:
        await ctx.send("The user is not in the queue to begin with!")

@bot.command()
async def fc(ctx):
    s = ctx.message.content.split()

    if len(s) == 1:
        user_fc = _get_fc(ctx.author)
        
        if user_fc == None:
            await ctx.send("You don't have your Friend Code registered. Please register first!")
            return
        
        await ctx.send("Hi! My name is " + user_fc["name"] + "! This is my FC " + user_fc["fc"] + "!")
        return

    if len(s) == 2:
        if len(ctx.message.mentions) == 0:
            await ctx.send("Wrong command!")
            return
        
        if _check_role(ctx.message.mentions[0], "Shiny Raid Host"):
            await ctx.send("The FC is hidden. We will let you know when you are in the queue!")
            return

        if _check_role(ctx.message.mentions[0], "Shiny FFA Host"):
            await ctx.send("The FC is hidden. Please wait until the host shares the FC!")
            return

        user_fc = _get_fc(ctx.message.mentions[0])

        if not user_fc:
            await ctx.send("This user has not registered yet! Find " + ctx.message.mentions[0].mention + "!")
            return

        await ctx.send("Hi! The name is " + user_fc["name"] + "! This is the FC " + user_fc["fc"] + "!")
        return

    if len(s) < 6:
        await ctx.send("Wrong command!")
        return

    if s[1] != "set" or s[2] != "switch":
        await ctx.send("Wrong command!")
        return

    if not ctx.channel.name == "friend-codes":
        await ctx.send("Please enter your command in #friend-codes!")
        return

    fc = s[3]

    p = re.compile('^SW\-\d{4}\-\d{4}\-\d{4}$', re.IGNORECASE)
    if not p.match(fc):
        await ctx.send("Wrong command!")
        return
    
    if s[4] != "name":
        await ctx.send("Wrong command!")
        return

    fc_name = " ".join(s[5:])

    await ctx.send(ctx.author.mention + "'s switch friendcode is added to the trainer database!")
    
    _set_fc(ctx.author, fc, fc_name)

    _log("Added FC " + fc_name + "(" + fc + ") for " + str(ctx.author))

bot.run("OTE1NjAyMDc3NTc5ODkwNjg4.Yad-4g.l_HjdpldjbRZeeEhkzKCBVE4gFY")
