import asyncio
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

last_user_message = {}
last_user_id = {}
wordchain_channel_id = {}
used_words = {}
selected_reaction = {}
parity = {}
is_handling_violation = {}
user_message_count = {}
total_message_count = {}

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
- Jos uusi sana alkaa vokaalilla, sanan täytyy loppua konsonanttiin ja päinvastoin.
- Sanassa ei saa olla samaa kirjainta peräkkäin.
- Sanan pituus on oltava vähintään 5 kirjainta.

:champagne:  **Cham*__pain__* mode:**
- Seuraavan sanan tulee alkaa edellisen sanan kahdella viimeisellä kirjaimella.
- Joka toisen sanan merkkimäärä tulee olla on parillinen ja joka toisen pariton.
- Sanassa ei saa olla samaa kirjainta peräkkäin.
- Sanan pituus on oltava vähintään 5 kirjainta.
- Jos uusi sana alkaa vokaalilla, sanan täytyy loppua konsonanttiin ja päinvastoin.
-------------------------------------------------------------------------------
"""


async def handle_reactions(message):
    global selected_reaction, last_user_message
    emoji_list = ['\U0001F95B', '\U00002615', '\U0001F378', '\U0001F37B', '\U0001F37E']
    for emoji in emoji_list:
        await message.add_reaction(emoji)

    def check(reaction, user):
        return user != bot.user and reaction.message.id == message.id

    reaction, user = await bot.wait_for('reaction_add', check=check)
    guild_id = message.guild.id  # Hae palvelimen ID
    selected_reaction[guild_id] = reaction.emoji  # Päivitä valittu reaktio kyseisellä palvelimella
    if reaction.emoji == '\U0001F95B':
        await reaction.message.channel.send(f":milk:Selvä! Mennään helpolla.")
    elif reaction.emoji == '\U00002615':
        await reaction.message.channel.send(f':coffee: Liian väsynyt vaikeampaan?')
    elif reaction.emoji == '\U0001F378':
        await reaction.message.channel.send(f':cocktail:Jotain tujumpaa? Täältä pesee!')
    elif reaction.emoji == '\U0001F37B':
        await reaction.message.channel.send(f':beers: Tästä tuleekin mielenkiintoista!')
    elif reaction.emoji == '\U0001F37E':
        await reaction.message.channel.send(f':champagne: Älä juhli liian aikaisin! Tästä tulee vaikeaa...')


async def handle_rule_violation(channel):
    global last_user_id, used_words, last_user_message, selected_reaction, parity, is_handling_violation, \
        user_message_count, total_message_count
    guild_id = channel.guild.id  # Hae palvelimen ID
    is_handling_violation[guild_id] = True
    await channel.send(
        f"**Sääntöjä rikottu!** _Peli nollataan 10 sekunnin kuluttua..._")
    await asyncio.sleep(10)
    while True:
        deleted = await channel.purge(limit=100)
        if len(deleted) < 100:
            break
    await channel.purge()

    last_user_message[guild_id] = None
    last_user_id[guild_id] = None
    used_words[guild_id] = {}
    selected_reaction[guild_id] = None
    parity[guild_id] = 0
    user_message_count[guild_id] = 0
    total_message_count[guild_id] = 0

    new_message = await channel.send(on_ready_message)
    await new_message.pin()
    await handle_reactions(new_message)
    is_handling_violation[guild_id] = False


async def milk_mode(message, lower_message_content, last_user_message):
    guild_id = message.guild.id  # Hae palvelimen ID
    if (last_user_message[guild_id] is not None and lower_message_content[0]
            != last_user_message[guild_id].content[-1].lower()):
        await message.channel.send(f"Seuraavan sanan tulee alkaa edellisen sanan viimeisellä kirjaimella.")
        await handle_rule_violation(message.channel)
        return False
    return True


async def coffee_mode(message, lower_message_content, last_user_message):
    guild_id = message.guild.id  # Hae palvelimen ID
    if len(lower_message_content) < 4:
        await message.channel.send(f"Sanan pituus on oltava vähintään 4 kirjainta.")
        await handle_rule_violation(message.channel)
        return False
    if last_user_message[guild_id] is not None and lower_message_content[:2] != last_user_message[guild_id].content[
                                                                                -2:].lower():
        await message.channel.send(f"Seuraavan sanan tulee alkaa edellisen sanan kahdella viimeisellä kirjaimella.")
        await handle_rule_violation(message.channel)
        return False
    return True


async def mojito_mode(message, lower_message_content):
    global last_user_message, last_user_id, used_words, parity
    guild_id = message.guild.id  # Hae palvelimen ID
    if len(lower_message_content) < 4:
        await message.channel.send(f"Sanan pituus on oltava vähintään 4 kirjainta.")
        await handle_rule_violation(message.channel)
        return False
    if last_user_message[guild_id] is None:
        last_user_message[guild_id] = message
        last_user_id[guild_id] = message.author.id
        used_words[guild_id][lower_message_content] = True
        parity[guild_id] = 1 - len(lower_message_content) % 2
        return True
    else:
        if lower_message_content[:2] != last_user_message[guild_id].content[-2:].lower():
            await message.channel.send(f"Seuraavan sanan tulee alkaa edellisen sanan kahdella viimeisellä kirjaimella.")
            await handle_rule_violation(message.channel)
            return False
        if len(lower_message_content) % 2 != parity[guild_id]:
            await message.channel.send(
                f"Joka toisen sanan merkkimäärä tulee olla on parillinen ja joka toisen pariton.")
            await handle_rule_violation(message.channel)
            return False
    last_user_message[guild_id] = message
    last_user_id[guild_id] = message.author.id
    used_words[guild_id][lower_message_content] = True
    parity[guild_id] = 1 - parity[guild_id]
    return True


async def booze_mode(message, lower_message_content):
    global last_user_message, last_user_id, used_words, parity
    guild_id = message.guild.id  # Hae palvelimen ID
    vowels = 'aeiouyäö'
    if (lower_message_content[0] in vowels) == (lower_message_content[-1] in vowels):
        await message.channel.send(f"Jos sana alkaa vokaalilla, sen täytyy loppua konsonanttiin ja päinvastoin.")
        await handle_rule_violation(message.channel)
        return False
    if len(lower_message_content) < 5:
        await message.channel.send(f"Sanan pituus on oltava vähintään 5 kirjainta.")
        await handle_rule_violation(message.channel)
        return False
    if any(lower_message_content[i] == lower_message_content[i + 1] for i in range(len(lower_message_content) - 1)):
        await message.channel.send(f"Sanassa ei saa olla samaa kirjainta peräkkäin.")
        await handle_rule_violation(message.channel)
        return False
    if last_user_message[guild_id] is None:
        last_user_message[guild_id] = message
        last_user_id[guild_id] = message.author.id
        used_words[guild_id][lower_message_content] = True
        parity[guild_id] = 1 - len(lower_message_content) % 2
        return True
    else:
        if lower_message_content[:2] != last_user_message[guild_id].content[-2:].lower():
            await message.channel.send(f"Seuraavan sanan tulee alkaa edellisen sanan kahdella viimeisellä kirjaimella.")
            await handle_rule_violation(message.channel)
            return False
    last_user_message[guild_id] = message
    last_user_id[guild_id] = message.author.id
    used_words[guild_id][lower_message_content] = True
    parity[guild_id] = 1 - parity[guild_id]
    return True


async def champagne_mode(message, lower_message_content):
    global last_user_message, last_user_id, used_words, parity
    guild_id = message.guild.id  # Hae palvelimen ID
    vowels = 'aeiouyäö'
    if (lower_message_content[0] in vowels) == (lower_message_content[-1] in vowels):
        await message.channel.send(f"Jos sana alkaa vokaalilla, sen täytyy loppua konsonanttiin ja päinvastoin.")
        await handle_rule_violation(message.channel)
        return False
    if len(lower_message_content) < 5:
        await message.channel.send(f"Sanan pituus on oltava vähintään 5 kirjainta.")
        await handle_rule_violation(message.channel)
        return False
    if any(lower_message_content[i] == lower_message_content[i + 1] for i in range(len(lower_message_content) - 1)):
        await message.channel.send(f"Sanassa ei saa olla samaa kirjainta peräkkäin.")
        await handle_rule_violation(message.channel)
        return False
    if last_user_message[guild_id] is None:
        last_user_message[guild_id] = message
        last_user_id[guild_id] = message.author.id
        used_words[guild_id][lower_message_content] = True
        parity[guild_id] = 1 - len(lower_message_content) % 2
        return True
    else:
        if lower_message_content[:2] != last_user_message[guild_id].content[-2:].lower():
            await message.channel.send(f"Seuraavan sanan tulee alkaa edellisen sanan kahdella viimeisellä kirjaimella.")
            await handle_rule_violation(message.channel)
            return False
        if len(lower_message_content) % 2 != parity[guild_id]:
            await message.channel.send(
                f"Joka toisen sanan merkkimäärä tulee olla on parillinen ja joka toisen pariton.")
            await handle_rule_violation(message.channel)
            return False
    last_user_message[guild_id] = message
    last_user_id[guild_id] = message.author.id
    used_words[guild_id][lower_message_content] = True
    parity[guild_id] = 1 - parity[guild_id]
    return True


async def create_wordchain_channel(guild, existing_channel=None):
    global wordchain_channel_id
    if existing_channel:
        while True:
            deleted = await existing_channel.purge(limit=100)
            if len(deleted) < 100:
                break
        await existing_channel.purge()
    else:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(manage_channels=False, mention_everyone=False,
                                                            embed_links=False, attach_files=False,
                                                            view_channel=True, read_message_history=True,
                                                            read_messages=True),
            bot.user: discord.PermissionOverwrite(read_message_history=True, manage_messages=True,
                                                  send_messages=True,
                                                  read_messages=True, manage_channels=True)
        }
        existing_channel = await guild.create_text_channel("sanaketju", overwrites=overwrites)
    guild_id = guild.id  # Hae palvelimen ID
    wordchain_channel_id[guild_id] = existing_channel.id  # Tallenna kanavan ID kyseisen palvelimen alle
    message = await existing_channel.send(on_ready_message)
    await message.pin()

    # Luo tehtävä handle_reactions-funktiolle, joka suoritetaan taustalla
    asyncio.create_task(handle_reactions(message))


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    for guild in bot.guilds:
        print(f"Connected to server: {guild.name}, id: {guild.id}")
        existing_channel = discord.utils.get(guild.text_channels, name="sanaketju")
        await create_wordchain_channel(guild, existing_channel)


@bot.event
async def on_guild_join(guild):
    existing_channel = discord.utils.get(guild.text_channels, name="sanaketju")
    await create_wordchain_channel(guild, existing_channel)


@bot.event
async def on_guild_channel_delete(channel):
    global wordchain_channel_id
    guild_id = channel.guild.id  # Hae palvelimen ID
    if channel.id == wordchain_channel_id[guild_id]:  # Tarkista, onko poistettu kanava "sanaketju"-kanava
        await create_wordchain_channel(channel.guild)


@bot.event
async def on_message_delete(message):
    global last_user_message, wordchain_channel_id
    guild_id = message.guild.id  # Hae palvelimen ID
    if message.channel.id != wordchain_channel_id[guild_id]:  # Tarkista kanavan ID kyseisen palvelimen perusteella
        return
    if message == last_user_message[guild_id]:  # Tarkista viimeinen viesti kyseisen palvelimen perusteella
        await message.channel.send(
            f"Sana poistettu tai sitä on muokattu. Jatka Sanaketjua sanasta: '**{message.content}**'")
        last_user_message[guild_id] = None


@bot.event
async def on_message_edit(before, after):
    guild_id = before.guild.id  # Hae palvelimen ID
    if before.content != after.content and before.channel.id == wordchain_channel_id[guild_id]:
        await before.channel.send(
            f"Viestiä muokattu. Jatka Sanaketjua sanasta: '**{before.content}**'.")
        if before == last_user_message[guild_id]:  # Tarkista, onko muokattu viesti viimeinen viesti kyseisen
            # palvelimen perusteella
            last_user_message[guild_id] = after  # Päivitä viimeinen viesti kyseisen palvelimen perusteella


@bot.event
async def on_message(message):
    global last_user_message, wordchain_channel_id, last_user_id, used_words, selected_reaction, \
        is_handling_violation, user_message_count, total_message_count
    guild_id = message.guild.id  # Hae palvelimen ID

    if guild_id not in is_handling_violation:
        is_handling_violation[guild_id] = False
    if guild_id not in wordchain_channel_id:
        wordchain_channel_id[guild_id] = None
    if guild_id not in selected_reaction:
        selected_reaction[guild_id] = None
    if guild_id not in user_message_count:
        user_message_count[guild_id] = 0
    if guild_id not in total_message_count:
        total_message_count[guild_id] = 0
    if guild_id not in last_user_id:
        last_user_id[guild_id] = None
    if guild_id not in used_words:
        used_words[guild_id] = {}
    if guild_id not in last_user_message:
        last_user_message[guild_id] = None

    if is_handling_violation[guild_id]:  # Tarkista tila kyseisen palvelimen perusteella
        return
    if message.channel.id != wordchain_channel_id[guild_id] or selected_reaction[guild_id] is None:  # Tarkista
        # kanavan ID ja valittu reaktio kyseisen palvelimen perusteella
        return
    if message.author == bot.user:
        return
    if not message.author.bot:
        user_message_count[guild_id] += 1
        total_message_count[guild_id] += 1
        if user_message_count[guild_id] >= 10:
            await message.channel.send(f"**:chains::fire:{total_message_count[guild_id]} STREAK!!!:fire::chains:**")
            user_message_count[guild_id] = 0
        lower_message_content = message.content.lower()
        if not lower_message_content.isalpha():
            await message.channel.send(f"Sanasi ei saa sisältää numeroita tai erikoismerkkejä!")
            await handle_rule_violation(message.channel)
            return
        if last_user_id[guild_id] == message.author.id:
            await message.channel.send(f"Voit lähettää vain yhden sanan vuorollasi!")
            await handle_rule_violation(message.channel)
            return
        if lower_message_content in used_words[guild_id]:
            await message.channel.send(f"Sana **'{message.content}'** on jo käytetty!")
            await handle_rule_violation(message.channel)
            return
        if selected_reaction[guild_id] == '\U0001F95B':  # Milk mode
            if not await milk_mode(message, lower_message_content, last_user_message):
                return
        elif selected_reaction[guild_id] == '\U00002615':  # Coffee mode
            if not await coffee_mode(message, lower_message_content, last_user_message):
                return
        elif selected_reaction[guild_id] == '\U0001F378':  # Mojito mode
            if not await mojito_mode(message, lower_message_content):
                return
        elif selected_reaction[guild_id] == '\U0001F37B':  # Booze mode
            if not await booze_mode(message, lower_message_content):
                return
        elif selected_reaction[guild_id] == '\U0001F37E':  # Champagne mode
            if not await champagne_mode(message, lower_message_content):
                return
        await message.add_reaction(selected_reaction[guild_id])
        last_user_message[guild_id] = message
        last_user_id[guild_id] = message.author.id
        used_words[guild_id][lower_message_content] = True


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send('')


bot.run(os.getenv("TOKEN"))
