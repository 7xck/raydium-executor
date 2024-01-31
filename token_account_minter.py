import requests
import pangres
from sqlalchemy import create_engine
import pandas as pd
from utils.create_token_address import create_account
import time
import json
import traceback

sol_mint = "So11111111111111111111111111111111111111112"

# read config.json
# so gay
with open("config.json") as f:
    config = json.load(f)

db_connection = create_engine(config["db"])
try:
    # Open the local JSON file
    with open("/home/ubuntu/raydium_exe_dev/mainnet.json", "r") as file:
        data = json.load(file)
        all_pools = data["unOfficial"]
except Exception as e:
    # Handle exceptions, e.g., file not found, JSON decode error, etc.
    print("An error occurred:", e)

# upload all_pools to postgres
df = pd.DataFrame(all_pools)
df = df[df["quoteMint"] == sol_mint]

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
    try:
        with open("/home/ubuntu/raydium_exe_dev/mainnet.json", "r") as file:
            data = json.load(file)
            all_pools = data["unOfficial"]
    except:
        continue

    # upload all_pools to postgres
    df = pd.DataFrame(all_pools)
    df = df[
        (df["quoteMint"] == sol_mint)
        | (df["baseMint"] == sol_mint)
    ]

    seen_pools = pd.read_sql(
        """SELECT * FROM all_pools WHERE 
                            "quoteMint" = 'So11111111111111111111111111111111111111112'
                            OR "baseMint" = 'So11111111111111111111111111111111111111112' """,
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
            if row["quoteMint"] == sol_mint:
                print("creating account for ", row["baseMint"])
                create_account(
                    config["private_key"],
                    config["wallet_add"],
                    row["programId"],
                    row["baseMint"],
                )
                print("created account for ", row["baseMint"])
            else:
                print("creating account for ", row["quoteMint"])
                create_account(
                    config["private_key"],
                    config["wallet_add"],
                    row["programId"],
                    row["quoteMint"],
                )
                print("created account for ", row["quoteMint"])

        except Exception as exc:
            print(exc)
            traceback.print_exc()
            print("failed to create account for ", row["baseMint"], row["quoteMint"])
            continue
