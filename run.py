from distutils.command.config import config
from pydoc import describe

import discord
import os

import texttable
from discord.ext import commands, tasks
from discord.ui import Button, View, Select
from discord import app_commands
import asyncio
import sys
from app.bot.helper.confighelper import ConfigHelper
import app.bot.helper.jellyfinhelper as jelly
from app.bot.helper.message import *
from requests import ConnectTimeout
from plexapi.myplex import MyPlexAccount
from app.bot.helper.migration.migration import upgrade_db
import app.bot.helper.database.JellyfinTable as JellyfinTable
import app.bot.helper.Utils as Utils

maxroles = 10
configHelper = ConfigHelper()

if not configHelper.config['discord_bot_token']:
    print("Missing Config.")
    sys.exit()

upgrade_db()

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
    while (value == None):
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
        plex_button = Button(label="Plex")
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
async def setupplex(interaction: discord.Interaction, username: str, password: str, server_name: str,
                    base_url: str = "", save_token: bool = True):
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
        configHelper.write_config("plex_base_url", plex._baseurl if base_url == "" else base_url, resync=False)
        configHelper.write_config("plex_token", plex._token, resync=False)

        # Delete old config entries
        configHelper.write_config("plex_user", "", resync=False)
        configHelper.write_config("plex_pass", "", resync=False)
        configHelper.write_config("plex_server_name", "", resync=False)
    else:
        # Save new config entries
        configHelper.write_config("plex_user", username, resync=False)
        configHelper.write_config("plex_pass", password, resync=False)
        configHelper.write_config("plex_server_name", server_name, resync=False)

        # Delete old config entries
        configHelper.write_config("plex_base_url", "", resync=False)
        configHelper.write_config("plex_token", "", resync=False)

    print("Plex authentication details updated. Restarting bot.")
    await interaction.followup.send(
        "Plex authentication details updated. Restarting bot. Please wait.\n", ephemeral=True)
    await reload()
    await interaction.followup.send("Bot successfully restarted.", ephemeral=True)


async def get_jellyfin_servers(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    servers = JellyfinTable.get_all_jellyfin_servers()
    return [
        app_commands.Choice(name=server, value=server) for server in servers if current.lower() in server.lower()
    ]


@jellyfin_commands.command(name="setuprole", description="Add or change a role to automatically add users to Jellyfin")
@app_commands.autocomplete(jellyfin_server=get_jellyfin_servers)
@app_commands.checks.has_permissions(administrator=True)
async def jellyrolesetup(interaction: discord.Interaction, role: discord.Role, jellyfin_server: str,
                         libraries: str = None):
    await interaction.response.defer()
    libraries = Utils.str_to_list(libraries)
    current_roles = JellyfinTable.get_jellyfin_roles(jellyfin_server)

    new_role = False
    if len(current_roles) <= maxroles and role.name not in current_roles:
        # Do not add roles multiple times.
        print(f"adding role {role.name} to jellyfin server {jellyfin_server}")
        JellyfinTable.add_jellyfin_role(jellyfin_server, role.name)
        new_role = True
    elif role.name not in current_roles:
        # why is there a max roles? lol.
        print("max roles reached")
        await embederror(interaction.followup, "Max number of roles reached for server.")
        return

    print(f"adding libraries {libraries} to jellyfin server {jellyfin_server} under role {role.name}")

    JellyfinTable.set_jellyfin_libraries(role.name, libraries)
    await interaction.followup.send(f"Role {'added' if new_role else 'updated'}", ephemeral=True)


@jellyfin_commands.command(name="removerole", description="Stop adding users with a role to Jellyfin")
@app_commands.autocomplete(jellyfin_server=get_jellyfin_servers)
@app_commands.checks.has_permissions(administrator=True)
async def jellyroleremove(interaction: discord.Interaction, jellyfin_server: str, role: discord.Role):
    if role.name not in JellyfinTable.get_jellyfin_roles(jellyfin_server):
        await embederror(interaction.response,
                         f"\"{role.name}\" is currently not a role for Jellyfin server {jellyfin_server}.")
        return
    JellyfinTable.remove_jellyfin_role(jellyfin_server, role)
    await interaction.response.send_message(
        f"Membarr will stop auto-adding \"{role.name}\" to Jellyfin server {jellyfin_server}",
        ephemeral=True, suppress_embeds=True)


@jellyfin_commands.command(name="viewsettings",
                           description="View all settings related to Jellyfin")
@app_commands.checks.has_permissions(administrator=True)
async def jellysettings(interaction: discord.Interaction):
    data = {}
    servers = JellyfinTable.get_all_jellyfin_servers(raw=True)

    count = 0
    for server in servers:
        data[server] = {}
        roles = JellyfinTable.get_jellyfin_roles(server[0])
        for role_name in roles:
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            data[server][role] = JellyfinTable.get_jellyfin_libraries(role_name)
            count += 1
    print(data)

    if count > 25:
        print("data too big.")
        pass
    else:
        embed = discord.Embed(title="Jellyfin Settings", description="All Jellyfin settings", color=0x00ff00)
        for server, roles in data.items():
            embed.add_field(
                name=f'**Server: {server[0]}**',
                value=f'*Enabled*: {server[2]}\n' +
                      (f'*External URL*: {server[3]}\n' if server[3] else '') +
                      ("\n".join([f"<@&{role.id}>: {', '.join(libraries)}" for role, libraries in roles.items()])),
                inline=False
            )

    await interaction.response.send_message(embed=embed, ephemeral=True)


@jellyfin_commands.command(name="setup", description="Setup Jellyfin server")
@app_commands.checks.has_permissions(administrator=True)
async def setupjelly(interaction: discord.Interaction, server_url: str, api_key: str, external_url: str = None):
    await interaction.response.defer()
    # get rid of trailing slashes
    server_url = server_url.rstrip('/')

    # add http:// if not present (lots of people forget this, so we'll do it for them)
    if (not server_url.startswith("http://") or server_url.startswith("https://")):
        server_url = "http://" + server_url

    # Test Jellyfin connection
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
            await embederror(interaction.followup,
                             "Unknown error occurred while connecting to Jellyfin. Check Membarr logs.")
    except ConnectTimeout as e:
        await embederror(interaction.followup,
                         "Connection to server timed out. Check that Jellyfin is online and reachable.")
        return
    except Exception as e:
        print("Exception while testing Jellyfin connection")
        print(type(e).__name__)
        print(e)
        await embederror(interaction.followup, "Unknown exception while connecting to Jellyfin. Check Membarr logs")
        return

    JellyfinTable.save_jellyfin_server(server_url, api_key, external_url if external_url else server_url, enabled=True)

    print("Jellyfin server URL and API key updated. Restarting bot.")
    await interaction.followup.send("Jellyfin server URL and API key updated. Restarting bot.", ephemeral=True)
    await reload()
    print("Bot has been restarted. Give it a few seconds.")

@jellyfin_commands.command(name="delete", description="Delete Jellyfin server")
@app_commands.autocomplete(jellyfin_server=get_jellyfin_servers)
@app_commands.checks.has_permissions(administrator=True)
async def deletejelly(interaction: discord.Interaction, jellyfin_server: str):
    JellyfinTable.delete_jellyfin_server(jellyfin_server)
    await interaction.response.send_message(f"Jellyfin server {jellyfin_server} has been deleted.",
                                            ephemeral=True, suppress_embeds=True)



@plex_commands.command(name="setuplibs", description="Setup libraries that new users can access")
@app_commands.checks.has_permissions(administrator=True)
async def setupplexlibs(interaction: discord.Interaction, libraries: str):
    if not libraries:
        await embederror(interaction.response, "libraries string is empty.")
        return
    else:
        # Do some fancy python to remove spaces from libraries string, but only where wanted.
        libraries = ",".join(list(map(lambda lib: lib.strip(), libraries.split(","))))
        configHelper.write_config("plex_libs", str(libraries))
        print("Plex libraries updated. Restarting bot. Please wait.")
        await interaction.response.send_message(
            "Jellyfin libraries updated. Please wait a few seconds for bot to restart.", ephemeral=True)
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


@jellyfin_commands.command(name="disable", description="Disable adding users to Jellyfin")
@app_commands.autocomplete(jellyfin_server=get_jellyfin_servers)
@app_commands.checks.has_permissions(administrator=True)
async def disablejellyfin(interaction: discord.Interaction, jellyfin_server: str):
    if not configHelper.config['jellyfin_enabled']:
        await interaction.response.send_message("Jellyfin already disabled.", ephemeral=True)
        return
    JellyfinTable.enable_server(jellyfin_server, False)
    print(f"Jellyfin server {jellyfin_server} disabled, reloading cogs")
    await reload()
    await interaction.response.send_message(f"Jellyfin server {jellyfin_server} disabled.",
                                            ephemeral=True, suppress_embeds=True)


bot.tree.add_command(plex_commands)
bot.tree.add_command(jellyfin_commands)

print(f"bot token: {configHelper.config['discord_bot_token']}")
bot.run(configHelper.config['discord_bot_token'])
