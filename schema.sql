-- Created for PostgreSQL 10

DROP TABLE IF EXISTS guild_attachments, private_attachments, guild_edits, private_edits, guild_deletions,
  private_deletions, guild_messages, private_messages, guild_channels, private_channels, guilds, users;

CREATE TABLE users
(
  user_id       BIGINT PRIMARY KEY,
  created_at    TIMESTAMP                NOT NULL,
  name          TEXT                     NOT NULL,
  discriminator VARCHAR(4)               NOT NULL,
  is_bot        BOOLEAN                  NOT NULL,
  last_updated  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE guilds
(
  guild_id     BIGINT PRIMARY KEY,
  name         TEXT                     NOT NULL,
  last_updated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE guild_channels
(
  channel_id   BIGINT PRIMARY KEY,
  guild_id     BIGINT                   NOT NULL REFERENCES guilds (guild_id),
  name         TEXT                     NOT NULL,
  last_updated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE private_channels
(
  channel_id BIGINT PRIMARY KEY,
  user_id1   BIGINT NOT NULL REFERENCES users (user_id),
  user_id2   BIGINT NOT NULL REFERENCES users (user_id)
);

CREATE TABLE guild_messages
(
  message_id BIGINT PRIMARY KEY,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL,
  channel_id BIGINT                   NOT NULL REFERENCES guild_channels (channel_id),
  user_id    BIGINT                   NOT NULL REFERENCES users (user_id),
  content    TEXT                     NOT NULL,
  rich_embed JSON
);

CREATE TABLE private_messages
(
  message_id BIGINT PRIMARY KEY,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL,
  channel_id BIGINT                   NOT NULL REFERENCES private_channels (channel_id),
  user_id    BIGINT                   NOT NULL REFERENCES users (user_id),
  content    TEXT                     NOT NULL,
  rich_embed JSON
);

CREATE TABLE guild_edits
(
  message_id BIGINT                   NOT NULL REFERENCES guild_messages (message_id),
  edited_at  TIMESTAMP WITH TIME ZONE NOT NULL,
  content    TEXT                     NOT NULL,
  embed      JSON
);

CREATE TABLE private_edits
(
  message_id BIGINT                   NOT NULL REFERENCES private_messages (message_id),
  edited_at  TIMESTAMP WITH TIME ZONE NOT NULL,
  content    TEXT                     NOT NULL,
  embed      JSON
);

CREATE TABLE guild_deletions
(
  message_id BIGINT                   NOT NULL REFERENCES guild_messages (message_id),
  deleted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE private_deletions
(
  message_id BIGINT                   NOT NULL REFERENCES private_messages (message_id),
  deleted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE guild_attachments
(
  attachment_id BIGINT PRIMARY KEY,
  message_id    BIGINT  NOT NULL REFERENCES guild_messages (message_id),
  filesize      INTEGER NOT NULL,
  filename      TEXT    NOT NULL,
  url           TEXT    NOT NULL
);

CREATE TABLE private_attachments
(
  attachment_id BIGINT PRIMARY KEY,
  message_id    BIGINT  NOT NULL REFERENCES private_messages (message_id),
  filesize      INTEGER NOT NULL,
  filename      TEXT    NOT NULL,
  url           TEXT    NOT NULL
);
