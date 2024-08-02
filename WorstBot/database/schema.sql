DO $$ BEGIN
    CREATE TYPE MEMBER as (
        guild_id BIGINT,
        user_id BIGINT
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS sponsor_block(
    guild_id BIGINT PRIMARY KEY,
    sponsor BOOLEAN NOT null,
    selfpromo BOOLEAN NOT null,
    interaction BOOLEAN NOT null,
    intro BOOLEAN NOT null,
    outro BOOLEAN NOT null,
    preview BOOLEAN NOT null,
    music_offtopic BOOLEAN NOT null,
    filler BOOLEAN NOT null
);

CREATE TABLE event_toggles(
    guild_id BIGINT PRIMARY KEY,
    event_name TEXT NOT NULL,
    event_value BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS chatter(
    member MEMBER NOT NULL,
    message_timestamp TIMESTAMPTZ DEFAULT NOW()
);

DO $$ BEGIN
    CREATE TYPE TRANSACTION_TYPE AS ENUM ('DEPOSIT', 'WITHDRAW', 'ASCEND', 'GIVE', 'RECEIVE', 'GAMBLE', 'WORK', 'CONVERSION_RATE');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS economy(
    member MEMBER,
    transaction TRANSACTION_TYPE NOT NULL,
    amount NUMERIC(1000, 2) NOT NULL,
    recipient MEMBER,
    transaction_id SERIAL,
    transaction_timestamp TIMESTAMPTZ DEFAULT NOW()
);