import pandas as pd

# start time
START_TIME = pd.Timestamp.now()
import asyncio
import time
import sys
import traceback
from sqlalchemy import create_engine

from exchanges.raydium_amm import Liquidity
from models.trade_results import TradeResults
from utils.utils import load_config
from solana.rpc.core import RPCException

# Configuration file for setup
CONFIG_FILE = "config.json"
config = load_config(CONFIG_FILE)

# Default Pool ID if not provided as command line argument
DEFAULT_POOL_ID = "73D9amguiZY8ah79xuZxDmfBpqGi4TYW7SgJsJBNW5EZ"
ENGINE = create_engine(config["db"])


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
        START_TIME,
    )
    print("time it took to make amm", pd.Timestamp.now() - START_TIME)

    return amm


async def buy_leg(amm, size=1):
    try:
        buy_tx_result = await amm.buy(size)
        print("Bought", size)
        return buy_tx_result
    except RPCException as e:
        print("reduce size")
        size = size / 2
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
    trade_length,  # seconds
):
    trade_results = TradeResults(amm.pool_id)
    print("Putting a trade on...")
    sol_now = await amm.get_balance()
    sol_now = sol_now["sol"]
    print("Got SOL balance")
    # go now
    print("Buying...")
    b_tx = await buy_leg(amm, size)
    # get buy time
    trade_results.buy_time = pd.Timestamp.now()
    # Get balances and sell
    print("Sleeping until trade length expires...")
    time.sleep(trade_length)
    print("Time to exit...")
    s_tx = await sell_leg(amm, size)
    # add sell time
    trade_results.sell_time = pd.Timestamp.now()
    print("Sold position")
    print("Waiting for balance to update...")
    time.sleep(10)
    sol_after = await amm.get_balance()
    sol_after = sol_after["sol"]
    trade_results.b_tx = b_tx.to_json()
    trade_results.s_tx = s_tx.to_json()
    trade_results.sol_before = sol_now
    trade_results.sol_after = sol_after
    print(
        "Trade results:\n",
        "Profit",
        trade_results.sol_after - trade_results.sol_before,
        "\n",
        "% Ret",
        trade_results.sol_after / trade_results.sol_before - 1,
        "\n",
        "Time it took from start to buy",
        trade_results.buy_time - START_TIME,
        "\n",
        "Time it took from start to sell",
        trade_results.sell_time - START_TIME,
        "\n",
    )
    trade_results.save(ENGINE)


def trading_operation(pool_id, size, trade_open_time, trade_length):
    """The trading operation function for a given pool ID."""
    # Since we are using threads, we need to create a new event loop for each
    # thread to run in.
    while time.time() < trade_open_time:
        time.sleep(0.1)
    this_amm = make_amm(pool_id)
    print("made AMM", this_amm.pool_id)
    asyncio.new_event_loop().run_until_complete(
        trade(
            this_amm,
            size,
            trade_length,
        )
    )


def execute_job(pool_id, size, trade_open_time, trade_length):
    """Wrapper function to execute a job."""
    try:
        trading_operation(pool_id, size, trade_open_time, trade_length)
    except Exception as e:
        traceback.print_exc()
        print(f"Error executing job for pool {pool_id}: {e}")


def main():
    if len(sys.argv) < 2:
        pool_id = DEFAULT_POOL_ID
    else:
        pool_id = sys.argv[1]

    # Default values
    size = 1
    trade_open_time = -100
    trade_length = 35

    # Process each argument for optional parameters
    for arg in sys.argv[2:]:
        if arg.startswith("size:"):
            size = float(arg.split(":")[1])
        elif arg.startswith("time:"):
            trade_open_time = float(arg.split(":")[1])
        elif arg.startswith("length:"):
            trade_length = float(arg.split(":")[1])

    print("Set values of: size", size, "time", trade_open_time, "length", trade_length)

    # Submit a new job to the executor
    execute_job(pool_id, size, trade_open_time, trade_length)


if __name__ == "__main__":
    main()
