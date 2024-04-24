SELECT
    count(*) as "num_donations",
    count(distinct voter) as unique_voters,
    count(distinct "payoutaddress") as unique_grantees,
    sum("amountUSD") as "crowdfunded_usd",
    max(tx_timestamp) as "last_donation",
    11700000 as "bounties_distributed",
    (SELECT sum(match_amount_usd) FROM all_matching) as "matchingfunds"
FROM
    all_donations;