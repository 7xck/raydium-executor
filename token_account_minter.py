import requests
import pangres
from sqlalchemy import create_engine
import pandas as pd
from utils.create_token_address import create_account
import time
import json

# read config.json
# so gay
with open("config.json") as f:
    config = json.load(f)

db_connection = create_engine(config["db"])
all_pools = requests.get("https://api.raydium.io/v2/sdk/liquidity/mainnet.json").json()[
    "unOfficial"
]

# upload all_pools to postgres
df = pd.DataFrame(all_pools)
df = df[df["quoteMint"] == "So11111111111111111111111111111111111111112"]

seen_pools = pd.read_sql(
    """SELECT * FROM all_pools WHERE 
                        "quoteMint" = 'So11111111111111111111111111111111111111112' """,
    db_connection,
)

unseen_pools = df[~df["id"].isin(seen_pools["id"])]

if len(unseen_pools.index) > 0:
    print("UNSEEN POOL!!!")
    print(unseen_pools)
    unseen_pools = unseen_pools.set_index("id")
    unseen_pools.to_sql("all_pools", db_connection, if_exists="append")
while True:
    all_pools = requests.get(
        "https://api.raydium.io/v2/sdk/liquidity/mainnet.json"
    ).json()["unOfficial"]

    # upload all_pools to postgres
    df = pd.DataFrame(all_pools)
    df = df[df["quoteMint"] == "So11111111111111111111111111111111111111112"]

    seen_pools = pd.read_sql(
        """SELECT * FROM all_pools WHERE 
                            "quoteMint" = 'So11111111111111111111111111111111111111112' """,
        db_connection,
    )

    unseen_pools = df[~df["id"].isin(seen_pools["id"])]

    if len(unseen_pools.index) > 0:
        print("UNSEEN POOL!!!")
        print(unseen_pools)
        unseen_pools = unseen_pools.set_index("id")
        unseen_pools["time_scraped"] = pd.Timestamp.utcnow()
        unseen_pools.to_sql("all_pools", db_connection, if_exists="append")

    for idx, row in unseen_pools.iterrows():
        try:
            create_account(
                config["private_key"],
                config["wallet_add"],
                row["programId"],
                row["baseMint"],
            )
            print("created account for ", row["baseMint"])
        except:
            print("failed to create account for ", row["baseMint"])
            continue
    time.sleep(30)
