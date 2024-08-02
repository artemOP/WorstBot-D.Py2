WITH user_stats AS (
    SELECT 
        (member).user_id AS user_id,
        COUNT(*) AS xp,
        MAX(message_timestamp) AS last_message
    FROM 
        chatter
    WHERE 
        (member).guild_id = $1
    GROUP BY 
        (member).user_id
),
ranked_stats AS (
    SELECT
        user_id,
        xp,
        last_message,
        ROW_NUMBER() OVER (ORDER BY xp DESC, last_message DESC) AS rank
    FROM
        user_stats
)
SELECT 
    user_id,
    xp,
    last_message,
    rank
FROM
    ranked_stats
WHERE
    rank <= $3

UNION ALL

SELECT 
    user_id,
    xp,
    last_message,
    rank
FROM
    ranked_stats
WHERE
    user_id = $2 AND rank > $3
ORDER BY
    rank;
