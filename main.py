import asyncio
import json
import traceback
from typing import Any
import time

from raydium_amm import Liquidity

# read json config file
with open("config.json") as f:
    config = json.load(f)

# read in command line arg and set it as pool_id
import sys

try:
    pool_id = sys.argv[1]
except:
    pool_id = "Dz2sTsKhaSPJLjTh5ZeSufeQrQixqsAjFhwz9hxH7h3D"


async def main():
    size = 1
    amm = Liquidity(
        config["rpc"],
        # "https://api.mainnet-beta.solana.com",  # rpc
        pool_id,  # pool id
        config["private_key"],  # private key
        "coin/sol",  # placeholder
        config["wallet_add"],  # my wallet address
    )
    coin_balances = await amm.get_balance()
    sol_before = coin_balances["sol"]
    while True:
        try:
            await amm.buy(size)
            break
        except:
            traceback.print_exc()
            print("failed b")
            continue
    print("bought ", size)
    time.sleep(10)
    coin_balances = await amm.get_balance()
    print(coin_balances)
    sell_size = coin_balances["coin"]
    time.sleep(6)
    tries = 0
    while True:
        try:
            await amm.sell(sell_size)
            break
        except:
            time.sleep(0.4)
            tries += 1
            print("failed s", tries)
            continue
    print("sold", sell_size)
    time.sleep(5)
    coin_balances = await amm.get_balance()
    sol_after = coin_balances["sol"]
    print({"before": sol_before}, {"after": sol_after})
    print({"profit": sol_after - sol_before})
    print("return, ", sol_after / sol_before - 1)


if __name__ == "__main__":
    asyncio.run(main())
