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
from typing import Union

import disnake
import asyncpg

user_query = '''INSERT INTO users VALUES ($1, $2, $3, $4, $5)
                   ON CONFLICT (user_id) DO UPDATE
                   SET name = EXCLUDED.name,
                   discriminator = EXCLUDED.discriminator,
                   last_updated = NOW()'''

guild_query = '''INSERT INTO guilds VALUES ($1, $2)
                    ON CONFLICT (guild_id) DO UPDATE
                    SET name = EXCLUDED.name,
                    last_updated = NOW()'''

private_channel_query = '''INSERT INTO private_channels VALUES ($1, $2, $3)
                             ON CONFLICT (channel_id) DO NOTHING'''
guild_channel_query = '''INSERT INTO guild_channels VALUES ($1, $2, $3)
                           ON CONFLICT (channel_id) DO UPDATE
                           SET name = EXCLUDED.name,
                           last_updated = NOW()'''

private_message_query = '''INSERT INTO private_messages VALUES ($1, $2, $3, $4, $5, $6)
                             ON CONFLICT (message_id) DO NOTHING'''
guild_message_query = '''INSERT INTO guild_messages VALUES ($1, $2, $3, $4, $5, $6)
                             ON CONFLICT (message_id) DO NOTHING'''

private_attachment_query = '''INSERT INTO private_attachments VALUES ($1, $2, $3, $4, $5)
                                ON CONFLICT (attachment_id) DO NOTHING'''
guild_attachment_query = '''INSERT INTO guild_attachments VALUES ($1, $2, $3, $4, $5)
                              ON CONFLICT (attachment_id) DO NOTHING'''

private_edit_query = '''INSERT INTO private_edits VALUES ($1, $2, $3, $4)'''
guild_edit_query = '''INSERT INTO guild_edits VALUES ($1, $2, $3, $4)'''

private_deletion_query = '''INSERT INTO private_deletions VALUES ($1)'''
guild_deletion_query = '''INSERT INTO guild_deletions VALUES ($1)'''


GuildChannel = Union[disnake.TextChannel, disnake.VoiceChannel, disnake.Thread]


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
    pool: asyncpg.Pool
    user: disnake.ClientUser
    connected = False

    async def start_bot(self, token, dsn: str, *a, **k):
        self.pool = await asyncpg.create_pool(dsn)
        self.private_channel_cache = {}
        await self.start(token, *a, **k)

    async def close(self):
        await self.pool.close()

    async def db_add_user(self, user: Union[disnake.User, disnake.Member, disnake.ClientUser],
                          conn: asyncpg.Connection):
        await conn.execute(user_query, user.id, user.created_at, user.name, user.discriminator, user.bot)

    async def db_add_guild(self, guild: disnake.Guild, conn: asyncpg.Connection):
        await conn.execute(guild_query, guild.id, guild.name)

    async def db_add_private_channel(self, channel: disnake.DMChannel, conn: asyncpg.Connection):
        ids = sorted((channel.recipient.id, self.user.id))
        await conn.execute(private_channel_query, channel.id, *ids)

    async def db_add_guild_channel(self, channel: GuildChannel, conn: asyncpg.Connection):
        await self.db_add_guild(channel.guild, conn)
        await conn.execute(guild_channel_query, channel.id, channel.guild.id, channel.name)

    async def db_add_message(self, message: disnake.Message, conn: asyncpg.Connection):
        embed = get_rich_embed(message)
        is_private = isinstance(message.channel, disnake.DMChannel)
        if is_private:
            if message.channel.recipient is None:
                return
            message_query = private_message_query
            attachment_query = private_attachment_query
            await self.db_add_user(message.channel.recipient, conn)
            await self.db_add_private_channel(message.channel, conn)
        else:
            message_query = guild_message_query
            attachment_query = guild_attachment_query
            await self.db_add_user(message.author, conn)
            await self.db_add_guild_channel(message.channel, conn)
        await conn.execute(message_query, message.id, message.created_at, message.channel.id, message.author.id,
                           message.content, embed)
        for a in message.attachments:  # type: disnake.Attachment
            await conn.execute(attachment_query, a.id, message.id, a.size, a.filename, a.url)

    async def db_add_edit(self, message: disnake.Message, conn: asyncpg.Connection):
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
        await conn.execute(edit_query, message.id, edited_at, message.content, embed)

    async def db_add_deletion(self, message: disnake.Message, conn: asyncpg.Connection):
        is_private = isinstance(message.channel, disnake.DMChannel)
        if is_private:
            deletion_query = private_deletion_query
        else:
            deletion_query = guild_deletion_query
        await conn.execute(deletion_query, message.id)

    async def on_ready(self):
        if not self.connected:
            print('Ready!')
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    await self.db_add_user(self.user, conn)
            self.connected = True

    async def on_message(self, message: disnake.Message):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await self.db_add_message(message, conn)

    async def on_message_edit(self, before: disnake.Message, after: disnake.Message):
        if before.content != after.content or get_rich_embed(before) != get_rich_embed(after):
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    await self.db_add_edit(after, conn)

    async def on_message_delete(self, message: disnake.Message):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                try:
                    await self.db_add_deletion(message, conn)
                except asyncpg.IntegrityConstraintViolationError:
                    # the edit may have fired before the message was inserted
                    pass


config = ConfigParser()
config.read('config.ini')
intents = disnake.Intents(messages=True, members=True, message_content=True, guilds=True)
p = Panopticon(max_messages=config.getint('main', 'max_messages'), intents=intents)
loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(p.start_bot(config['main']['token'], config['database']['dsn']))
except KeyboardInterrupt:
    loop.run_until_complete(p.close())
finally:
    loop.close()
