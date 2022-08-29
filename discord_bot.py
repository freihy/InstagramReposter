import discord
import json
import re
import pathlib
import firebase_admin
import os
from firebase_admin import db
from discord.ext import tasks
from Grabber import InstaGrabber

# Load from json
setup_configs = json.load(open('config.json'))
discord_configs = setup_configs["discord"]
instagram_configs = setup_configs["instagram"]
fp_dir = instagram_configs["first_post_directory_name"]
firebase_certificate = json.load(setup_configs["firebase"]["certificate_json"])
firebase_cred = json.load(setup_configs["firebase"]["cred_obj"])

# Firebase initial setup and linking to cloud account
cred_obj = firebase_admin.credentials.Certificate(firebase_certificate)
default_app = firebase_admin.initialize_app(cred_obj, {
    'databaseURL': firebase_cred
    })

# Firebase realtime database reference
ref = db.reference("/")

# Initialise InstaGrabber
while True:
    try:
        igg = InstaGrabber()
        break
    except:
        print('Failed to login to dummy account, retrying...')

# Bot setup and variables
TOKEN = discord_configs["token"]
PREFIX = discord_configs["prefix"]
MINS = discord_configs["refresh"]

client = discord.Client()

def posted(shortcode: str) -> bool:
    try:
        database_retrived = ref.get()
        return database_retrived["shortcode"] == shortcode
    except:
        return False

'''
Log on command
'''
@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def check_and_post(bypass: bool = False, force_channel: int = None):
    image_video_formats = ['jpg', 'png', 'webp', 'webm', 'mp4']
    first_post = igg.get_first_post()
    all_post = igg.get_all_post()
    database_retrived = ref.get()

    # Retrieve all possible posts.
    while True:
        post = next(all_post)

        print(f'Post: {post.shortcode}')
        # If the recent most updated post has been reached, break
        if post.shortcode == database_retrived["shortcode"]:
            break

        if not posted(post.shortcode) or bypass:
            if bypass and posted(post.shortcode):
                print("Force reposting! Bewarned of duplicates!")
            elif not bypass and not posted(post.shortcode):
                print("New post found! Reposting...")
            igg.save_post(post, post.url)   

            # Find all media files
            media_file = None
            path_folder = pathlib.Path(fp_dir).iterdir()
            for path in path_folder:
                if path.is_file() and path.name[:-len(path.suffix)] == 'first_post' and path.suffix[1:] in image_video_formats:
                    media_file = path.name # Favour video files
                    if path.suffix[1:] in ['mp4', 'webm']:
                        break

            # Get all hashtags
            # Find a hashtag that corresponds to the correct discord channel
            try:
                hashtags = re.findall(r'(#.*$)', post.caption)[0].split(" ")
            except:
                hashtags = [] # You forgot the hastag!
                print("There's no hashtags!")
            channel_id = None
            for i in range(len(hashtags)):
                try:
                    channel_id = discord_configs["channel_ids"][hashtags[i]]
                except KeyError:
                    pass

            # If we can't find one, use the default
            if channel_id == None:
                print('All hashtags are invalid, using default channel!')
                channel_id = discord_configs["channel_ids"]["default"]

            # Send the post on the chosen channel
            if force_channel == None:
                designated_channel = client.get_channel(channel_id)
            else:
                designated_channel = client.get_channel(force_channel)
            with open(f'{fp_dir}/{media_file}', 'rb') as f:
                picture = discord.File(f)
                # Creates an embed container for the message
                embed=discord.Embed(title="@musa.soit",
                                    url="https://www.instagram.com/p/" + str(post.shortcode),
                                    description=str(post.caption),
                                    color=discord.Color.blue(), image=picture)
                try:
                    await designated_channel.send(file=picture, embed=embed)
                except:
                    await designated_channel.send(embed=embed)
                f.close()

            # Write the post shortcode into cloud storage (firebase)
            print(f'{post.shortcode} posted!')
            
        else:
            print(f'No new post found, waiting another {MINS} minutes.')

    # Write the post shortcode into cloud storage (firebase)
    # After all posts have been posted, update the short code to the newest post
    ref.set({'shortcode': first_post.shortcode})
    print("All post have been posted and shortcode updated")

'''
Responding to messages
'''
@client.event
async def on_message(message):
    username = str(message.author).split('#')[0]
    raw_user_message = str(message.content)
    channel = str(message.channel.name)

    # Prevent loopback
    if message.author == client.user:
        return

    if raw_user_message[:1] == PREFIX:
        content = raw_user_message[1:].split(" ")
        action = content[0]

        # Ping test
        if action == "ping":
            await message.channel.send("pong")

        # Force bot to repost the latest post on the instagram account
        if action == "newpost":
            try:
                force_channel = int(content[1])
                await check_and_post(True, force_channel)
            except IndexError:
                await check_and_post(bypass=True)

        if action == "change_mem_shortcode":
            try:
                code = content[1]
                ref.set({'shortcode': code})
                print("Changed")
            except IndexError:
                await message.channel.send("Shortcode empty")
            


@tasks.loop(minutes=MINS)
async def do_tasks():
    await check_and_post()

@do_tasks.before_loop
async def my_background_task_before_loop():
    await client.wait_until_ready()
do_tasks.start()

client.run(TOKEN)