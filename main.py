import discord
import datetime
import asyncio
import configs


## INTENTS ## if an event from the API straight up isn't triggering a privileged intent probably needs to be enabled
intents = discord.Intents.default()
intents.members = True  # Be sure to enable this from the discord developer portal as well


## FUNCTIONS ##
def read_token():  # Read token from file token.txt and store as string
    with open("token.txt", "r") as f:
        lines = f.readlines()
        return lines[0].strip()


async def post_modlog(guild, kind, user=None, target=None, reason=None, author=None, channel=None, message=None, after=None):  # Create and post embed based on audit log info
    mod_log_channel = discord.utils.get(guild.text_channels, name=configs.MOD_LOG_CHANNEL_NAME)
    if not mod_log_channel:
        return
    e = discord.Embed(color=configs.MODLOG_COLORS[kind], timestamp=datetime.datetime.utcnow())
    e.set_author(name=str(kind.capitalize()))
    if target:
        e.add_field(name="Member", value=f"<@{str(target.id)}> ({str(target)})", inline=True)
    if user:
        e.add_field(name="Moderator", value=f"<@{str(user.id)}> ({str(user)})", inline=True)
    if reason:
        e.add_field(name="Reason", value=reason, inline=False)
    if author:
        e.add_field(name="Author", value=f"<@{str(author.id)}> ({str(author)})", inline=True)
    if channel:
        e.add_field(name="Channel", value=f"<#{str(channel.id)}>", inline=True)
    if message:
        if after:
            e.add_field(name="Before", value=message, inline=False)
            e.add_field(name="After", value=after, inline=False)
        else:
            e.add_field(name="Message", value=message, inline=False)
    await mod_log_channel.send(embed=e)


## GLOBAL VARIABLES ##
TOKEN = read_token()

client = discord.Client(intents=intents)


## EVENTS ##
@client.event
async def on_ready():  # Run as soon as the bot is logged in
    print('We have logged in as {0.user}'.format(client))


@client.event
async def on_message_delete(message):  # Run as soon as a message is deleted
    await post_modlog(guild=message .guild, kind="DELETE", author=message.author, channel=message.channel,
                      message=message.content, after=None)


@client.event
async def on_message_edit(before, after):  # Run as soon as a message is edited
    if before.content == after.content:  # Edit must be different (automatic link embedding sometimes triggers event)
        return
    await post_modlog(guild=before.guild, kind="EDIT", author=before.author, channel=before.channel,
                      message=before.content, after=after.content)


@client.event
async def on_member_ban(guild, user):  # Run as soon as a member is banned
    await asyncio.sleep(0.5)  # wait for audit log
    found_entry = None
    async for entry in guild.audit_logs(limit=50, action=discord.AuditLogAction.ban,
                                        after=datetime.datetime.utcnow() - datetime.timedelta(seconds=15),
                                        oldest_first=False):
        if entry.created_at < datetime.datetime.utcnow() - datetime.timedelta(seconds=10):
            continue
        if entry.target.id == user.id:
            found_entry = entry
            break
    if not found_entry:
        return
    await post_modlog(guild=guild, kind="BAN", user=found_entry.user, target=user, reason=found_entry.reason)


@client.event
async def on_member_unban(guild, usr):  # Run as soon as a member is unbanned
    await asyncio.sleep(0.5)  # wait for audit log
    found_entry = None
    async for entry in guild.audit_logs(limit=50, action=discord.AuditLogAction.unban,
                                        after=datetime.datetime.utcnow() - datetime.timedelta(seconds=15),
                                        oldest_first=False):
        if entry.created_at < datetime.datetime.utcnow() - datetime.timedelta(seconds=10):
            continue
        if entry.target.id == usr.id:
            found_entry = entry
            break
    if not found_entry:
        return
    await post_modlog(guild=guild, kind="UNBAN", user=found_entry.user, target=usr, reason=found_entry.reason)


@client.event
async def on_member_remove(user):  # Run as soon as a member is removed (either by kicking or leaving)
    await asyncio.sleep(0.5)  # wait for audit log
    found_entry = None
    async for entry in user.guild.audit_logs(limit=50, action=discord.AuditLogAction.ban,
                                             after=datetime.datetime.utcnow() - datetime.timedelta(seconds=15),
                                             oldest_first=False):
        if entry.created_at < datetime.datetime.utcnow() - datetime.timedelta(seconds=10):
            continue
        if entry.target.id == user.id:
            return
    async for entry in user.guild.audit_logs(limit=50, action=discord.AuditLogAction.kick,
                                             after=datetime.datetime.utcnow() - datetime.timedelta(seconds=10),
                                             oldest_first=False):   # 10 to prevent join-kick-join-leave false-positives
        if entry.created_at < datetime.datetime.utcnow() - datetime.timedelta(seconds=10):
            continue
        if entry.target.id == user.id:
            found_entry = entry
            break
    if not found_entry:
        await post_modlog(guild=user.guild, kind="LEAVE", target=user)
        return
    await post_modlog(guild=user.guild, kind="KICK", user=found_entry.user, target=user, reason=found_entry.reason)


@client.event
async def on_member_join(member):
    await post_modlog(guild=member.guild, kind="JOIN", target=member)


client.run(TOKEN)
