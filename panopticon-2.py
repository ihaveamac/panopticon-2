#!/usr/bin/env python3

# This file is a part of panopticon-2.
#
# Copyright (c) 2019 Ian Burgwin
# This file is licensed under The MIT License (MIT).
# You can find the full license text in LICENSE.md in the root of this project.

import asyncio
import json
from configparser import ConfigParser
from datetime import datetime

import disnake
import aiopg
import psycopg2

user_query = '''INSERT INTO users VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (user_id) DO UPDATE
                   SET name = EXCLUDED.name,
                   discriminator = EXCLUDED.discriminator,
                   last_updated = NOW()'''

guild_query = '''INSERT INTO guilds VALUES (%s, %s)
                    ON CONFLICT (guild_id) DO UPDATE
                    SET name = EXCLUDED.name,
                    last_updated = NOW()'''

private_channel_query = '''INSERT INTO private_channels VALUES (%s, %s, %s)
                             ON CONFLICT (channel_id) DO NOTHING'''
guild_channel_query = '''INSERT INTO guild_channels VALUES (%s, %s, %s)
                           ON CONFLICT (channel_id) DO UPDATE
                           SET name = EXCLUDED.name,
                           last_updated = NOW()'''

private_message_query = '''INSERT INTO private_messages VALUES (%s, %s, %s, %s, %s, %s)
                             ON CONFLICT (message_id) DO NOTHING'''
guild_message_query = '''INSERT INTO guild_messages VALUES (%s, %s, %s, %s, %s, %s)
                             ON CONFLICT (message_id) DO NOTHING'''

private_attachment_query = '''INSERT INTO private_attachments VALUES (%s, %s, %s, %s, %s)
                                ON CONFLICT (attachment_id) DO NOTHING'''
guild_attachment_query = '''INSERT INTO guild_attachments VALUES (%s, %s, %s, %s, %s)
                              ON CONFLICT (attachment_id) DO NOTHING'''

private_edit_query = '''INSERT INTO private_edits VALUES (%s, %s, %s, %s)'''
guild_edit_query = '''INSERT INTO guild_edits VALUES (%s, %s, %s, %s)'''

private_deletion_query = '''INSERT INTO private_deletions VALUES (%s)'''
guild_deletion_query = '''INSERT INTO guild_deletions VALUES (%s)'''


def get_rich_embed(message: disnake.Message):
    if message.embeds:
        for e in message.embeds:  # type: disnake.Embed
            if e.type == 'rich':
                return json.dumps(e.to_dict())
        else:
            return None
    else:
        return None


class Panopticon(disnake.Client):
    pool: aiopg.Pool
    connected = False

    async def start_bot(self, token, dsn, *a, **k):
        print('Connecting to database...')
        self.pool = await aiopg.create_pool(dsn)
        print('Connecting to Discord...')
        await self.start(token, *a, **k)

    async def close(self):
        self.pool.close()
        await self.pool.wait_closed()

    async def db_add_user(self, user: disnake.User, cur: aiopg.Cursor):
        await cur.execute(user_query, (user.id, user.created_at, user.name, user.discriminator, user.bot))

    async def db_add_guild(self, guild: disnake.Guild, cur: aiopg.Cursor):
        await cur.execute(guild_query, (guild.id, guild.name))

    async def db_add_private_channel(self, channel: disnake.DMChannel, cur: aiopg.Cursor):
        ids = sorted((channel.recipient.id, self.user.id))
        await cur.execute(private_channel_query, (channel.id, *ids))

    async def db_add_guild_channel(self, channel: disnake.TextChannel, cur: aiopg.Cursor):
        await self.db_add_guild(channel.guild, cur)
        await cur.execute(guild_channel_query, (channel.id, channel.guild.id, channel.name))

    async def db_add_message(self, message: disnake.Message, cur: aiopg.Cursor):
        embed = get_rich_embed(message)
        is_private = isinstance(message.channel, disnake.DMChannel)
        if is_private:
            message_query = private_message_query
            attachment_query = private_attachment_query
            await self.db_add_user(message.channel.recipient, cur)
            await self.db_add_private_channel(message.channel, cur)
        else:
            message_query = guild_message_query
            attachment_query = guild_attachment_query
            await self.db_add_user(message.author, cur)
            await self.db_add_guild_channel(message.channel, cur)
        await cur.execute(message_query, (message.id, message.created_at, message.channel.id, message.author.id,
                                          message.content, embed))
        for a in message.attachments:  # type: disnake.Attachment
            await cur.execute(attachment_query, (a.id, message.id, a.size, a.filename, a.url))

    async def db_add_edit(self, message: disnake.Message, cur: aiopg.Cursor):
        embed = get_rich_embed(message)
        is_private = isinstance(message.channel, disnake.DMChannel)
        if is_private:
            edit_query = private_edit_query
        else:
            edit_query = guild_edit_query
        if message.edited_at:
            edited_at = message.edited_at
        else:
            # I saw one time message.edited_at was None, so just in case.
            edited_at = datetime.utcnow()
        await cur.execute(edit_query, (message.id, edited_at, message.content, embed))

    async def db_add_deletion(self, message: disnake.Message, cur: aiopg.Cursor):
        is_private = isinstance(message.channel, disnake.DMChannel)
        if is_private:
            deletion_query = private_deletion_query
        else:
            deletion_query = guild_deletion_query
        await cur.execute(deletion_query, (message.id,))

    async def on_ready(self):
        if not self.connected:
            print('Ready!')
            async with self.pool.acquire() as conn:  # type: aiopg.Connection
                async with conn.cursor() as cur:  # type: aiopg.Cursor
                    await self.db_add_user(self.user, cur)
            self.connected = True

    async def on_message(self, message: disnake.Message):
        if isinstance(message.channel, (disnake.TextChannel, disnake.DMChannel)):
            async with self.pool.acquire() as conn:  # type: aiopg.Connection
                async with conn.cursor() as cur:  # type: aiopg.Cursor
                    await self.db_add_message(message, cur)

    async def on_message_edit(self, before: disnake.Message, after: disnake.Message):
        if isinstance(after.channel, (disnake.TextChannel, disnake.DMChannel)):
            if before.content != after.content or get_rich_embed(before) != get_rich_embed(after):
                async with self.pool.acquire() as conn:  # type: aiopg.Connection
                    async with conn.cursor() as cur:  # type: aiopg.Cursor
                        await self.db_add_edit(after, cur)

    async def on_message_delete(self, message: disnake.Message):
        if isinstance(message.channel, (disnake.TextChannel, disnake.DMChannel)):
            async with self.pool.acquire() as conn:  # type: aiopg.Connection
                async with conn.cursor() as cur:  # type: aiopg.Cursor
                    try:
                        await self.db_add_deletion(message, cur)
                    except psycopg2.IntegrityError:
                        # the edit may have fired before the message was inserted
                        pass


config = ConfigParser()
config.read('config.ini')

p = Panopticon(max_messages=config.getint('main', 'max_messages'))

loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(p.start_bot(config['main']['token'], config['database']['dsn']))
except KeyboardInterrupt:
    loop.run_until_complete(p.logout())
finally:
    loop.close()
