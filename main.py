import os
import asyncio
from discord.ext import commands
import discord
import json
from pymongo import MongoClient
from views import gameSuggestionView
from discord.ext.commands import Greedy, Context
from typing import Literal, Optional
with open("./config.json") as f: configData = json.load(f)

# Development or Production
inDev = configData["inDev"]

# Get environment variables
if inDev:
    with open("./auth.json") as f: authData = json.load(f)
    token = authData["Token"]
    cluster = MongoClient(authData["MongoClient"])
    jeux_collection = "dev_Jeux"

else:
    token = str(os.environ.get("DISCORD_TOKEN"))
    cluster = MongoClient(str(os.environ.get("MONGOCLIENT")))
    jeux_collection = "Jeux"


# Setup client
class PersistentViewBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix = configData["prefix"], intents = intents, case_insensitive=True, help_command=None)

    async def setup_hook(self) -> None:
        self.add_view(gameSuggestionView.gameSuggestionView(self))

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')


client = PersistentViewBot()
db = cluster["SuggestionsJeuxBot"]

#Set variables accessible in all cogs
client.jeux_coll = db[jeux_collection] # either Jeux or dev_Jeux
client.color = 0x1ABC9C #0x74d40c
client.prefix = configData["prefix"]



@client.command()
@commands.has_permissions(administrator=True)
async def reload(ctx, extension=None):
    if extension is None:
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await client.unload_extension(f'cogs.{filename[:-3]}')
                await client.load_extension(f'cogs.{filename[:-3]}')
                await ctx.send(f'Reloaded **{filename[:-3]}**!')
    else:
        await client.unload_extension(f'cogs.{extension}')
        await client.load_extension(f'cogs.{extension}')
        await ctx.send(f'Reloaded **{extension}**!')


async def load():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await client.load_extension(f'cogs.{filename[:-3]}')

async def main():
    await load()
    await  client.start(token)


@client.command()
@commands.guild_only()
@commands.has_permissions(administrator=True)
async def sync(
  ctx: Context, guilds: Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
    if not guilds:
        if spec == "~":
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "*":
            ctx.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "^":
            ctx.bot.tree.clear_commands(guild=ctx.guild)
            await ctx.bot.tree.sync(guild=ctx.guild)
            synced = []
        else:
            synced = await ctx.bot.tree.sync()

        await ctx.send(
            f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
        )
        return

    ret = 0
    for guild in guilds:
        try:
            await ctx.bot.tree.sync(guild=guild)
        except discord.HTTPException:
            pass
        else:
            ret += 1

    await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")


asyncio.run(main())