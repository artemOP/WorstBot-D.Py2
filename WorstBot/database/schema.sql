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