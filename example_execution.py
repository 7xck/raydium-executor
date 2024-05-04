import requests
import re
from raydium_executor import RaydiumExecutor

#%%
# Define your wallet details and crap
rpc_endpoint = "https://solana-api.projectserum.com/"  # best to use a paid RPC, I liked chainstack.
wallet_secret = "..."  # literally just your wallet secret key
wallet_address = "..."  # literally just your wallet address...

#%%
# we need some pool keys. get these from where ever you want. Raydium website is always slow, but works.
# you can also get them from the onchain data, but that's a bit more complicated.
# if you want to get the freshest pools (i.e. just created pools you want to snipe) you will need to build a tool
# to get them on chain. there is typescript code in the raydium sdk github repo to do this.
# here's an example of how you might get them from the Raydium website
# result = requests.get(
#     "https://api.raydium.io/v2/sdk/liquidity/mainnet.json"
# )
# result_json = result.json()
# result_json["unOfficial"]
# for x in result_json["unOfficial"]:
#     if x["id"] == "GH8Ers4yzKR3UKDvgVu8cqJfGzU4cU62mTeg9bcJ7ug6":
#         print("found pool")
#     pool_data = x


# this pool is just some random pool I found looking at what was popular
# at the moment on Dexscreener... GuardianAI coin? whatever...
# Dexscreener sites have the pool id in the URL, eg:
# https://dexscreener.com/solana/6a1csrpezubdjeje9s1cmvheb6hwm5d7m1cj2jkhyxhj
# 6a1c... is the pool id in this case, so now do a simple search like I did in the commented out code above
# to get all the pool key details...
# this is how it comes from the API...
pool_data = {'id': 'zZzp86JcMhjdwaoxgewghCx7TC1uxq6d3fCYLm87zFE',
             'baseMint': 'BiePGS754tJp9Khp7PHUcc6ahXfKPq9QBZwxvq5s8FZp',
             'quoteMint': 'So11111111111111111111111111111111111111112',
             'lpMint': '5iZsGVkSGwtiqWzyV4RprdJGkjVgJZ6JZ2SLHwu1Y8TH',
             'baseDecimals': 9,
             'quoteDecimals': 9,
             'lpDecimals': 9,
             'version': 4,
             'programId': '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8',
             'authority': '5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1',
             'openOrders': '8UHqksqCfwU8quUp463sshzPPB8idzHdnX4Mw5fsvAoR',
             'targetOrders': 'Qw6rBxPob153Qi6n6BD2rHwBmvDjP17Uo5LkCjfYmFX',
             'baseVault': 'CvRawNjcEmwkvntCtpUwruwKrWspG2R1B3DuSa2qCauQ',
             'quoteVault': '9ec4xZw8NhifQ5wDFRMRK9FvgcLS67ETWUbBCicCXZcw',
             'withdrawQueue': '11111111111111111111111111111111',
             'lpVault': '11111111111111111111111111111111',
             'marketVersion': 4,
             'marketProgramId': 'srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX',
             'marketId': '6LCnUWTjPN55FwVtMWhiDHo4AXa7Abg8suDrJiTrHEGG',
             'marketAuthority': '93M2YE4QHChbEb68BKB6HWdYpZZJz3Wqsir8bEBHywKp',
             'marketBaseVault': 'GPyKT2F6GUKGa62GMmPrhFAEfE1cxTVAaxNChM9PvUh',
             'marketQuoteVault': 'GsznDfAYbbRoP4ep6FiHrsUby87G3XmZQGt3yq5t6zc2',
             'marketBids': 'GWje1eXmo1QnCxEDgokY9FHr6v76aX7SmwWeptyLVrFa',
             'marketAsks': 'Cyj1gw28BaPx8xiRPTHXeSsQaraptSexaZGoVe8V3Rrx',
             'marketEventQueue': 'EaYoQyDnhLup8SMQrzBbjeLNBfA17NaQVFzkpvZqPE91',
             'lookupTableAccount': 'A8MGRr6n2EKUweTjb2ffL5bunwfZPR8L5yYpsComWJkj'}
# reformat it so that it's cleaner to work with...


def camel_to_snake(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def reformat_dict(input_dict):
    return {camel_to_snake(key): value for key, value in input_dict.items()}


formatted_pool_keys = reformat_dict(pool_data)

#%%
executor = RaydiumExecutor(
    rpc_endpoint="https://api.mainnet-beta.solana.com",
    pool_id=formatted_pool_keys['id'],
    wallet_secret=wallet_secret,
    wallet_address=wallet_address,
    pool_keys=formatted_pool_keys
)
#%%
await executor.buy(
    amount=0.05
)
#%%
balances = await executor.get_balances()
balance_of_the_coin_we_just_bought = balances[formatted_pool_keys['base_mint']]
#%%
await executor.sell(
    amount=balance_of_the_coin_we_just_bought
)