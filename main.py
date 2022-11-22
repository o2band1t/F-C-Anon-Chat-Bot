
import discord
from discord import ButtonStyle, Embed, Intents
from discord.ui import Button, View


### MADE TO BE USED IN 1 GUILD ONLY ###


### globals ###

# bot takes slash commands

intents = Intents.default()
intents.messages = True
intents.message_content = True
intents.reactions = True
intents.emojis_and_stickers = True
intents.members = True

bot = discord.Bot(intents=intents)

# stores ids of members who are in private anon convos 
# and maps each of them to the discord.Member object of their partner
convo_member_partner: dict[int, discord.Member] = {}

# stores all members in who are in private anon convos
convo_members: list[discord.Member] = []

# stores all request messages, each having a button with a callback containing the user id of the one who made them
# userid : [list of messages]
active_chat_req_messages: dict[int, list[discord.Message]] = {}

# stores all members with pending chat req messages
active_chat_req_members: list[discord.Member] = []

# stores all currently active DM channels for anon chats
active_dm_channels: list[discord.DMChannel] = []

# stores channels that chat request messages are sent to
chat_req_message_channels: list[discord.TextChannel] = []


### functions ###

async def del_req_messages(member):
	for message in active_chat_req_messages[member.id]:
		active_chat_req_messages[member.id].remove(message)
		await message.delete()
	del active_chat_req_messages[member.id]

async def send_req_messages(member):
	active_chat_req_messages[member.id] = []
	for channel in chat_req_message_channels:
		message = await channel.send(
			content='Someone wants to chat anonymously :)', 
			view=get_anon_chat_request_view(member))
		active_chat_req_messages[member.id].append(message)
		await message.delete(delay=1800) # del request message after 30 mins of no acceptance

def start_conversation(member1, member2):
	active_dm_channels.append(member1.dm_channel)
	active_dm_channels.append(member2.dm_channel)
	convo_member_partner[member1.id] = member2
	convo_member_partner[member2.id] = member1
	convo_members.append(member1)
	convo_members.append(member2)

def end_conversation(member1, member2):
	active_dm_channels.remove(member1.dm_channel)
	active_dm_channels.remove(member2.dm_channel)
	del convo_member_partner[member1.id]
	del convo_member_partner[member2.id]
	convo_members.remove(member1)
	convo_members.remove(member2)

def get_anon_chat_request_creator_view():
	view = View()
	btn_request = Button(
		style=ButtonStyle.green, 
		label='Request'
	)
	async def btn_request_callback(interaction):
		member = interaction.user
		if member in active_chat_req_members:
			await interaction.response.send_message(
				content='You already have a pending request.',
				ephemeral=True
			)
			return
		if member.dm_channel in active_dm_channels:
			await interaction.response.send_message(
				content='You can only be in one anon conversation at a time.',
				ephemeral=True
			)
			return
		active_chat_req_members.append(member)
		await send_req_messages(member)
	btn_request.callback = btn_request_callback
	btn_cancel = Button(
		style=ButtonStyle.red,
		label='Cancel'
	)
	async def btn_cancel_callback(interaction):
		member = interaction.user
		if member not in active_chat_req_members:
			await interaction.response.send_message(
				content='You do not have any pending requests.',
				ephemeral=True
			)
			return
		active_chat_req_members.remove(member)
		await del_req_messages(member)
	btn_cancel.callback = btn_cancel_callback
	view.add_item(btn_request)
	view.add_item(btn_cancel)
	return view

def get_anon_chat_request_view(member):
	view = View()
	button = Button(
		style=ButtonStyle.green,
		label='Start Chat'
	)
	async def callback(interaction):
		nonlocal member
		# return if member tries to accept own convo request
		if interaction.user.id == member.id:
			# ephemeral message here "you cannot start a convo with yourself"
			await interaction.response.send_message(
				content='You cannot start a private anon convo with yourself!',
				ephemeral=True
			)
			return
		embed = Embed(title='Say Hello!', description='A new conversation has started!')
		# create the DM channels using member.send if not existing yet
		await member.send(embed=embed)
		await interaction.user.send(embed=embed)
		start_conversation(member, interaction.user)
		await del_req_messages(member)
	button.callback = callback
	view.add_item(button)
	return view

def get_channel_by_name(channel_name):
	channel = [c for c in bot.guilds[0].text_channels if c.name == channel_name]
	if len(channel) == 0:
		return None
	return channel[0]


### commands ### 

@bot.command(description='(ADMIN ONLY) Show the channels that new anon chat requests will be sent to.')
async def show_chat_req_message_channels(ctx):
	if 'Council' not in [role.name for role in ctx.user.roles]:
		return
	desc = ', '.join([c.name for c in chat_req_message_channels])
	embed = Embed(title='Chat Request Message Channels', description=desc)
	await ctx.channel.send(embed=embed)

@bot.command(description='(ADMIN ONLY) Add a channel to the list of channels that receive new anon chat requests.')
async def add_chat_request_channel(ctx, channel_name):
	if 'Council' not in [role.name for role in ctx.user.roles]:
		return
	channel = get_channel_by_name(channel_name)
	if channel is None:
		desc = f'The channel, #{channel.name} was not found.'
		embed = Embed(title='Cannot Add Channel', description=desc)
		await ctx.channel.send(embed=embed)
		return
	if channel in chat_req_message_channels:
		desc = f'The channel, #{channel.name} is already in Chat Request Channels.'
		embed = Embed(title='Cannot Add Channel', description=desc)
		await ctx.channel.send(embed=embed)
		return
	chat_req_message_channels.append(channel)
	desc = f'You have successfully added #{channel_name} to the Chat Request Channels!'
	embed = Embed(title='Chat Request Channel Added', description=desc)
	await ctx.channel.send(embed=embed)

@bot.command(description='(ADMIN ONLY) Remove a channel from the list of channels that receive new anon chat requests.')
async def remove_chat_request_channel(ctx, chanel_name):
	if 'Council' not in [role.name for role in ctx.user.roles]:
		return
	channel = get_channel_by_name(channel_name)
	if channel is None:
		desc = f'The channel, #{channel.name} was not found.'
		embed = Embed(title='Cannot Remove Channel', description=desc)
		await ctx.channel.send(embed=embed)
		return
	if channel not in chat_req_message_channels:
		desc = f'The channel, #{channel.name} is not in Chat Request Channels.'
		embed = Embed(title='Cannot Remove Channel', description=desc)
		await ctx.channel.send(embed=embed)
		return
	desc = f'You have successfully removed #{channel_name} from the Chat Request Channels!'
	embed = Embed(title='Chat Request Message Channels', description=channels)
	await ctx.channel.send(embed=embed)

@bot.command(description='(ADMIN ONLY) Sends an Anon Chat Request Creator message to a channel.')
async def send_chat_request_creator(ctx, channel_name):
	if 'Council' not in [role.name for role in ctx.user.roles]:
		return
	channel = get_channel_by_name(channel_name)
	if channel is None:
		await ctx.respond(f'The channel with the name #{channel_name} was not found!')
		return
	await channel.send(
		content='Request an anonymous chat!',
		view=get_anon_chat_request_creator_view()
	)
	await ctx.respond(f'An Anon Chat Request Creator message was sent to #{channel_name}')

@bot.command(description='Ends the private anon conversation.')
async def goodbye(ctx):
	if ctx.channel.id not in [c.id for c in active_dm_channels]:
		return
	partner_channel = convo_member_partner[ctx.author.id].dm_channel
	end_conversation(ctx.author, convo_member_partner[ctx.author.id])
	embed = Embed(title='Thanks for chatting!', description='This conversation has ended.')
	await ctx.channel.send(embed=embed)
	await partner_channel.send(embed=embed)


### event listeners ###

@bot.event
async def on_ready():
	print('Bot is active!\n')

@bot.event
async def on_message(message):
	# ignore own messages
	if message.author == bot.user:
		return
	if message.channel not in active_dm_channels:
		return
	# limit number of attachments to 3
	if len(message.attachments) > 3:
		embed = Embed(
			title="Too many attachments!", 
			description="Please limit them to 3 at a time. Only the first 3 attachments were sent."
		)
		message.channel.send(embed=embed)
	files_to_send = [await a.to_file() for a in message.attachments[:3]]
	await convo_member_partner[message.author.id].send(content=message.content, files=files_to_send)

@bot.event
async def on_message_delete(message):
	# ignore if not own message
	if message.author.id != bot.user.id:
		return
	if message in active_chat_req_messages:
		active_chat_req_messages.remove(message)
		active_chat_req_members.remove(message.author)
		# if message was an active chat request message
		# then remove it from active_chat_req_messages, wherever it was in there


### running the bot ###

with open('bot_token.txt', 'r') as f:
	BOT_TOKEN = f.read()

bot.run(BOT_TOKEN)


