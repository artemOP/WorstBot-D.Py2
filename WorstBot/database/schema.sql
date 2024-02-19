DO $$ BEGIN
    CREATE TYPE MEMBER as (
        guild_id BIGINT,
        user_id BIGINT,
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;
```