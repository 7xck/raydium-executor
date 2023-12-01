import asyncio
import json
import sys
import time
import traceback
from typing import Any

from raydium_amm import Liquidity

# Configuration file for setup
CONFIG_FILE = "config.json"

# Default Pool ID if not provided as command line argument
DEFAULT_POOL_ID = "Dz2sTsKhaSPJLjTh5ZeSufeQrQixqsAjFhwz9hxH7h3D"


def load_config(file_path: str) -> Any:
    """Load configuration from a JSON file."""
    with open(file_path) as file:
        return json.load(file)


def get_pool_id() -> str:
    """Retrieve the pool ID from command line arguments or use default."""
    try:
        return sys.argv[1]
    except IndexError:
        return DEFAULT_POOL_ID


async def main():
    config = load_config(CONFIG_FILE)
    pool_id = get_pool_id()

    amm = Liquidity(
        config["rpc"],
        pool_id,
        config["private_key"],
        "coin/sol",
        config["wallet_add"],
    )

    coin_balances = await amm.get_balance()
    sol_before = coin_balances["sol"]

    # Attempt to buy
    size = 1
    while True:
        try:
            await amm.buy(size)
            break
        except Exception as e:
            traceback.print_exc()
            print("Failed to buy: retrying...")
            continue

    print("Bought", size)
    time.sleep(10)

    # Get balances and sell
    coin_balances = await amm.get_balance()
    sell_size = coin_balances["coin"]
    time.sleep(6)
    tries = 0

    while True:
        try:
            await amm.sell(sell_size)
            break
        except Exception as e:
            time.sleep(0.4)
            tries += 1
            print(f"Failed to sell, attempt {tries}")
            continue

    print("Sold", sell_size)
    time.sleep(5)

    # Calculate and display profit
    coin_balances = await amm.get_balance()
    sol_after = coin_balances["sol"]
    print({"before": sol_before}, {"after": sol_after})
    print({"profit": sol_after - sol_before})
    print("Return:", sol_after / sol_before - 1)


if __name__ == "__main__":
    asyncio.run(main())
