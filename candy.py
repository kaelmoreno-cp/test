from google.cloud import firestore
import discord
import os
import time
import asyncio

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "/home/username/key.json"
os.environ['GCLOUD_PROJECT'] = "XXX"

_cache = {}
_limits = {}

def _log(message):
    print(time.strftime("%Y %b %d %H:%M:%S") + ": " + str(message))

@firestore.transactional
def _update_doc(transaction, doc_ref):
    snapshot = doc_ref.get(transaction=transaction).to_dict()

    update = {}

    for user_id in _cache:
        user_key = "u" + str(user_id)
        amount = (snapshot[user_key] if snapshot and user_key in snapshot else 0) + _cache[user_id]
        update[user_key] = amount if amount != 0 else firestore.DELETE_FIELD

    transaction.update(doc_ref, update)

def _get_week():
    if time.strftime("%W") == "00":
        return "week-" + str(int(time.strftime("%Y")) - 1) + "-53"
    return "week-" + time.strftime("%Y-%W")

def _get_month():
    return "month-" + time.strftime("%Y-%m")

def _save():
    global _cache

    db = firestore.Client()
    transaction = db.transaction()

    for doc in [_get_month(), "all", _get_week()]:
        doc_ref = db.collection(u'candies').document(doc)

        if not doc_ref.get().exists:
            doc_ref.set({})

        _update_doc(transaction, doc_ref)
    
    db._firestore_api.transport._channel.close()
    _cache = {}

def _give_candy(user, amount):
    if not user in _cache:
        _cache[user] = 0
    
    _cache[user] += amount
    _log("Gave " + str(user) + " " + str(amount))

def _get_candy_amount(user):
    db = firestore.Client()
    snapshot = db.collection(u'candies').document(u'all').get().to_dict()
    db._firestore_api.transport._channel.close()
    
    user_key = "u" + str(user)

    amount = snapshot[user_key] if snapshot and user_key in snapshot else 0

    if user in _cache:
        amount += _cache[user]
    
    return amount

def _get_top(doc):
    db = firestore.Client()
    snapshot = db.collection(u'candies').document(doc).get().to_dict()
    db._firestore_api.transport._channel.close()

    if not snapshot:
        return []
    
    for user in snapshot:
        if user in _cache:
            snapshot[user] += _cache[user]
    
    top = sorted([u for u in snapshot], key=lambda u: snapshot[u], reverse=True)[0:10]
    
    return [[int(u[1:]), snapshot[u]] for u in top]



def _check_role(user, roles):
    if not isinstance(user, discord.member.Member):
        return False

    for role in roles:
        if role in [r.name for r in user.roles]:
            return True
    
    return False

async def _async_check_role(roles, message):
    if not _check_role(message.author, roles):
        await message.channel.send("Hey " + message.author.mention + "! ⛔️Only " + roles[0] + " can do this!")
        return False

    return True

async def _check_rewards(user, message):    
    amount = _get_candy_amount(user.id)

    if amount < 50:
        return False
    
    if not isinstance(user, discord.member.Member):
        return False

    if not _check_role(user, "RED ZONER"):
        role = discord.utils.get(message.guild.roles, name="RED ZONER")
        if role:
            await user.add_roles(role)
            return True
    
    return False

class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bg_task = self.loop.create_task(self.my_background_task())

    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

    async def on_message(self, message):
        # we do not want the bot to reply to itself
        if message.author.id == self.user.id:
            return
        
        if isinstance(message.channel, discord.channel.DMChannel):
            await message.channel.send("You really want candies, don't you?")
            return

        args = message.content.split()

        if len(args) == 0:
            return

        if args[0] == "!give":
            if not await _async_check_role(["Vanya", "Looker"], message):
                return

            if len(args) < 2 or not args[1].isdigit() or not len(message.mentions) != 0:
                await message.channel.send("Wrong command!")
                return

            _give_candy(message.mentions[0].id, int(args[1]))
            await message.channel.send("Hey " + message.mentions[0].mention + ", you did well! I appreciate it! Here! Take " + args[1] + " candies! ")
            
            await _check_rewards(message.mentions[0], message)

            return

        if args[0] == "!take":
            if not await _async_check_role(["Vanya"], message):
                return

            if len(args) < 2 or not args[1].isdigit() or not len(message.mentions) != 0:
                await message.channel.send("Wrong command!")
                return

            _give_candy(message.mentions[0].id, -int(args[1]))
            await message.channel.send("Hey " + message.mentions[0].mention + ", Oh no! You did something bad. I am taking " + args[1] + " candies away.")

            return

        if args[0] == "!rep":
            if len(message.mentions) == 0:
                amount = _get_candy_amount(message.author.id)
                await message.channel.send("Hey " + message.author.mention + ", you have earned " + str(amount) + " candies! Awesome!")
                return

            amount = _get_candy_amount(message.mentions[0].id)
            await message.channel.send(message.mentions[0].mention + " has collected " + str(amount) + " candies so far! Terrific!")
            
            return
        
        if args[0] == "!toprep":
            if len(args) > 2:
                await message.channel.send("Wrong command!")
                return

            if len(args) == 2:
                if args[1] == "weekly":
                    top = _get_top(_get_week())
                    top_users_message = "These " + str(len(top)) + " people take the lead this week!"
                elif args[1] == "monthly":
                    top = _get_top(_get_month())
                    top_users_message = "Best " + str(len(top)) + " people who have the most candies!\nAmazing!"
                else:
                    await message.channel.send("Wrong command!")
                    return
            else:
                top = _get_top("all")
                top_users_message = "These " + str(len(top)) + " people have done very well!\nEnjoy the candies!"

            top_users = ""
            for user_id in top:
                user = client.get_user(user_id[0])
                top_users += "@" + str(user) if user else str(user_id[0])
                top_users += " - - - > " + str(user_id[1]) + "\n"

            if len(top) == 0:
                await message.channel.send("The list is empty!")
                return

            await message.channel.send(top_users + top_users_message)
            return
        
        global _limits
        _new_limits = {}

        for u in _limits:
            if not time.time() - _limits[u] > 10:
                _new_limits[u] = _limits[u]

        _limits = _new_limits

        words = [arg for arg in args]
        for i in range(len(args) - 1):
            words.append(" ".join(args[i:i+2]))

        if len(message.mentions) > 0:
            for word in words:
                if word.lower() in ["thanks", "thank", "thankful", "cheers", "danke", "appreciate", "grateful", "gratitude", "gracias", "merci", "grazie", "arigato", "ありがとう", "spasiba", "spasibo", "takk", "tak", "obrigado", "terima kasih", "trims", "tq", "thx", "cheers", "shukran", "xie xie", "hvala", "tak", "dank", "kiitos", "merci", "danke", "efharisto", "mahalo", "grazie", "arigato", "kamsahamnida", "takk obrigado", "spasiba", "gracias", "salamat", "kop khun", "nuhun", "matur", "suksma", "nuwun", "sakalangkong", "mauliate", "makasih", "tampiaseh", "amanai", "epanggawang"]:
                    if message.mentions[0].id != message.author.id and message.author.id not in _limits:
                        _give_candy(message.mentions[0].id, 1)
                        _limits[message.author.id] = time.time()
                        await message.channel.send(message.mentions[0].mention + " got a candy!")
                        await _check_rewards(message.mentions[0], message)
                        return

    async def my_background_task(self):
        await self.wait_until_ready()
        while not self.is_closed():
            if len(_cache) > 0:
                _save()
            await asyncio.sleep(3)

client = MyClient()
client.run('XXX')
