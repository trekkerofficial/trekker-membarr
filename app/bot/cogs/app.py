from pickle import FALSE
import app.bot.helper.jellyfinhelper as jelly
from app.bot.helper.textformat import bcolors
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer
import app.bot.helper.db as db
import app.bot.helper.plexhelper as plexhelper
import app.bot.helper.jellyfinhelper as jelly
import texttable
from app.bot.helper.message import *
from app.bot.helper.confighelper import ConfigHelper
import app.bot.helper.database.JellyfinTable as JellyfinTable

MEMBARR_VERSION = 2.0
configHelper = ConfigHelper()
config = ConfigHelper.config
print (f"plex enabled: {config['plex_enabled']} plex configured: {configHelper.plex_configured}")
if config['plex_enabled'] and configHelper.plex_configured:
    try:
        print("Connecting to Plex......")
        if configHelper.plex_token_configured:
            print("Using Plex auth token to connect to Plex")
            plex = PlexServer(config['plex_base_url'], config['plex_token'])
        else:
            print("Using Plex login info to connect to Plex (This is deprecated. Rerun the /plexsettings setup command to use Plex tokens instead.)")
            account = MyPlexAccount(config['plex_user'], config['plex_pass'])
            plex = account.resource(config['plex_server_name']).connect()  # returns a PlexServer instance
        print('Logged into Plex!')
    except Exception as e:
        # probably rate limited.
        print('Error with plex login. Please check Plex authentication details. If you have restarted the bot multiple times recently, this is most likely due to being ratelimited on the Plex API. Try again in 10 minutes.')
        print(f'Error: {e}')
else:
    print(f"Plex {'disabled' if not config['plex_enabled'] else 'not configured'}. Skipping Plex login.")


class app(commands.Cog):
    # App command groups
    plex_commands = app_commands.Group(name="plex", description="Membarr Plex commands")
    jellyfin_commands = app_commands.Group(name="jellyfin", description="Membarr Jellyfin commands")
    membarr_commands = app_commands.Group(name="membarr", description="Membarr general commands")

    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        print('------')
        print("{:^41}".format(f"MEMBARR V {MEMBARR_VERSION}"))
        print(f'Made by Yoruio https://github.com/Yoruio/\n')
        print(f'Forked from Invitarr https://github.com/Sleepingpirates/Invitarr')
        print(f'Logged in as {self.bot.user} (ID: {self.bot.user.id})')
        print('------')

    
    async def getemail(self, after):
        email = None
        await embedinfo(after, f'Welcome To {config["plex_server_name"]}. Just reply with your email so we can add you to Plex!')
        await embedinfo(after,'I will wait 24 hours for your message, if you do not send it by then I will cancel the command.')
        while(email == None):
            def check(m):
                return m.author == after and not m.guild
            try:
                email = await self.bot.wait_for('message', timeout=86400, check=check)
                if(plexhelper.verifyemail(str(email.content))):
                    return str(email.content)
                else:
                    email = None
                    message = "Invalid email. Please just type in your email and nothing else."
                    await embederror(after, message)
                    continue
            except asyncio.TimeoutError:
                message = "Timed Out. Message Server Admin with your email so They Can Add You Manually."
                await embederror(after, message)
                return None
    
    async def getusername(self, after):
        username = None
        await embedinfo(after, f"Welcome To Jellyfin! Just reply with a username for Jellyfin so we can add you!")
        await embedinfo(after, f"I will wait 24 hours for your message, if you do not send it by then I will cancel the command.")
        while (username is None):
            def check(m):
                return m.author == after and not m.guild
            try:
                username = await self.bot.wait_for('message', timeout=86400, check=check)
                if(jelly.verify_username(config['jellyfin_server_url'], config['jellyfin_api_key'], str(username.content))):
                    return str(username.content)
                else:
                    username = None
                    message = "This username is taken. Please select another Username."
                    await embederror(after, message)
                    continue
            except asyncio.TimeoutError:
                message = "Timed Out. Message Server Admin with your preferred username so They Can Add You Manually."
                print("Jellyfin user prompt timed out")
                await embederror(after, message)
                return None
            except Exception as e:
                await embederror(after, "Something went wrong. Please try again with another username.")
                print (e)
                username = None


    async def addtoplex(self, email, response):
        if(plexhelper.verifyemail(email)):
            if plexhelper.plexadd(plex, email, config['plex_libs']):
                await embedinfo(response, 'This email address has been added to plex')
                return True
            else:
                await embederror(response, 'There was an error adding this email address. Check logs.')
                return False
        else:
            await embederror(response, 'Invalid email.')
            return False

    async def removefromplex(self, email, response):
        if(plexhelper.verifyemail(email)):
            if plexhelper.plexremove(plex,email):
                await embedinfo(response, 'This email address has been removed from plex.')
                return True
            else:
                await embederror(response, 'There was an error removing this email address. Check logs.')
                return False
        else:
            await embederror(response, 'Invalid email.')
            return False
    
    async def addtojellyfin(self, username, password, response):
        if not jelly.verify_username(config['jellyfin_server_url'], config['jellyfin_api_key'], username):
            await embederror(response, f'An account with username {username} already exists.')
            return False

        if jelly.add_user(config['jellyfin_server_url'], config['jellyfin_api_key'], username, password, config['jellyfin_libs']):
            return True
        else:
            await embederror(response, 'There was an error adding this user to Jellyfin. Check logs for more info.')
            return False

    async def removefromjellyfin(self, username, response):
        if jelly.verify_username(config['jellyfin_server_url'], config['jellyfin_api_key'], username):
            await embederror(response, f'Could not find account with username {username}.')
            return
        
        if jelly.remove_user(config['jellyfin_server_url'], config['jellyfin_api_key'], username):
            await embedinfo(response, f'Successfully removed user {username} from Jellyfin.')
            return True
        else:
            await embederror(response, f'There was an error removing this user from Jellyfin. Check logs for more info.')
            return False

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if config['plex_roles'] is None and config['jellyfin_roles'] is None:
            return

        roles_in_guild = after.guild.roles
        role = None

        plex_processed = False
        jellyfin_processed = False

        # Check Plex roles
        if configHelper.plex_configured and config['plex_enabled']:
            for role_for_app in config['plex_roles']:
                for role_in_guild in roles_in_guild:
                    if role_in_guild.name == role_for_app:
                        role = role_in_guild

                    # Plex role was added
                    if role is not None and (role in after.roles and role not in before.roles):
                        email = await self.getemail(after)
                        if email is not None:
                            await embedinfo(after, "Got it we will be adding your email to plex shortly!")
                            if plexhelper.plexadd(plex, email, config['plex_libs']):
                                db.save_user_email(str(after.id), email)
                                await asyncio.sleep(5)
                                await embedinfo(after, 'You have Been Added To Plex! Login to plex and accept the invite!')
                            else:
                                await embedinfo(after, 'There was an error adding this email address. Message Server Admin.')
                        plex_processed = True
                        break

                    # Plex role was removed
                    elif role is not None and (role not in after.roles and role in before.roles):
                        try:
                            user_id = after.id
                            email = db.get_useremail(user_id)
                            plexhelper.plexremove(plex, email)
                            deleted = db.remove_email(user_id)
                            if deleted:
                                print("Removed Plex email {} from db".format(after.name))
                                #await secure.send(plexname + ' ' + after.mention + ' was removed from plex')
                            else:
                                print("Cannot remove Plex from this user.")
                            await embedinfo(after, "You have been removed from Plex")
                        except Exception as e:
                            print(e)
                            print("{} Cannot remove this user from plex.".format(email))
                        plex_processed = True
                        break
                if plex_processed:
                    break

        role = None
        # Check Jellyfin roles
        for role_for_app in JellyfinTable.get_jellyfin_roles():
            for role_in_guild in roles_in_guild:
                if role_in_guild.name == role_for_app:
                    role = role_in_guild

                # Jellyfin role was added
                if role is not None and (role in after.roles and role not in before.roles):
                    print("Jellyfin role added")
                    username = await self.getusername(after)
                    print("Username retrieved from user")
                    if username is not None:
                        await embedinfo(after, "Got it we will be creating your Jellyfin account shortly!")
                        password = jelly.generate_password(16)
                        if jelly.add_user(config['jellyfin_server_url'], config['jellyfin_api_key'], username, password, config['jellyfin_libs']):
                            db.save_user_jellyfin(str(after.id), username)
                            await asyncio.sleep(5)
                            await embedcustom(after, "You have been added to Jellyfin!", {'Username': username, 'Password': f"||{password}||"})
                            await embedinfo(after, f"Go to {config['jellyfin_external_url']} to log in!")
                        else:
                            await embedinfo(after, 'There was an error adding this user to Jellyfin. Message Server Admin.')
                    jellyfin_processed = True
                    break

                # Jellyfin role was removed
                elif role is not None and (role not in after.roles and role in before.roles):
                    print("Jellyfin role removed")
                    try:
                        user_id = after.id
                        username = db.get_jellyfin_username(user_id)
                        jelly.remove_user(config['jellyfin_server_url'], config['jellyfin_api_key'], username)
                        deleted = db.remove_jellyfin(user_id)
                        if deleted:
                            print("Removed Jellyfin from {}".format(after.name))
                            #await secure.send(plexname + ' ' + after.mention + ' was removed from plex')
                        else:
                            print("Cannot remove Jellyfin from this user")
                        await embedinfo(after, "You have been removed from Jellyfin")
                    except Exception as e:
                        print(e)
                        print("{} Cannot remove this user from Jellyfin.".format(username))
                    jellyfin_processed = True
                    break
            if jellyfin_processed:
                break

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if config['plex_enabled'] and configHelper.plex_configured:
            email = db.get_useremail(member.id)
            plexhelper.plexremove(plex,email)
        
        if config['jellyfin_enabled'] and configHelper.jellyfin_configured:
            jellyfin_username = db.get_jellyfin_username(member.id)
            jelly.remove_user(config['jellyfin_server_url'], config['jellyfin_api_key'], jellyfin_username)
            
        deleted = db.delete_user(member.id)
        if deleted:
            print("Removed {} from db because user left discord server.".format(email))

    @app_commands.checks.has_permissions(administrator=True)
    @plex_commands.command(name="invite", description="Invite a user to Plex")
    async def plexinvite(self, interaction: discord.Interaction, email: str):
        await self.addtoplex(email, interaction.response)
    
    @app_commands.checks.has_permissions(administrator=True)
    @plex_commands.command(name="remove", description="Remove a user from Plex")
    async def plexremove(self, interaction: discord.Interaction, email: str):
        await self.removefromplex(email, interaction.response)
    
    @app_commands.checks.has_permissions(administrator=True)
    @jellyfin_commands.command(name="invite", description="Invite a user to Jellyfin")
    async def jellyfininvite(self, interaction: discord.Interaction, username: str):
        password = jelly.generate_password(16)
        if await self.addtojellyfin(username, password, interaction.response):
            await embedcustom(interaction.response, "Jellyfin user created!", {'Username': username, 'Password': f"||{password}||"})

    @app_commands.checks.has_permissions(administrator=True)
    @jellyfin_commands.command(name="remove", description="Remove a user from Jellyfin")
    async def jellyfinremove(self, interaction: discord.Interaction, username: str):
        await self.removefromjellyfin(username, interaction.response)
    
    @app_commands.checks.has_permissions(administrator=True)
    @membarr_commands.command(name="dbadd", description="Add a user to the Membarr database")
    async def dbadd(self, interaction: discord.Interaction, member: discord.Member, email: str = "", jellyfin_username: str = ""):
        email = email.strip()
        jellyfin_username = jellyfin_username.strip()
        
        # Check email if provided
        if email and not plexhelper.verifyemail(email):
            await embederror(interaction.response, "Invalid email.")
            return

        try:
            db.save_user_all(str(member.id), email, jellyfin_username)
            await embedinfo(interaction.response,'User was added to the database.')
        except Exception as e:
            await embedinfo(interaction.response, 'There was an error adding this user to database. Check Membarr logs for more info')
            print(e)

    @app_commands.checks.has_permissions(administrator=True)
    @membarr_commands.command(name="dbls", description="View Membarr database")
    async def dbls(self, interaction: discord.Interaction):

        embed = discord.Embed(title='Membarr Database.')
        all = db.read_all()
        table = texttable.Texttable()
        table.set_cols_dtype(["t", "t", "t", "t"])
        table.set_cols_align(["c", "c", "c", "c"])
        header = ("#", "Name", "Email", "Jellyfin")
        table.add_row(header)
        for index, peoples in enumerate(all):
            index = index + 1
            id = int(peoples[1])
            dbuser = self.bot.get_user(id)
            dbemail = peoples[2] if peoples[2] else "No Plex"
            dbjellyfin = peoples[3] if peoples[3] else "No Jellyfin"
            try:
                username = dbuser.name
            except:
                username = "User Not Found."
            embed.add_field(name=f"**{index}. {username}**", value=dbemail+'\n'+dbjellyfin+'\n', inline=False)
            table.add_row((index, username, dbemail, dbjellyfin))
        
        total = str(len(all))
        if(len(all)>25):
            f = open("db.txt", "w")
            f.write(table.draw())
            f.close()
            await interaction.response.send_message("Database too large! Total: {total}".format(total = total),file=discord.File('db.txt'), ephemeral=True)
        else:
            await interaction.response.send_message(embed = embed, ephemeral=True)
        
            
    @app_commands.checks.has_permissions(administrator=True)
    @membarr_commands.command(name="dbrm", description="Remove user from Membarr database")
    async def dbrm(self, interaction: discord.Interaction, position: int):
        embed = discord.Embed(title='Membarr Database.')
        all = db.read_all()
        for index, peoples in enumerate(all):
            index = index + 1
            id = int(peoples[1])
            dbuser = self.bot.get_user(id)
            dbemail = peoples[2] if peoples[2] else "No Plex"
            dbjellyfin = peoples[3] if peoples[3] else "No Jellyfin"
            try:
                username = dbuser.name
            except:
                username = "User Not Found."
            embed.add_field(name=f"**{index}. {username}**", value=dbemail+'\n'+dbjellyfin+'\n', inline=False)

        try:
            position = int(position) - 1
            id = all[position][1]
            discord_user = await self.bot.fetch_user(id)
            username = discord_user.name
            deleted = db.delete_user(id)
            if deleted:
                print("Removed {} from db".format(username))
                await embedinfo(interaction.response,"Removed {} from db".format(username))
            else:
                await embederror(interaction.response,"Cannot remove this user from db.")
        except Exception as e:
            print(e)

async def setup(bot):
    await bot.add_cog(app(bot))
