import os
from dataclasses import dataclass

def req(name: str) -> str:
    v = os.getenv(name, '').strip()
    if not v:
        raise RuntimeError(f'Missing required environment variable: {name}')
    return v

@dataclass(frozen=True)
class Settings:
    bot_token: str
    owner_id: int
    channel_username: str
    database_url: str
    secret_key: str
    log_level: str

def load() -> Settings:
    db = req('DATABASE_URL')
    if db.startswith('postgres://'):
        db = 'postgresql+asyncpg://' + db[11:]
    elif db.startswith('postgresql://'):
        db = 'postgresql+asyncpg://' + db[13:]
    elif db.startswith('sqlite:///'):
        db = db.replace('sqlite:///', 'sqlite+aiosqlite:///', 1)
    return Settings(
        req('BOT_TOKEN'),
        int(req('OWNER_ID')),
        req('CHANNEL_USERNAME').lstrip('@'),
        db,
        req('SECRET_KEY'),
        os.getenv('LOG_LEVEL', 'INFO'),
    )

settings = load()
