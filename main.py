import asyncio
import json
import traceback
from typing import Any
import time

from loguru import logger

from CEX import CEX
from raydium_amm import Liquidity
from utils import purchase_info, sale_info

# read json config file
with open("config.json") as f:
    config = json.load(f)


async def main():
    size = 0.5
    amm = Liquidity(
        "https://api.mainnet-beta.solana.com",
        "5wyH6cE9qaNmxw9HyM2WVHZkQDXyrFVSgEMCDksbfjUP",
        config["private_key"],
        "coin/sol",
    )
    coin_balances = await amm.get_balance()
    sol_before = coin_balances["sol"]

    await amm.buy(size)
    time.sleep(5)
    coin_balances = await amm.get_balance()
    sell_size = coin_balances["coin"]
    await amm.sell(sell_size)
    time.sleep(5)
    coin_balances = await amm.get_balance()
    sol_after = coin_balances["sol"]
    print({"before": sol_before}, {"after": sol_after})
    print({"profit": sol_after - sol_before})
    print("return, ", sol_after / sol_before - 1)


if __name__ == "__main__":
    asyncio.run(main())
