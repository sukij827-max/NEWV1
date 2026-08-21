# GENZ Experience Bot — V1

Telegram-only. Railway + PostgreSQL.

## Required variables
```text
BOT_TOKEN=
OWNER_ID=
CHANNEL_USERNAME=
DATABASE_URL=
SECRET_KEY=
```

`OWNER_ID` is the immutable Telegram identity of the owner. `CHANNEL_USERNAME` is the public channel username used for membership checks. The bot must be an administrator in the channel.

Premium is granted manually by owner and is stored by Telegram ID, so changing username does not remove Premium.
