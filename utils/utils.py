import requests
from loguru import logger
from solders.pubkey import Pubkey as PublicKey
from solana.rpc.api import Client
from solana.rpc.types import TokenAccountOpts
import json
import time
import traceback
import pandas as pd
from sqlalchemy import create_engine


def load_config(file_path: str):
    """Load configuration from a JSON file."""
    with open(file_path) as file:
        return json.load(file)


# get db engine
engine = create_engine(load_config("config.json")["db"])


def extract_pool_info(pools_list: list, pool_id: str) -> dict:
    print("starting to extract pool info")
    start_time = pd.Timestamp.now()
    for pool in pools_list:
        if pool["id"] == pool_id:
            end_time = pd.Timestamp.now()
            print("time it took to extract pool info", end_time - start_time)
            return pool
    raise Exception(f"{pool_id} pool not found!")


def fetch_pool_keys(pool_id: str):
    df = pd.read_sql(f"""SELECT * FROM all_pools WHERE id = '{pool_id}' """, engine)
    if len(df.index) == 1:
        # turn it into a json dictionary because it will only be 1 row
        df = df.to_json(orient="records")
        amm_info = json.loads(df)[0]
        print("found pool in db!")
        return {
            "amm_id": PublicKey.from_string(pool_id),
            "authority": PublicKey.from_string(amm_info["authority"]),
            "base_mint": PublicKey.from_string(amm_info["baseMint"]),
            "base_decimals": amm_info["baseDecimals"],
            "quote_mint": PublicKey.from_string(amm_info["quoteMint"]),
            "quote_decimals": amm_info["quoteDecimals"],
            "lp_mint": PublicKey.from_string(amm_info["lpMint"]),
            "open_orders": PublicKey.from_string(amm_info["openOrders"]),
            "target_orders": PublicKey.from_string(amm_info["targetOrders"]),
            "base_vault": PublicKey.from_string(amm_info["baseVault"]),
            "quote_vault": PublicKey.from_string(amm_info["quoteVault"]),
            "market_id": PublicKey.from_string(amm_info["marketId"]),
            "market_base_vault": PublicKey.from_string(amm_info["marketBaseVault"]),
            "market_quote_vault": PublicKey.from_string(amm_info["marketQuoteVault"]),
            "market_authority": PublicKey.from_string(amm_info["marketAuthority"]),
            "bids": PublicKey.from_string(amm_info["marketBids"]),
            "asks": PublicKey.from_string(amm_info["marketAsks"]),
            "event_queue": PublicKey.from_string(amm_info["marketEventQueue"]),
            "program_id": amm_info["programId"],
            "str_quote_mint": amm_info["quoteMint"],
            "str_base_mint": amm_info["baseMint"],
        }

    while True:
        start_time = pd.Timestamp.now()
        all_pools = requests.get(
            "https://api.raydium.io/v2/sdk/liquidity/mainnet.json",
        ).json()
        print("hit raydium api, time it took", pd.Timestamp.now() - start_time)
        pools = all_pools["official"] + all_pools["unOfficial"]
        try:
            amm_info = extract_pool_info(pools, pool_id)
            break
        except Exception:
            traceback.print_exc()
            time.sleep(20)
            continue

    return {
        "amm_id": PublicKey.from_string(pool_id),
        "authority": PublicKey.from_string(amm_info["authority"]),
        "base_mint": PublicKey.from_string(amm_info["baseMint"]),
        "base_decimals": amm_info["baseDecimals"],
        "quote_mint": PublicKey.from_string(amm_info["quoteMint"]),
        "quote_decimals": amm_info["quoteDecimals"],
        "lp_mint": PublicKey.from_string(amm_info["lpMint"]),
        "open_orders": PublicKey.from_string(amm_info["openOrders"]),
        "target_orders": PublicKey.from_string(amm_info["targetOrders"]),
        "base_vault": PublicKey.from_string(amm_info["baseVault"]),
        "quote_vault": PublicKey.from_string(amm_info["quoteVault"]),
        "market_id": PublicKey.from_string(amm_info["marketId"]),
        "market_base_vault": PublicKey.from_string(amm_info["marketBaseVault"]),
        "market_quote_vault": PublicKey.from_string(amm_info["marketQuoteVault"]),
        "market_authority": PublicKey.from_string(amm_info["marketAuthority"]),
        "bids": PublicKey.from_string(amm_info["marketBids"]),
        "asks": PublicKey.from_string(amm_info["marketAsks"]),
        "event_queue": PublicKey.from_string(amm_info["marketEventQueue"]),
        "program_id": amm_info["programId"],
        "str_quote_mint": amm_info["quoteMint"],
        "str_base_mint": amm_info["baseMint"],
    }


def get_token_account(client, owner: PublicKey, mint: PublicKey):
    account_data = client.get_token_accounts_by_owner(owner, TokenAccountOpts(mint))
    print("mint", account_data.value[0].pubkey)
    return account_data.value[0].pubkey


def sale_info(balance_before: dict, balance_after: dict):
    base_symbol, quote_symbol = balance_before.keys()
    base_before, quote_before = balance_before.values()
    base_after, quote_after = balance_after.values()
    sold_amount = base_before - base_after
    quote_received = quote_after - quote_before
    price = quote_received / sold_amount
    logger.info(
        f"Sold {sold_amount} {base_symbol}, price: {price} {quote_symbol}, {quote_symbol} received: {quote_received}"
    )


def purchase_info(balance_before: dict, balance_after: dict):
    base_symbol, quote_symbol = balance_before.keys()
    base_before, quote_before = balance_before.values()
    base_after, quote_after = balance_after.values()
    bought_amount = base_after - base_before
    quote_spent = quote_before - quote_after
    price = quote_spent / bought_amount
    logger.info(
        f"Bought {bought_amount} {base_symbol}, price: {price} {quote_symbol}, {quote_symbol} spent: {quote_spent}"
    )
