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
wordchain_channel_id = None
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

emoji_list = ['\U0001F95B', '\U00002615', '\U0001F379', '\U0001F37B']


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
        for emoji in emoji_list:
            await message.add_reaction(emoji)


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
    global last_user_message, wordchain_channel_id
    if message.channel.id != wordchain_channel_id:
        return
    if message.author == bot.user:
        return
    if not message.author.bot:
        last_user_message = message
    if len(message.content.split()) > 1:
        await message.channel.send(
            f"Sääntöjä rikottu! Voit lähettää vain yhden sanan kerrallaan. Peli nollataan 15 sekunnin kuluttua...")
        await asyncio.sleep(15)
        await message.channel.purge()
        new_message = await message.channel.send(on_ready_message)
        for emoji in emoji_list:
            await new_message.add_reaction(emoji)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send('')


bot.run(os.getenv("TOKEN"))

input("Press Enter to exit...")
