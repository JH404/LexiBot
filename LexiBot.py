import asyncio
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

last_user_message = None
last_user_id = None
wordchain_channel_id = None
used_words = {}
selected_reaction = None
on_ready_message = """
** :chains: Welcome to play the Wordchain! :chains:  **

**Aloita uusi peli reagoimalla tähän viestiin haluamasi pelimuotoa vastaavalla emojilla!**

:ok_hand: Sama käyttäjä ei voi vastata kuin kerran putkeen.
:v: Samoja sanoja ei voi käyttää uudelleen.
:metal: Voit kirjoittaa vain yhden sanan kerrallaan.
:pinched_fingers: Helpotat muiden peliä kun et muokkaa tai poista vastauksiasi.
:muscle: Sääntöjä rikkoessa botti aloittaa uuden pelin.

**Wordchainin eri pelimuotojen säännöt alapuolella:**

:milk:  **Milk mode:**
Uusi sana alkaa edellisen sanan viimeisellä kirjaimella.

:coffee:  **Coffee mode:**
Uusi sana alkaa edellisen sanan kahdella viimeisellä kirjaimella.
Sanan pituus vähintään 4 kirjainta.

:cocktail:  **Mojito mode:**
Uusi sana alkaa edellisen sanan viimeisellä kirjaimella.
Uusi sana sisältää 2 samaa kirjainta edellisestä sanasta lukuunottamatta viimeistä kirjainta.
Sanan pituus vähintään 4 kirjainta.

:beers:  **Booze mode:**
Uusi sana alkaa edellisen sanan kahdella viimeisellä kirjaimella.
Uusi sana sisältää 2 samaa kirjainta edellisestä sanasta lukuunottamatta kahta viimeistä kirjainta.
Sanan pituus vähintään 5 kirjainta.
-
"""


async def handle_reactions(message):
    global selected_reaction
    emoji_list = ['\U0001F95B', '\U00002615', '\U0001F378', '\U0001F37B']
    for emoji in emoji_list:
        await message.add_reaction(emoji)

    def check(reaction, user):
        return user != bot.user and reaction.message.id == message.id

    reaction, user = await bot.wait_for('reaction_add', check=check)
    selected_reaction = reaction.emoji
    if reaction.emoji == '\U0001F95B':
        await reaction.message.channel.send(f":milk: Okay, I'll go easy on you. First word is: **Maito**")
    elif reaction.emoji == '\U00002615':
        await reaction.message.channel.send(f':coffee: Too tired for hard one? First word is: **Kahvi**')
    elif reaction.emoji == '\U0001F378':
        await reaction.message.channel.send(f'_Tätä pelimuotoa ei vielä ole olemassa!_')
        # :cocktail: Something tougher? As you wish! First word is: **Mojito**
    elif reaction.emoji == '\U0001F37B':
        await reaction.message.channel.send(f'_Tätä pelimuotoa ei vielä ole olemassa!_')
        # :beers: You are not immortal you know? First word is: **Karhu**


async def handle_rule_violation(channel):
    global last_user_id, used_words
    await channel.send(
        f"**Sääntöjä rikottu!** _Peli nollataan 10 sekunnin kuluttua..._")
    await asyncio.sleep(10)
    await channel.purge()
    last_user_id = None
    used_words = {}
    new_message = await channel.send(on_ready_message)
    await handle_reactions(new_message)


@bot.event
async def on_ready():
    global wordchain_channel_id
    print(f"Logged in as {bot.user.name}")
    for guild in bot.guilds:
        existing_channel = discord.utils.get(guild.text_channels, name="wordchain")
        if existing_channel:
            await existing_channel.delete()
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(manage_channels=False, mention_everyone=False,
                                                            embed_links=False, attach_files=False,
                                                            view_channel=True, read_message_history=True,
                                                            read_messages=True),
            bot.user: discord.PermissionOverwrite(read_message_history=True, manage_messages=True,
                                                  send_messages=True,
                                                  read_messages=True, manage_channels=True)
        }
        channel = await guild.create_text_channel("wordchain", overwrites=overwrites)
        wordchain_channel_id = channel.id
        message = await channel.send(on_ready_message)
        await handle_reactions(message)


@bot.event
async def on_message_delete(message):
    global last_user_message, wordchain_channel_id
    if message.channel.id != wordchain_channel_id:
        return
    if message == last_user_message:
        await message.channel.send(f"Sana poistettu tai sitä on muokattu: Jatka Wordchainia sanasta: {message.content}")
        last_user_message = None


@bot.event
async def on_message_edit(before, after):
    global last_user_message, wordchain_channel_id
    if before.channel.id != wordchain_channel_id:
        return
    if before == last_user_message:
        await before.channel.send(f"Sana poistettu tai sitä on muokattu: Jatka Wordchainia sanasta: {before.content}")
        last_user_message = None


@bot.event
async def on_message(message):
    global last_user_message, wordchain_channel_id, last_user_id, used_words, selected_reaction
    if message.channel.id != wordchain_channel_id or selected_reaction is None:
        return
    if message.author == bot.user:
        return
    if not message.author.bot:
        if last_user_id == message.author.id:
            await message.channel.send(f"Voit lähettää vain yhden viestin kerrallaan!")
            await handle_rule_violation(message.channel)
            return
        if message.content in used_words:
            await message.channel.send(f"Sana **'{message.content}'** on jo käytetty!")
            await handle_rule_violation(message.channel)
            return
        last_user_message = message
        last_user_id = message.author.id
        used_words[message.content] = True
    if len(message.content.split()) > 1:
        await message.channel.send(f"Viestisi voi sisältää vain yhden sanan!")
        await handle_rule_violation(message.channel)
        return


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send('')


bot.run(os.getenv("TOKEN"))

input("Press Enter to exit...")
