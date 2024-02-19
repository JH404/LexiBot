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
parity = 0
is_handling_violation = False
user_message_count = 0
total_message_count = 0
on_ready_message = """
** :chains: Tervetuloa pelaamaan Sanaketjua :chains:  **

**Aloita uusi peli reagoimalla tähän viestiin haluamasi pelimuotoa vastaavalla emojilla!**

:ok_hand: Sama käyttäjä ei voi vastata kuin kerran putkeen.
:v: Samoja sanoja ei voi käyttää uudelleen.
:metal: Voit kirjoittaa vain yhden sanan kerrallaan.
:hand_with_index_finger_and_thumb_crossed: Ei numeroiden eikä erikoismerkkien käyttöä.
:pinched_fingers: Helpotat muiden peliä kun et muokkaa tai poista vastauksiasi.
:muscle: Sääntöjä rikkoessa botti aloittaa uuden pelin.

**Sanaketjun eri pelimuotojen säännöt alapuolella:**

:milk:  **Milk mode:**
- Seuraavan sanan tulee alkaa edellisen sanan viimeisellä kirjaimella.

:coffee:  **Coffee mode:**
- Seuraavan sanan tulee alkaa edellisen sanan kahdella viimeisellä kirjaimella.
- Sanan pituus on oltava vähintään 4 kirjainta.

:cocktail:  **Mojito mode:**
- Seuraavan sanan tulee alkaa edellisen sanan kahdella viimeisellä kirjaimella.
- Joka toisen sanan merkkimäärä tulee olla on parillinen ja joka toisen pariton.
- Sanan pituus on oltava vähintään 4 kirjainta.

:beers:  **Booze mode:**
- Seuraavan sanan tulee alkaa edellisen sanan kahdella viimeisellä kirjaimella.
- Joka toisen sanan merkkimäärä tulee olla on parillinen ja joka toisen pariton.
- Sanassa ei saa olla samaa kirjainta peräkkäin.
- Sanan pituus on oltava vähintään 5 kirjainta.
-------------------------------------------------------------------------------
"""


async def handle_reactions(message):
    global selected_reaction, last_user_message
    emoji_list = ['\U0001F95B', '\U00002615', '\U0001F378', '\U0001F37B']
    for emoji in emoji_list:
        await message.add_reaction(emoji)

    def check(reaction, user):
        return user != bot.user and reaction.message.id == message.id

    reaction, user = await bot.wait_for('reaction_add', check=check)
    selected_reaction = reaction.emoji
    if reaction.emoji == '\U0001F95B':
        await reaction.message.channel.send(f":milk: Okay, I'll go easy on you.")
    elif reaction.emoji == '\U00002615':
        await reaction.message.channel.send(f':coffee: Too tired for hard one?')
    elif reaction.emoji == '\U0001F378':
        await reaction.message.channel.send(f':cocktail: Something tougher? As you wish!')
    elif reaction.emoji == '\U0001F37B':
        await reaction.message.channel.send(f':beers: You are not immortal you know?')


async def handle_rule_violation(channel):
    global last_user_id, used_words, last_user_message, selected_reaction, parity, is_handling_violation, user_message_count, total_message_count
    is_handling_violation = True
    await channel.send(
        f"**Sääntöjä rikottu!** _Peli nollataan 10 sekunnin kuluttua..._")
    await asyncio.sleep(10)
    while True:
        deleted = await channel.purge(limit=100)
        if len(deleted) < 100:
            break
    await channel.purge()

    last_user_message = None
    last_user_id = None
    used_words = {}
    selected_reaction = None
    parity = 0
    user_message_count = 0
    total_message_count = 0

    new_message = await channel.send(on_ready_message)
    await new_message.pin()
    await handle_reactions(new_message)
    is_handling_violation = False


async def milk_mode(message, lower_message_content, last_user_message):
    if last_user_message is not None and lower_message_content[0] != last_user_message.content[-1].lower():
        await message.channel.send(f"Seuraavan sanan tulee alkaa edellisen sanan viimeisellä kirjaimella.")
        await handle_rule_violation(message.channel)
        return False
    return True


async def coffee_mode(message, lower_message_content, last_user_message):
    if len(lower_message_content) < 4:
        await message.channel.send(f"Sanan pituus on oltava vähintään 4 kirjainta.")
        await handle_rule_violation(message.channel)
        return False
    if last_user_message is not None and lower_message_content[:2] != last_user_message.content[-2:].lower():
        await message.channel.send(f"Seuraavan sanan tulee alkaa edellisen sanan kahdella viimeisellä kirjaimella.")
        await handle_rule_violation(message.channel)
        return False
    return True


async def mojito_mode(message, lower_message_content):
    global last_user_message, last_user_id, used_words, parity
    if len(lower_message_content) < 4:
        await message.channel.send(f"Sanan pituus on oltava vähintään 4 kirjainta.")
        await handle_rule_violation(message.channel)
        return False
    if last_user_message is None:
        last_user_message = message
        last_user_id = message.author.id
        used_words[lower_message_content] = True
        parity = 1 - len(lower_message_content) % 2
        return True
    else:
        if lower_message_content[:2] != last_user_message.content[-2:].lower():
            await message.channel.send(f"Seuraavan sanan tulee alkaa edellisen sanan kahdella viimeisellä kirjaimella.")
            await handle_rule_violation(message.channel)
            return False
        if len(lower_message_content) % 2 != parity:
            await message.channel.send(f"Joka toisen sanan merkkimäärä tulee olla on parillinen ja joka toisen pariton.")
            await handle_rule_violation(message.channel)
            return False
    last_user_message = message
    last_user_id = message.author.id
    used_words[lower_message_content] = True
    parity = 1 - parity
    return True


async def booze_mode(message, lower_message_content):
    global last_user_message, last_user_id, used_words, parity
    if len(lower_message_content) < 5:
        await message.channel.send(f"Sanan pituus on oltava vähintään 5 kirjainta.")
        await handle_rule_violation(message.channel)
        return False
    if any(lower_message_content[i] == lower_message_content[i + 1] for i in range(len(lower_message_content) - 1)):
        await message.channel.send(f"Sanassa ei saa olla samaa kirjainta peräkkäin.")
        await handle_rule_violation(message.channel)
        return False
    if last_user_message is None:
        last_user_message = message
        last_user_id = message.author.id
        used_words[lower_message_content] = True
        parity = 1 - len(lower_message_content) % 2
        return True
    else:
        if lower_message_content[:2] != last_user_message.content[-2:].lower():
            await message.channel.send(f"Seuraavan sanan tulee alkaa edellisen sanan kahdella viimeisellä kirjaimella.")
            await handle_rule_violation(message.channel)
            return False
        if len(lower_message_content) % 2 != parity:
            await message.channel.send(f"Joka toisen sanan merkkimäärä tulee olla on parillinen ja joka toisen pariton.")
            await handle_rule_violation(message.channel)
            return False
    last_user_message = message
    last_user_id = message.author.id
    used_words[lower_message_content] = True
    parity = 1 - parity
    return True


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
        await message.pin()
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
    global last_user_message, wordchain_channel_id, last_user_id, used_words, selected_reaction, is_handling_violation, user_message_count, total_message_count
    if is_handling_violation:
        return
    if message.channel.id != wordchain_channel_id or selected_reaction is None:
        return
    if message.author == bot.user:
        return
    if not message.author.bot:
        user_message_count += 1
        total_message_count += 1
        if user_message_count >= 10:
            await message.channel.send(f"**:chains::fire:{total_message_count} STREAK!!!:fire::chains:**")
            user_message_count = 0
        lower_message_content = message.content.lower()
        if not lower_message_content.isalpha():
            await message.channel.send(f"Sanasi ei saa sisältää numeroita tai erikoismerkkejä!")
            await handle_rule_violation(message.channel)
            return
        if last_user_id == message.author.id:
            await message.channel.send(f"Voit lähettää vain yhden sanan vuorollasi!")
            await handle_rule_violation(message.channel)
            return
        if lower_message_content in used_words:
            await message.channel.send(f"Sana **'{message.content}'** on jo käytetty!")
            await handle_rule_violation(message.channel)
            return
        if selected_reaction == '\U0001F95B':  # Milk mode
            if not await milk_mode(message, lower_message_content, last_user_message):
                return
        elif selected_reaction == '\U00002615':  # Coffee mode
            if not await coffee_mode(message, lower_message_content, last_user_message):
                return
        elif selected_reaction == '\U0001F378':  # Mojito mode
            if not await mojito_mode(message, lower_message_content):
                return
        elif selected_reaction == '\U0001F37B':  # Booze mode
            if not await booze_mode(message, lower_message_content):
                return
        await message.add_reaction(selected_reaction)
        last_user_message = message
        last_user_id = message.author.id
        used_words[lower_message_content] = True


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send('')


bot.run(os.getenv("TOKEN"))

input("Press Enter to exit...")
