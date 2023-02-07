from discord.ext import commands
import discord
from cogs import commandes

# Define a simple View that gives us a confirmation menu
class YesNoView(discord.ui.View):
    def __init__(self, client, gameName):
        super().__init__()
        self.value = None
        self.timeout = None
        self.client = client
        self.gameName = gameName


    # Grey out on timeout
    #async def on_timeout(self) -> None:
    #    await self.disable_buttons()


    async def disable_buttons(self):
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)


    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Oui', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f'{str(interaction.user)} a répondu "Oui" pour son intérêt pour {self.gameName} en DMs')
        await interaction.response.send_message('✅ Merci pour la confirmation')
        self.value = True
        self.stop()
        await self.disable_buttons()
        self.client.jeux_coll.update_one({"Nom": "jeux"},
                                         {"$set": {f'{self.gameName}.{interaction.user.id}': True}})

        await commandes.refresh_embeds(self.client)

        # Si 3 votes, notifier tout le monde que le jeu est actif
        document = self.client.jeux_coll.find_one({"Nom": "jeux"})
        users_object = document[self.gameName]
        if list(users_object.values()).count(True) >= 3:
            for userid, isConfirmed in users_object.items():
                doc = self.client.jeux_coll.find_one({"Nom": "embeds"})
                guild = await self.client.fetch_guild(doc["guildid"])
                member = await guild.fetch_member(int(userid))
                try:
                    await member.send(f"**{self.gameName}** a reçu assez d'intérêt et est maintenant actif")
                except:
                    print(f"Couldn't send DM to {str(member)}")





    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='Non', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f'{str(interaction.user)} a répondu "Non" pour son intérêt pour {self.gameName} en DMs')
        await interaction.response.send_message('Merci. Ton intérêt pour ce jeu a été retiré.')
        self.value = False
        self.stop()
        await self.disable_buttons()
        self.client.jeux_coll.update_one({"Nom": "jeux"},
                                         {"$unset": {f'{self.gameName}.{interaction.user.id}': 1 }})
        await commandes.refresh_embeds(self.client)

        # S'il reste 2 joueurs, mettre leur intérêt à False
        document = self.client.jeux_coll.find_one({"Nom": "jeux"})
        users_object = document[self.gameName]
        if len(users_object) == 2:
            for userid, isConfirmed in users_object.items():
                doc = self.client.jeux_coll.find_one({"Nom": "embeds"})
                guild = await self.client.fetch_guild(doc["guildid"])
                member = await guild.fetch_member(int(userid))
                member_that_answered_No = await guild.fetch_member(interaction.user.id)
                try:
                    await member.send(f"**{member_that_answered_No.mention}** n'est plus intéressé par **{self.gameName}**")
                except:
                    print(f"Couldn't send DM to {str(member)}")

                self.client.jeux_coll.update_one({"Nom": "jeux"},
                                                 {"$set": {f'{self.gameName}.{userid}': False}})