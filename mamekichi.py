import discord
from discord.ext import commands
import time

from datetime import timedelta
from datetime import datetime
import math

description = '''Bot'''
bot = commands.Bot(command_prefix='+', description=description)

market = []

def _check_role(user, role):
    if not isinstance(user, discord.member.Member):
        return False

    return role in [r.name for r in user.roles]

async def _async_check_channel(name, ctx):
    if not isinstance(ctx.channel, discord.channel.TextChannel) or ctx.channel.name != name:
        await ctx.send("We are not here!\n*Not here...*")
        return False

    return True

def _log(message):
    print(time.strftime("%Y %b %d %H:%M:%S") + ": " + str(message))

def _time_string(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    periods = [('hours', hours), ('minutes', minutes)]
    return ' '.join('{} {}'.format(math.floor(value), name) for name, value in periods if value)

def _remove_old():
    global market

    old_market = market
    market = []

    for m in old_market:
        if (m["expire"] - datetime.now()).total_seconds() > 1:
            market.append(m)

@bot.event
async def on_ready():
    _log('Logged in as')
    _log(bot.user.name)
    _log(bot.user.id)
    _log('------')

@bot.command()
async def regmarket(ctx):
    if not await _async_check_channel("nook-cranny-zone", ctx):
        return

    s = ctx.message.content.split()

    if len(s) != 3:
        await ctx.send("Hi!\n*Hi...*\nSorry we can't understand.\n*Sorry...*")
        return
    
    open_time = s[1]
    bells = s[2]

    if not open_time.isdigit() or not bells.isdigit() or len(open_time) < 3 or len(open_time) > 4:
        await ctx.send("Hi!\n*Hi...*\nSorry we can't understand.\n*Sorry...*")
        return
    
    bells = int(bells)

    if len(open_time) == 3:
        hours = int(open_time[:1])
        minutes = int(open_time[1:])
    else:
        hours = int(open_time[:2])
        minutes = int(open_time[2:])

    if hours >= 24 or minutes >= 60:
        await ctx.send("Hi!\n*Hi...*\nSorry we can't understand.\n*Sorry...*")
        return

    if hours < 8 or hours > 21:
        await ctx.send("Sorry the nook store is closed.\n*Sorry, closed...*")
        return

    for m in market:
        if m["user"].id == ctx.author.id:
            await ctx.send("Welcome!\n*Come...*\n\nYou only have one Nook Cranny...\n*Only one...*\n\nSee you later!\n*Later...*")
            return

    _remove_old()

    if hours < 12:
        expire = timedelta(hours=12, minutes=0) - timedelta(hours=hours, minutes=minutes)
    else:
        expire = timedelta(hours=22, minutes=0) - timedelta(hours=hours, minutes=minutes)

    market.append({
        "user": ctx.author,
        "expire": datetime.now() + expire,
        "bells": int(bells)
    })

    await ctx.send("Welcome!\n*Come...*\n**" + ctx.author.mention + "'s** nook cranny is buying turnips for **" + str(bells) + "** bells!\nThank you!\n*Thank you...*")

@bot.command()
async def latestmarket(ctx):
    if not await _async_check_channel("nook-cranny-zone", ctx):
        return

    _remove_old()

    if len(market) == 0:
        await ctx.send("Welcome!\n*Come...*\n\nSorry, we are not looking for turnips at the moment.\n*Sorry...*")
        return
    
    message = "Welcome!\n*Come...*\n\nPlease look around.\n*Round...*\n\n"

    for m in sorted(market, key=lambda m: -m["bells"]):
        message += "**" + str(m["user"]) + "'s** Nook Cranny is buying for **" + str(m["bells"]) + "** bells.\n"
        message += "**" + _time_string((m["expire"] - datetime.now()).total_seconds()) + "** left until closing!\n\n"

    message += "Thank you!\n*Thank you...*"

    await ctx.send(message)
    
@bot.command()
async def removemarket(ctx):
    if not await _async_check_channel("nook-cranny-zone", ctx):
        return

    _remove_old()

    s = ctx.message.content.split()

    if len(s) == 1:
        global market

        old_market = market
        market = []

        found = False

        for m in old_market:
            if m["user"].id == ctx.author.id:
                found = True
            else:
                market.append(m)

        if found:
            await ctx.send(ctx.author.mention + "'s Nook Cranny is closing now.\nThank you.\n*Thank you...*")
        else:
            await ctx.send("Hi!\n*Hi...*\nSorry we can't understand.\n*Sorry...*")
        
        return

    if len(ctx.message.mentions) == 0:
        await ctx.send("Hi!\n*Hi...*\nSorry we can't understand.\n*Sorry...*")
        return

    if not _check_role(ctx.author, "ISLAND COORDINATOR") and not _check_role(ctx.author, "MODERATOR") and not _check_role(ctx.author, "HEAD MODERATOR"):
        await ctx.send("Hi!\n*Hi...*\nSorry we can't understand.\n*Sorry...*")
        return

    old_market = market
    market = []

    found = False

    for m in old_market:
        if m["user"].id == ctx.message.mentions[0].id:
            found = True
        else:
            market.append(m)

    if found:
        await ctx.send(ctx.message.mentions[0].mention + "'s Nook Cranny is closing early.\nThank you.\n*Thank you...*")
    else:
        await ctx.send("Hi!\n*Hi...*\nSorry we can't understand.\n*Sorry...*")

bot.run("XXX")
