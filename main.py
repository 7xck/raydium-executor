import asyncio
import sys
import time
from models.trade_results import TradeResults
from utils.utils import load_config

from exchanges.raydium_amm import Liquidity

# Configuration file for setup
CONFIG_FILE = "config.json"
config = load_config(CONFIG_FILE)

# Default Pool ID if not provided as command line argument
DEFAULT_POOL_ID = "AVs9TA4nWDzfPJE9gGVNJMVhcQy3V9PGazuz33BfG2RA"


def get_pool_id() -> str:
    """Retrieve the pool ID from command line arguments or use default."""
    try:
        return sys.argv[1]
    except IndexError:
        return DEFAULT_POOL_ID


def make_amm(pool_id, symbol="coin/sol"):
    amm = Liquidity(
        config["rpc"],
        pool_id,
        config["private_key"],
        symbol,
        config["wallet_add"],
    )

    return amm


async def buy_leg(amm, size=1):
    buy_tx_result = await amm.buy(size)
    print("Bought", size)
    return buy_tx_result


async def sell_leg(amm, size=1):
    tries = 0
    while True:
        try:
            coin_balances = await amm.get_balance()
            sell_size = coin_balances["coin"]
            sell_tx_result = await amm.sell(sell_size)
            print("Sold", size)
            return sell_tx_result
        except Exception as e:
            time.sleep(0.4)
            tries += 1
            print(f"Failed to sell, attempt {tries}")
            continue


async def trade(
    amm,
    size,
    trade_open_time,  # unix timestamp
    trade_length,  # seconds
):
    sol_now = await amm.get_balance()
    sol_now = sol_now["sol"]
    if trade_open_time == -100:
        # go now
        trade_length = 20
        b_tx = await buy_leg(amm, size)
        # Get balances and sell
        time.sleep(trade_length)
        s_tx = await sell_leg(amm, size)
        time.sleep(5)
    else:
        # check if the current time is >= trade_open_time
        while time.time() < trade_open_time:
            time.sleep(0.1)
        # go now
        trade_length = 20
        b_tx = await buy_leg(amm, size)
        # Get balances and sell
        time.sleep(trade_length)
        s_tx = await sell_leg(amm, size)
        time.sleep(5)
    sol_after = await amm.get_balance()
    sol_after = sol_after["sol"]
    trade_results = TradeResults(amm.pool_id)
    trade_results.b_tx = b_tx
    trade_results.s_tx = s_tx
    trade_results.sol_before = sol_now
    trade_results.sol_after = sol_after
    print(
        "Trade results:\n",
        "Profit",
        trade_results.sol_after - trade_results.sol_before,
        "\n",
    )


def trading_operation(pool_id, size, trade_open_time, trade_length):
    """The trading operation function for a given pool ID."""
    # Since we are using threads, we need to create a new event loop for each
    # thread to run in.
    this_amm = make_amm(pool_id)
    asyncio.new_event_loop().run_until_complete(
        trade(
            this_amm,
            size,
            trade_open_time,
            trade_length,
        )
    )


def execute_job(pool_id, size, trade_open_time, trade_length):
    """Wrapper function to execute a job."""
    try:
        trading_operation(pool_id, size, trade_open_time, trade_length)
    except Exception as e:
        print(f"Error executing job for pool {pool_id}: {e}")


def main():
    pool_id = sys.argv[1]

    # Default values
    size = 1
    trade_open_time = -100
    trade_length = 20

    # Process each argument for optional parameters
    for arg in sys.argv[2:]:
        if arg.startswith("size:"):
            size = float(arg.split(":")[1])
        elif arg.startswith("time:"):
            trade_open_time = float(arg.split(":")[1])
        elif arg.startswith("length:"):
            trade_length = float(arg.split(":")[1])

    # Submit a new job to the executor
    execute_job(pool_id, size, trade_open_time, trade_length)


if __name__ == "__main__":
    main()
