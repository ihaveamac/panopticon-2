# panopticon-2
Discord message logger, similar to [the original panopticon](https://github.com/ihaveamac/panopticon).

Logs guilds, channels (DM and guild), users, and messages. Does not log private groups (bot accounts cannot be in these anyway).

## Requirements
* Python 3.6.1 or later
* disnake >= 2.4 and aiopg
* PostgreSQL (10 tested)

## Quick setup
* Install and set up a database in PostgreSQL
* Execute `schema.sql` to set up the tables
* Install Python 3.6.1 or later
* Recommended: Set up a [virtual environment](https://docs.python.org/3/tutorial/venv.html)
* Install the Python requirements: `pip install -r requirements.txt`

## License / Credits
`panopticon-2` is under the MIT license. Special thanks to @Jisagi for assistance with the database schema design.
