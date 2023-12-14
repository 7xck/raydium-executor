import pandas as pd

# start time
START_TIME = pd.Timestamp.now()
import asyncio
import time
import sys
import traceback
from sqlalchemy import create_engine
import datetime

from exchanges.raydium_amm import Liquidity
from models.trade_results import TradeResults
from utils.utils import load_config
from solana.rpc.core import RPCException

# Configuration file for setup
CONFIG_FILE = "config.json"
config = load_config(CONFIG_FILE)

# Default Pool ID if not provided as command line argument
DEFAULT_POOL_ID = "2CTX11qNHNmiCt74H14vVSfn9RgtCUraEkuAgSbTAdZt"
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
    buy_tx_result = await amm.buy(size)
    print("Bought", size)
    return buy_tx_result


async def sell_leg(amm, trade_results, half=False):
    tries = 0
    reduce_size = 0
    while True:
        try:
            while True:
                coin_balances = await amm.get_balance()
                print(coin_balances)
                if coin_balances["coin"] < 1:
                    print("Don't own coin, waiting 1")
                    time.sleep(1)
                    continue
                else:
                    trade_results.sol_before = coin_balances["sol"]
                    break
            if half:
                # round to floor
                sell_size = int(coin_balances["coin"] * 0.6)
            else:
                sell_size = coin_balances["coin"] - reduce_size
            sell_tx_result = await amm.sell(sell_size)
            print("Sold", sell_size)
            return sell_tx_result
        except Exception as e:
            time.sleep(0.4)
            tries += 1
            print(f"Failed to sell, attempt {tries}")
            reduce_size = 1
            continue


async def buy_leg_reversed_mints(amm, size=1):
    # we're selling 1 sol to buy the coin
    buy_tx_result = await amm.sell(size)
    print("Bought", size)
    return buy_tx_result


async def sell_leg_reversed_mints(amm, trade_results, half=False, balances=None):
    tries = 0
    reduce_size = 0
    while True:
        try:
            while True:
                coin_balances = await amm.get_balance()
                print(coin_balances)
                if coin_balances["sol"] < 1:
                    print("Don't own coin, waiting 1")
                    time.sleep(1)
                    continue
                else:
                    trade_results.sol_before = coin_balances["coin"]
                    break
            if half:
                # round to floor
                sell_size = int(coin_balances["sol"] * 0.6)
            else:
                sell_size = coin_balances["sol"] - reduce_size
            sell_tx_result = await amm.buy(sell_size)
            print("Sold", sell_size)
            return sell_tx_result
        except Exception as e:
            time.sleep(0.4)
            tries += 1
            print(f"Failed to sell, attempt {tries}")
            reduce_size = 1
            continue


async def handle_trade(amm, size, trade_length, buy_func, sell_func):
    print("Buying...")
    b_tx = await buy_func(amm, size)
    # get buy time
    trade_results = TradeResults(amm.pool_id)
    print("Putting a trade on...")
    trade_results.buy_time = pd.Timestamp.now()
    time.sleep(trade_length)
    s_tx = await sell_func(amm, trade_results)
    trade_results.sell_time = pd.Timestamp.now()
    print("Sold position, first")
    time.sleep(15)
    if amm.pool_keys["str_quote_mint"] == amm.sol_mint:
        sol_after = await amm.get_balance()
        sol_after = sol_after["sol"]
    else:
        sol_after = await amm.get_balance()
        sol_after = sol_after["coin"]
    trade_results.b_tx = b_tx.to_json()
    trade_results.s_tx = s_tx.to_json()
    trade_results.sol_after = sol_after
    print(
        "Trade results:\n",
        "Profit",
        trade_results.sol_after - (trade_results.sol_before + size),
        "\n",
        "% Ret",
        trade_results.sol_after / (trade_results.sol_before + size) - 1,
        "\n",
        "Time it took from start to buy",
        trade_results.buy_time - START_TIME,
        "\n",
        "Time it took from start to sell",
        trade_results.sell_time - START_TIME,
        "\n",
    )
    trade_results.save(ENGINE)


async def trade(
    amm,
    size,
    trade_length,  # seconds
):
    if amm.pool_keys["str_quote_mint"] == amm.sol_mint:
        await handle_trade(amm, size, trade_length, buy_leg, sell_leg)
    else:
        await handle_trade(
            amm, size, trade_length, buy_leg_reversed_mints, sell_leg_reversed_mints
        )


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


def main():
    if len(sys.argv) < 2:
        pool_id = DEFAULT_POOL_ID
    else:
        pool_id = sys.argv[1]

    # Default values
    size = 0.5
    trade_open_time = -100
    trade_length = 5

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
    try:
        trading_operation(pool_id, size, trade_open_time, trade_length)
    except Exception as e:
        traceback.print_exc()
        print(f"Error executing job for pool {pool_id}: {e}")


if __name__ == "__main__":
    main()
