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
DEFAULT_POOL_ID = "Gre9Y65kJpZF4dFuyezfBzLxdcpq6dUs1fXZ5YU69SxL"
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


async def sell_leg(amm, half=False):
    tries = 0
    reduce_size = 0
    while True:
        try:
            coin_balances = await amm.get_balance()
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


async def sell_leg_reversed_mints(amm, half=False):
    tries = 0
    reduce_size = 0
    while True:
        try:
            coin_balances = await amm.get_balance()
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
    # go now
    trade_results.buy_time = pd.Timestamp.now()
    # Save sol balance
    if amm.pool_keys["str_quote_mint"] == amm.sol_mint:
        sol_now = await amm.get_balance()
        sol_now = sol_now["sol"]
    else:
        sol_now = await amm.get_balance()
        sol_now = sol_now["coin"]
    print("Got SOL balance")
    try:
        entry_price = amm.get_current_ds_price()
    except:
        entry_price = 1
    print("Sleeping until trade length expires or TP is hit...")
    # get time now + trade length
    # get current time
    now = datetime.datetime.now()
    trade_length = datetime.timedelta(seconds=trade_length)
    future_time = now + trade_length
    # get current price from dex screener
    tp = entry_price * 1.30
    while datetime.datetime.now() < future_time:
        try:
            # get current price
            try:
                latest_price = amm.get_current_ds_price()
            except:
                latest_price = entry_price
            print("got latest price", latest_price, "vs entry ", entry_price)
            print("current approx. return:", latest_price / entry_price - 1)
            # check if current price meets condition
            if latest_price >= tp:
                break
            # sleep for a while before checking again
            time.sleep(0.1)  # sleep for 1 second
        except Exception as e:
            print("error getting price", e)
            continue
    print("Time to exit...")
    s_tx = await sell_func(amm, half=True)
    trade_results.sell_time = pd.Timestamp.now()
    print("Sold position, first")
    time.sleep(15)
    s_tx_two = await sell_func(amm)
    trade_results.s_tx_two = s_tx_two.to_json()
    time.sleep(15)
    if amm.pool_keys["str_quote_mint"] == amm.sol_mint:
        sol_after = await amm.get_balance()
        sol_after = sol_after["sol"]
    else:
        sol_after = await amm.get_balance()
        sol_after = sol_after["coin"]
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
    size = 1
    trade_open_time = -100
    trade_length = 60

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
