-- Assuming given_user_id is the user_id that should always be included in the leaderboard
WITH transactions_summary AS (
    SELECT
        (member).user_id AS user_id,
        SUM(CASE WHEN transaction = 'DEPOSIT' THEN amount ELSE 0 END) AS total_deposits,
        SUM(CASE WHEN transaction = 'WITHDRAW' THEN amount ELSE 0 END) AS total_withdrawals,
        SUM(CASE WHEN transaction = 'GIVE' THEN amount ELSE 0 END) AS total_given,
        SUM(CASE WHEN transaction = 'RECEIVE' THEN amount ELSE 0 END) AS total_received,
        SUM(CASE WHEN transaction = 'GAMBLE' THEN amount ELSE 0 END) AS total_gambled,
        SUM(CASE WHEN transaction = 'WORK' THEN amount ELSE 0 END) AS total_worked
    FROM
        economy
    WHERE 
        (member).guild_id = $1
    GROUP BY
        user_id
    
),
combined_wealth AS (
    SELECT
        user_id,
        (total_received + total_gambled + total_worked - total_given) AS combined_balance
    FROM
        transactions_summary
),
leaderboard AS (
    SELECT
        *,
        ROW_NUMBER() OVER (ORDER BY combined_balance DESC) AS rank
    FROM
        combined_wealth
),
top_n AS (
    SELECT
        *
    FROM
        leaderboard
    WHERE
        rank <= $3
),
include_user AS (
    SELECT
        *
    FROM
        leaderboard
    WHERE
        user_id = $2
)
-- Select the top n users by wealth and ensure the given user is included
SELECT
    *
FROM
    top_n
UNION
SELECT
    *
FROM
    include_user
ORDER BY
    combined_balance DESC
LIMIT $3;
