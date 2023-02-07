import datetime
import re
import traceback
import discord
from discord.ext import commands
from discord import app_commands
import json
from cogs import utils
from views import gameSuggestionView
import math

class Commandes(commands.Cog, name='Commandes'):

    def __init__(self, client):
        self.client = client

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def post(self, ctx):
        await ctx.message.delete()
        await refresh_embeds(self.client, new=True, ctx=ctx)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def refresh(self, ctx):
        await ctx.message.delete()
        await refresh_embeds(self.client)



    @app_commands.command(name="jeu", description="Ajoute un jeu dans la liste de suggestions")
    async def addGame(self, interaction: discord.Interaction, game_name : str):
        """Ajoute un jeu dans la liste de suggestions"""
        print(f'{str(interaction.user)} a utilisé /Jeu et a ajouté le jeu {game_name}')
        self.client.jeux_coll.update_one({"Nom": "jeux"},
                                         {"$set": {game_name: {} }})
        await interaction.response.send_message(f'**{game_name}** a été ajouté', ephemeral=True)

        await refresh_embeds(self.client)


    @app_commands.command(name="enleverjeu", description="Enlève un jeu dans la liste de suggestions")
    async def removeGame(self, interaction: discord.Interaction):
        """Ajoute un jeu dans la liste de suggestions"""

        client = self.client

        # Select class
        class itemSelect(discord.ui.Select['itemSelect']):
            def __init__(self, options):
                super().__init__(options=options, placeholder="Jeux", min_values=1, max_values=len(options))
            async def callback(self, interaction: discord.Interaction):
                # remove selected items from document
                for game_name in self.values:
                    print(game_name)
                    client.jeux_coll.update_one({"Nom": "jeux"},
                                                     {"$unset": {game_name: 1 }})
                    await interaction.response.send_message(f'**{game_name}** a été retiré', ephemeral=True)
                    await refresh_embeds(client)


        select_options = []
        doc_jeux = self.client.jeux_coll.find_one({"Nom": "jeux"})
        del doc_jeux["Nom"]
        del doc_jeux["_id"]
        for game_name, users_object in doc_jeux.items():
            select_options.append(discord.SelectOption(label=game_name, value=game_name))

        select = itemSelect(select_options)
        view = discord.ui.View()
        view.add_item(select)
        view.message = await interaction.response.send_message("Choisir les jeux à retirer...", view=view, ephemeral=True)





async def setup(client):
    await client.add_cog(Commandes(client))
    print('Commandes cog is loaded')



async def refresh_embeds(client, new=False, ctx=None):
    """Refresh les 2 embeds selon les données courantes"""

    try:
        # Jeux courants
        embed_jeux_courants = discord.Embed(title="Jeux Courants", color=client.color)
        doc_jeux = client.jeux_coll.find_one({"Nom": "jeux"})
        del doc_jeux["Nom"]
        del doc_jeux["_id"]
        thereIsAnActiveGame = False
        desc_actifs = ''
        desc_attente = ''
        for game_name, users_object in doc_jeux.items():
            if len(users_object) >= 3:
                print(list(users_object.values()))
                print(list(users_object.values()).count(True) >= 3)
                if list(users_object.values()).count(True) >= 3: # Example: [True,True,False].count(True) = 2
                    thereIsAnActiveGame = True
                    # Mettre dans "actif"
                    desc_actifs += f'{game_name}  ('
                    for userid, isConfirmed in users_object.items():
                        if isConfirmed:
                            desc_actifs += f'<@{userid}> '
                    desc_actifs += ')\n'
                else:
                    # Mettre dans "En attente de confirmation"
                    desc_attente += f'{game_name}  ('
                    for userid, isConfirmed in users_object.items():
                        desc_attente += f'{"✅" if isConfirmed else ":question:"} <@{userid}> '
                    desc_attente += ')\n'
        if not thereIsAnActiveGame:
            desc_actifs = '*Aucun*'

        embed_jeux_courants.add_field(name=":runner: Actifs", value=desc_actifs, inline=False)
        if desc_attente:
            embed_jeux_courants.add_field(name=":timer: En attente de confirmation", value=desc_attente, inline=False)


        # Suggestions de jeux
        doc_jeux_classes = {k: v for k, v in sorted(doc_jeux.items(), key=lambda item: len(item[1]), reverse=True)} # Classer selon le jeu avec le plus d'intéressés (desc)
        desc = '\u200b\n'
        for game_name, users_object in doc_jeux_classes.items():
            desc += f':blue_circle: **{game_name}** ({len(users_object)} {"personne intéressée" if len(users_object) == 1 else "personnes intéressées"})\n'
            for userid, isConfirmed in users_object.items():
                desc += f'<@{userid}> '
            desc += '\n\n'

        desc += "\n*Pour voter pour un jeu, clique sur un bouton.*\n" \
                "*Pour retirer ton vote, clique une 2e fois sur le bouton.*\n" \
                "*Pour suggérer un jeu, utilise la commande **/Jeu***\n"
        embed_suggestions = discord.Embed(title=":memo: Suggestions de Jeux de groupe (coop, team-based, 3+ joueurs)", description=desc, color=client.color)


        if new:
            msg1 = await ctx.send(embed=embed_jeux_courants)
            view = gameSuggestionView.gameSuggestionView(client)
            msg2 = await ctx.send(embed=embed_suggestions, view=view)
            view.message = msg2

            client.jeux_coll.update_one({"Nom": "embeds"}, {"$set": {"embed_jeux_courants": msg1.id,
                                                                          "embed_suggestions": msg2.id,
                                                                          "channelid": ctx.channel.id,
                                                                          "guildid": ctx.guild.id}})

        else:
            document = client.jeux_coll.find_one({"Nom": "embeds"})
            id_embed_jeux_courants = document["embed_jeux_courants"]
            id_embed_suggestions = document["embed_suggestions"]

            guild = await client.fetch_guild(document["guildid"])
            channel = await guild.fetch_channel(document["channelid"])

            msg_jeux_courants = await channel.fetch_message(id_embed_jeux_courants)
            msg_suggestions = await channel.fetch_message(id_embed_suggestions)

            await msg_jeux_courants.edit(embed=embed_jeux_courants)
            view = gameSuggestionView.gameSuggestionView(client)
            await msg_suggestions.edit(embed=embed_suggestions, view=view)

    except:
        print(f'There was an error. Error log for Dev: ```{traceback.format_exc()}```')

