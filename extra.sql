-- Extra views and functions.

-- Views:
-- guild_message_with_edits
--   Get all non-deleted messages, with the latest edit

-- Functions:
-- total_messages_per_hour(user_id, channel_id)
--   Count all messages sent for each hour of the day.
--
--   Returns:
--     TABLE (
--       hour  DOUBLE PRECISION,
--       count BIGINT
--     )
--
--   Arguments:
--     user_id    BIGINT DEFAULT NULL,
--     channel_id BIGINT DEFAULT NULL
--
-- message_count_date_trunc(field, user_id, channel_id)
--   Count all messages sent in a unit of time.
--   Valid values for date_trunc: https://www.postgresql.org/docs/10/functions-datetime.html#FUNCTIONS-DATETIME-TRUNC
--
--   Returns:
--     TABLE (
--       utctime TIMESTAMP WITH TIME ZONE,
--       count   BIGINT
--     )
--
--   Arguments:
--     field      TEXT,
--     user_id    BIGINT DEFAULT NULL,
--     channel_id BIGINT DEFAULT NULL

-- get all messages, with the latest edit if edited, removing deleted messages
CREATE OR REPLACE VIEW guild_messages_with_edits AS
SELECT *
FROM (SELECT g.guild_id,
             g.name                                                             AS guild_name,
             gc.channel_id,
             gc.name                                                            AS channel_name,
             gm.message_id,
             gm.created_at,
             ge.edited_at,
             u.name || '#' || u.discriminator                                   AS tag,
             (CASE WHEN ge.content IS NULL THEN gm.content ELSE ge.content END) AS final_content
      FROM guild_messages gm
             LEFT JOIN guild_edits ge ON gm.message_id = ge.message_id AND ge.edited_at = (SELECT max(edited_at)
                                                                                           FROM guild_edits ge1
                                                                                           WHERE ge.message_id = ge1.message_id)
             JOIN users u ON gm.user_id = u.user_id
             JOIN guild_channels gc ON gm.channel_id = gc.channel_id
             JOIN guilds g ON gc.guild_id = g.guild_id
             LEFT JOIN guild_deletions gd ON gm.message_id = gd.message_id
      WHERE gd.message_id IS NULL
      ORDER BY gm.created_at ASC) AS data;

-- get total messages sent per UTC hour, optionally for a specific user and/or channel
CREATE OR REPLACE FUNCTION total_messages_per_hour(BIGINT DEFAULT NULL, BIGINT DEFAULT NULL)
  RETURNS TABLE
          (
            hour  NUMERIC,
            count BIGINT
          )
AS
$$
BEGIN
  RETURN QUERY SELECT date_part('hour', guild_messages.created_at) :: NUMERIC AS hour, COUNT(*)
               FROM guild_messages
                      JOIN guild_channels gc ON guild_messages.channel_id = gc.channel_id
                      JOIN users u ON guild_messages.user_id = u.user_id
                      LEFT JOIN generate_series(0, 23) hhh ON hour = hhh
               WHERE ($1 IS NULL OR u.user_id = $1)
                 AND ($2 IS NULL OR gc.channel_id = $2)
               GROUP BY hour
               ORDER BY hour ASC;
END;
$$ LANGUAGE plpgsql;

-- get messages sent in a unit of time, optionally for a specific user and/or channel
CREATE OR REPLACE FUNCTION message_count_date_trunc(TEXT, BIGINT DEFAULT NULL, BIGINT DEFAULT NULL)
  RETURNS TABLE
          (
            utctime TIMESTAMP WITH TIME ZONE,
            count   BIGINT
          )
AS
$$
BEGIN
  RETURN QUERY SELECT date_trunc($1, guild_messages.created_at) AS hour, COUNT(*)
               FROM guild_messages
                      JOIN guild_channels gc ON guild_messages.channel_id = gc.channel_id
                      JOIN users u ON guild_messages.user_id = u.user_id
               WHERE ($2 IS NULL OR u.user_id = $2)
                 AND ($3 IS NULL OR gc.channel_id = $3)
               GROUP BY hour
               ORDER BY hour ASC;
END;
$$ LANGUAGE plpgsql;
