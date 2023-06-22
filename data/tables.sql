BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS banned_text (
    id INTEGER PRIMARY KEY,
    message TEXT
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    broadcaster_type TEXT,
    description TEXT,
    display_name TEXT,
    login TEXT,
    offline_image_url TEXT,
    profile_image_url TEXT,
    type TEXT,
    view_count INTEGER,
    created_at TEXT,
    first_seen INTEGER DEFAULT(DATETIME('now')),
    last_seen INTEGER
);

CREATE TABLE IF NOT EXISTS points (
    user_id INTEGER PRIMARY KEY,
    points INTEGER DEFAULT(1)
);

CREATE TABLE IF NOT EXISTS chat_log (
    id INTEGER PRIMARY KEY,
    event_time INTEGER DEFAULT(DATETIME('now')),
    display_name TEXT,
    user_id INTEGER,
    tags TEXT,
    message TEXT
);

CREATE TABLE IF NOT EXISTS config (
    id INTEGER PRIMARY KEY,
    key INTEGER UNIQUE NOT NULL,
    value TEXT
);

CREATE TABLE IF NOT EXISTS commands (
    id INTEGER PRIMARY KEY,
    command TEXT,
    response TEXT
);

CREATE TABLE IF NOT EXISTS bots (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    live_in INTEGER,
    last_seen INTEGER,
    whitelist INTEGER DEFAULT 0 NOT NULL,
    banned INTEGER DEFAULT 0 NOT NULL
);

INSERT INTO bots (username, whitelist) VALUES ('streamlabs', 1) ON CONFLICT(username) DO NOTHING;
INSERT INTO bots (username, whitelist) VALUES ('streamelements', 1) ON CONFLICT(username) DO NOTHING;
INSERT INTO bots (username, whitelist) VALUES ('commanderroot', 1) ON CONFLICT(username) DO NOTHING;

COMMIT;