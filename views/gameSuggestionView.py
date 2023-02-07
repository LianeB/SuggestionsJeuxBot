from discord.ext import commands
import discord
from cogs import commandes
from views import YesNoView

# Define a simple View that gives us a confirmation menu
class gameSuggestionView(discord.ui.View):
    def __init__(self, client):
        super().__init__()
        self.value = None
        self.timeout = None
        self.client = client

        doc_jeux = self.client.jeux_coll.find_one({"Nom": "jeux"})
        del doc_jeux["Nom"]
        del doc_jeux["_id"]
        doc_jeux_classes = {k: v for k, v in sorted(doc_jeux.items(), key=lambda item: len(item[1]),
                                                    reverse=True)}  # Classer selon le jeu avec le plus d'intéressés (desc)
        for game_name, users_object in doc_jeux_classes.items():
            self.add_item(gameButton(label = game_name))




class gameButton(discord.ui.Button['gameButton']):
    def __init__(self, label):
        super().__init__(label=label, style=discord.ButtonStyle.blurple, custom_id=label)
        self.label = label

    # This function is called whenever the button is clicked
    async def callback(self, interaction: discord.Interaction):
        try:
            print(f'{str(interaction.user)} a cliqué sur le bouton {self.label}')

            label = ''
            for actionRow in interaction.message.components:
                for component in actionRow.children:
                    if component.type == discord.ComponentType.button and interaction.data["custom_id"] == component.custom_id:
                        label = component.label

            document = self.view.client.jeux_coll.find_one({"Nom": "jeux"})
            users_object = document[label]

            # if already in document, then remove the user
            if interaction.user.id in [int(key) for key in document[label].keys()]: #convert to int

                self.view.client.jeux_coll.update_one({"Nom": "jeux"},
                                                      {"$unset": {f'{label}.{interaction.user.id}': 1}})

                # if there was 3 people, notify the others that one lost interest
                if len(users_object) == 3:
                    for userid, isConfirmed in users_object.items():
                        if int(userid) != interaction.user.id:
                            member = await interaction.guild.fetch_member(int(userid))
                            try:
                                await member.send(f"<@{interaction.user.id}> n’est plus intéressé par **{label}**")
                            except:
                                print(f"Couldn't send DM to {str(member)}")

                            self.view.client.jeux_coll.update_one({"Nom": "jeux"},
                                                                  {"$set": {f'{label}.{userid}': False}})

                await interaction.response.defer()

            # Else add them
            else:

                # if the 3rd user
                if len(users_object) == 2: # the document is not refreshed, so these are the two other users
                    # send DM to the 2 other people
                    for userid, isConfirmed in users_object.items():
                        member = await interaction.guild.fetch_member(int(userid))
                        view = YesNoView.YesNoView(self.view.client, label)
                        try:
                            view.message = await member.send(f"**{label}** a reçu 3 votes! Es-tu toujours intéressé?", view=view)
                        except:
                            print(f"Couldn't send DM to {str(member)}")

                    self.view.client.jeux_coll.update_one({"Nom": "jeux"},
                                                          {"$set": {f'{label}.{interaction.user.id}': True}})


                # if 4th or more
                elif len(users_object) >= 3:
                    self.view.client.jeux_coll.update_one({"Nom": "jeux"},
                                                          {"$set": {f'{label}.{interaction.user.id}': True}})

                # un des deux premiers
                else:
                    self.view.client.jeux_coll.update_one({"Nom": "jeux"},
                                                          {"$set": {f'{label}.{interaction.user.id}': False}})

                await interaction.response.defer()

            await commandes.refresh_embeds(self.view.client)

        except:
            print(traceback.format_exc())
            await interaction.channel.send(f'There was an unexpected error. Error log for Dev: ```{traceback.format_exc()}```')