from distutils.command.config import config
from pydoc import describe
import discord
import os
from discord.ext import commands, tasks
from discord.utils import get
from discord.ui import Button, View, Select
from discord import app_commands
import asyncio
import sys
from app.bot.helper.confighelper import ConfigHelper
import app.bot.helper.jellyfinhelper as jelly
from app.bot.helper.message import *
from requests import ConnectTimeout
from plexapi.myplex import MyPlexAccount

maxroles = 10
configHelper = ConfigHelper()

if not configHelper.config['discord_bot_token']:
    print("Missing Config.")
    sys.exit()

class Bot(commands.Bot):
    def __init__(self) -> None:
        print("Initializing Discord bot")
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix=".", intents=intents)

    async def on_ready(self):
        print("Bot is online.")
        for guild in self.guilds:
            print("Syncing commands to " + guild.name)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
    
    async def on_guild_join(self, guild):
        print(f"Joined guild {guild.name}")
        print(f"Syncing commands to {guild.name}")
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
    
    async def setup_hook(self):
        print("Loading media server connectors")
        await self.load_extension(f'app.bot.cogs.app')

bot = Bot()

async def reload():
    await bot.reload_extension(f'app.bot.cogs.app')

async def getuser(interaction, server, type):
    value = None
    await interaction.user.send("Please reply with your {} {}:".format(server, type))
    while(value == None):
        def check(m):
            return m.author == interaction.user and not m.guild
        try:
            value = await bot.wait_for('message', timeout=200, check=check)
            return value.content
        except asyncio.TimeoutError:
            message = "Timed Out. Try again."
            return None

plex_commands = app_commands.Group(name="plexsettings", description="Membarr Plex commands")
jellyfin_commands = app_commands.Group(name="jellyfinsettings", description="Membarr Jellyfin commands")

@plex_commands.command(name="addrole", description="Add a role to automatically add users to Plex")
@app_commands.checks.has_permissions(administrator=True)
async def plexroleadd(interaction: discord.Interaction, role: discord.Role):
    if len(configHelper.config['plex_roles']) <= maxroles:
        # Do not add roles multiple times.
        if role.name in configHelper.config['plex_roles']:
            await embederror(interaction.response, f"Plex role \"{role.name}\" already added.")
            return

        configHelper.config['plex_roles'].append(role.name)
        saveroles = ",".join(configHelper.config['plex_roles'])
        plex_button = Button(label = "Plex")
        view = View()
        view.add_item(plex_button)
        configHelper.write_config("plex_roles", saveroles)
        await interaction.response.send_message("Updated Plex roles. Bot is restarting. Please wait.", ephemeral=True)
        print("Plex roles updated. Restarting bot, Give it a few seconds.")
        await reload()
        print("Bot has been restarted. Give it a few seconds.")

@plex_commands.command(name="removerole", description="Stop adding users with a role to Plex")
@app_commands.checks.has_permissions(administrator=True)
async def plexroleremove(interaction: discord.Interaction, role: discord.Role):
    if role.name not in configHelper.config['plex_roles']:
        await embederror(interaction.response, f"\"{role.name}\" is currently not a Plex role.")
        return
    configHelper.config['plex_roles'].remove(role.name)
    configHelper.write_config("jellyfin_roles", ",".join(configHelper.config['plex_roles']))
    await interaction.response.send_message(f"Membarr will stop auto-adding \"{role.name}\" to Plex", ephemeral=True)

@plex_commands.command(name="listroles", description="List all roles whose members will be automatically added to Plex")
@app_commands.checks.has_permissions(administrator=True)
async def plexrolels(interaction: discord.Interaction):
    await interaction.response.send_message(
        "The following roles are being automatically added to Plex:\n" +
        ", ".join(configHelper.config['plex_roles']), ephemeral=True
    )

@plex_commands.command(name="setup", description="Setup Plex integration")
@app_commands.checks.has_permissions(administrator=True)
async def setupplex(interaction: discord.Interaction, username: str, password: str, server_name: str, base_url: str = "", save_token: bool = True):
    await interaction.response.defer()
    try:
        account = MyPlexAccount(username, password)
        plex = account.resource(server_name).connect()
    except Exception as e:
        if str(e).startswith("(429)"):
            await embederror(interaction.followup, "You're being ratelimited by Plex! Please try again later.")
            return
        
        await embederror(interaction.followup, "Could not connect to Plex server. Please check your credentials.")
        return
    
    if (save_token):        
        # Save new config entries
        configHelper.write_config("plex_base_url", plex._baseurl if base_url == "" else base_url, resync = False)
        configHelper.write_config("plex_token", plex._token, resync = False)

        # Delete old config entries
        configHelper.write_config("plex_user", "", resync = False)
        configHelper.write_config("plex_pass", "", resync = False)
        configHelper.write_config("plex_server_name", "", resync = False)
    else:
        # Save new config entries
        configHelper.write_config("plex_user", username, resync = False)
        configHelper.write_config("plex_pass", password, resync = False)
        configHelper.write_config("plex_server_name", server_name, resync = False)

        # Delete old config entries
        configHelper.write_config("plex_base_url", "", resync = False)
        configHelper.write_config("plex_token", "", resync = False)


    print("Plex authentication details updated. Restarting bot.")
    await interaction.followup.send(
        "Plex authentication details updated. Restarting bot. Please wait.\n", ephemeral=True)
    await reload()
    await interaction.followup.send("Bot successfully restarted.", ephemeral=True)

@jellyfin_commands.command(name="addrole", description="Add a role to automatically add users to Jellyfin")           
@app_commands.checks.has_permissions(administrator=True)
async def jellyroleadd(interaction: discord.Interaction, role: discord.Role):
    if len(configHelper.config['jellyfin_roles']) <= maxroles:
        # Do not add roles multiple times.
        if role.name in configHelper.config['jellyfin_roles']:
            await embederror(interaction.response, f"Jellyfin role \"{role.name}\" already added.")
            return

        configHelper.config['jellyfin_roles'].append(role.name)
        saveroles = ",".join(configHelper.config['jellyfin_roles'])
        configHelper.write_config("jellyfin_roles", saveroles)
        await interaction.response.send_message("Updated Jellyfin roles. Bot is restarting. Please wait a few seconds.", ephemeral=True)
        print("Jellyfin roles updated. Restarting bot.")
        await reload()
        print("Bot has been restarted. Give it a few seconds.")

@jellyfin_commands.command(name="removerole", description="Stop adding users with a role to Jellyfin")
@app_commands.checks.has_permissions(administrator=True)
async def jellyroleremove(interaction: discord.Interaction, role: discord.Role):
    if role.name not in configHelper.config['jellyfin_roles']:
        await embederror(interaction.response, f"\"{role.name}\" is currently not a Jellyfin role.")
        return
    configHelper.config['jellyfin_roles'].remove(role.name)
    configHelper.write_config("jellyfin_roles", ",".join(configHelper.config['jellyfin_roles']))
    await interaction.response.send_message(f"Membarr will stop auto-adding \"{role.name}\" to Jellyfin", ephemeral=True)

@jellyfin_commands.command(name="listroles", description="List all roles whose members will be automatically added to Jellyfin")
@app_commands.checks.has_permissions(administrator=True)
async def jellyrolels(interaction: discord.Interaction):
    await interaction.response.send_message(
        "The following roles are being automatically added to Jellyfin:\n" +
        ", ".join(configHelper.config['jellyfin_roles']), ephemeral=True
    )

@jellyfin_commands.command(name="setup", description="Setup Jellyfin integration")
@app_commands.checks.has_permissions(administrator=True)
async def setupjelly(interaction: discord.Interaction, server_url: str, api_key: str, external_url: str = None):
    await interaction.response.defer()
    # get rid of training slashes
    server_url = server_url.rstrip('/')

    try:
        server_status = jelly.get_status(server_url, api_key)
        if server_status == 200:
            pass
        elif server_status == 401:
            # Unauthorized
            await embederror(interaction.followup, "API key provided is invalid")
            return
        elif server_status == 403:
            # Forbidden
            await embederror(interaction.followup, "API key provided does not have permissions")
            return
        elif server_status == 404:
            # page not found
            await embederror(interaction.followup, "Server endpoint provided was not found")
            return
        else:
            await embederror(interaction.followup, "Unknown error occurred while connecting to Jellyfin. Check Membarr logs.")
    except ConnectTimeout as e:
        await embederror(interaction.followup, "Connection to server timed out. Check that Jellyfin is online and reachable.")
        return
    except Exception as e:
        print("Exception while testing Jellyfin connection")
        print(type(e).__name__)
        print(e)
        await embederror(interaction.followup, "Unknown exception while connecting to Jellyfin. Check Membarr logs")
        return
    
    configHelper.write_config("jellyfin_server_url", str(server_url))
    configHelper.write_config("jellyfin_api_key", str(api_key))
    if external_url is not None:
        configHelper.write_config("jellyfin_external_url", str(external_url))
    else:
        configHelper.write_config("jellyfin_external_url", "")
    print("Jellyfin server URL and API key updated. Restarting bot.")
    await interaction.followup.send("Jellyfin server URL and API key updated. Restarting bot.", ephemeral=True)
    await reload()
    print("Bot has been restarted. Give it a few seconds.")


@plex_commands.command(name="setuplibs", description="Setup libraries that new users can access")
@app_commands.checks.has_permissions(administrator=True)
async def setupplexlibs(interaction: discord.Interaction, libraries:str):
    if not libraries:
        await embederror(interaction.response, "libraries string is empty.")
        return
    else:
        # Do some fancy python to remove spaces from libraries string, but only where wanted.
        libraries = ",".join(list(map(lambda lib: lib.strip(),libraries.split(","))))
        configHelper.write_config("plex_libs", str(libraries))
        print("Plex libraries updated. Restarting bot. Please wait.")
        await interaction.response.send_message("Jellyfin libraries updated. Please wait a few seconds for bot to restart.", ephemeral=True)
        await reload()
        print("Bot has been restarted. Give it a few seconds.")

@jellyfin_commands.command(name="setuplibs", description="Setup libraries that new users can access")
@app_commands.checks.has_permissions(administrator=True)
async def setupjellylibs(interaction: discord.Interaction, libraries:str):
    if not libraries is None:
        await embederror(interaction.response, "libraries string is empty.")
        return
    else:
        # Do some fancy python to remove spaces from libraries string, but only where wanted.
        libraries = ",".join(list(map(lambda lib: lib.strip(),libraries.split(","))))
        configHelper.write_config("jellyfin_libs", str(libraries))
        print("Jellyfin libraries updated. Restarting bot. Please wait.")
        await interaction.response.send_message("Jellyfin libraries updated. Please wait a few seconds for bot to restart.", ephemeral=True)
        await reload()
        print("Bot has been restarted. Give it a few seconds.")

# Enable / Disable Plex integration
@plex_commands.command(name="enable", description="Enable auto-adding users to Plex")
@app_commands.checks.has_permissions(administrator=True)
async def enableplex(interaction: discord.Interaction):
    if configHelper.config['plex_enabled']:
        await interaction.response.send_message("Plex already enabled.", ephemeral=True)
        return
    configHelper.write_config("plex_enabled", True)
    print("Plex enabled, reloading server")
    await reload()
    configHelper.config['plex_enabled'] = True
    await interaction.response.send_message("Plex enabled. Restarting server. Give it a few seconds.", ephemeral=True)
    print("Bot has restarted. Give it a few seconds.")

@plex_commands.command(name="disable", description="Disable adding users to Plex")
@app_commands.checks.has_permissions(administrator=True)
async def disableplex(interaction: discord.Interaction):
    if not configHelper.config['plex_enabled']:
        await interaction.response.send_message("Plex already disabled.", ephemeral=True)
        return
    configHelper.write_config("plex_enabled", False)
    print("Plex disabled, reloading server")
    await reload()
    configHelper.config['plex_enabled'] = False
    await interaction.response.send_message("Plex disabled. Restarting server. Give it a few seconds.", ephemeral=True)
    print("Bot has restarted. Give it a few seconds.")

# Enable / Disable Jellyfin integration
@jellyfin_commands.command(name="enable", description="Enable adding users to Jellyfin")
@app_commands.checks.has_permissions(administrator=True)
async def enablejellyfin(interaction: discord.Interaction):
    if configHelper.config['jellyfin_enabled']:
        await interaction.response.send_message("Jellyfin already enabled.", ephemeral=True)
        return
    configHelper.write_config("jellyfin_enabled", True)
    print("Jellyfin enabled, reloading server")
    configHelper.config['jellyfin_enabled'] = True
    await reload()
    await interaction.response.send_message("Jellyfin enabled. Restarting server. Give it a few seconds.", ephemeral=True)
    print("Bot has restarted. Give it a few seconds.")

@jellyfin_commands.command(name="disable", description = "Disable adding users to Jellyfin")
@app_commands.checks.has_permissions(administrator=True)
async def disablejellyfin(interaction: discord.Interaction):
    if not configHelper.config['jellyfin_enabled']:
        await interaction.response.send_message("Jellyfin already disabled.", ephemeral=True)
        return
    configHelper.write_config("jellyfin_enabled", False)
    print("Jellyfin disabled, reloading server")
    await reload()
    configHelper.config['jellyfin_enabled'] = False
    await interaction.response.send_message("Jellyfin disabled. Restarting server. Give it a few seconds.", ephemeral=True)
    print("Bot has restarted. Give it a few seconds.")


bot.tree.add_command(plex_commands)
bot.tree.add_command(jellyfin_commands)

print(f"bot token: {configHelper.config['discord_bot_token']}")
bot.run(configHelper.config['discord_bot_token'])