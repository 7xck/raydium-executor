import asyncio
import json
import traceback
from typing import Any

from loguru import logger

from CEX import CEX
from raydium_amm import Liquidity
from utils import purchase_info, sale_info

logger.add("bot.csv", format="{time:YYYY-MM-DD HH:mm:ss},{level},{message}")

amm: Liquidity
cex: CEX
config: Any

# read json config file
with open("config.json") as f:
    config = json.load(f)


async def main():
    global amm
    amm = Liquidity(
        "https://api.mainnet-beta.solana.com",
        "5wyH6cE9qaNmxw9HyM2WVHZkQDXyrFVSgEMCDksbfjUP",
        config["private_key"],
        "xd/usd",
    )
    await amm.buy(0.5)


if __name__ == "__main__":
    asyncio.run(main())
