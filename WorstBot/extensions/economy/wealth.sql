WITH transactions_summary AS (
    SELECT
        member,
        SUM(CASE WHEN transaction = 'DEPOSIT' THEN amount ELSE 0 END) AS total_deposits,
        SUM(CASE WHEN transaction = 'WITHDRAW' THEN amount ELSE 0 END) AS total_withdrawals,
        SUM(CASE WHEN transaction = 'ASCEND' THEN amount ELSE 0 END) AS total_ascended,
        SUM(CASE WHEN transaction = 'GIVE' THEN amount ELSE 0 END) AS total_given,
        SUM(CASE WHEN transaction = 'RECEIVE' THEN amount ELSE 0 END) AS total_received,
        SUM(CASE WHEN transaction = 'GAMBLE' THEN amount ELSE 0 END) AS total_gambled,
        SUM(CASE WHEN transaction = 'WORK' THEN amount ELSE 0 END) AS total_worked,
        COALESCE(MAX(CASE WHEN transaction = 'CONVERSION_RATE' THEN amount ELSE NULL END), 1) AS conversion_rate
    FROM
        economy
    WHERE
        member = $1::MEMBER
    GROUP BY
        member
),
balances AS (
    SELECT
        member,
        (
            total_received + total_gambled + total_worked
            - total_given
            + total_withdrawals
            - total_deposits
        ) AS wallet_balance,
        (total_deposits - total_withdrawals) AS bank_balance,
        total_ascended AS ascended_balance,
        conversion_rate
    FROM
        transactions_summary
)

SELECT
    member,
    wallet_balance,
    bank_balance,
    ascended_balance,
    conversion_rate
FROM
    balances;
