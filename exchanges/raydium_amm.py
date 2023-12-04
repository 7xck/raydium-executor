import asyncio
import re
from ast import literal_eval
import pandas as pd

from solders.keypair import Keypair
from solders.pubkey import Pubkey as PublicKey
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Commitment
from solana.transaction import AccountMeta, Transaction
from solana.transaction import Instruction as TransactionInstruction
from solana.rpc.types import TxOpts
from solana.rpc.api import Client
import json
import solana
import numpy as np
import threading
import requests

from utils.create_token_address import create_account
from utils.layouts import SWAP_LAYOUT, POOL_INFO_LAYOUT
from utils.utils import fetch_pool_keys, get_token_account

SERUM_VERSION = 3
AMM_PROGRAM_VERSION = 4

AMM_PROGRAM_ID = PublicKey.from_string("675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8")
TOKEN_PROGRAM_ID = PublicKey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
SERUM_PROGRAM_ID = PublicKey.from_string("srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX")
ALTERNATE_SERUM_ID = PublicKey.from_string(
    "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin"
)
explorerULRTx = "https://explorer.solana.com/tx/"

LIQUIDITY_FEES_NUMERATOR = 25
LIQUIDITY_FEES_DENOMINATOR = 10000


def compute_sell_price(pool_info):
    reserve_in = pool_info["pool_coin_amount"]
    reserve_out = pool_info["pool_pc_amount"]

    amount_in = 1 * 10 ** pool_info["coin_decimals"]
    fee = amount_in * LIQUIDITY_FEES_NUMERATOR / LIQUIDITY_FEES_DENOMINATOR
    amount_in_with_fee = amount_in - fee
    denominator = reserve_in + amount_in_with_fee
    amount_out = reserve_out * amount_in_with_fee / denominator
    return amount_out / 10 ** pool_info["pc_decimals"]


def compute_buy_price(pool_info):
    reserve_in = pool_info["pool_pc_amount"]
    reserve_out = pool_info["pool_coin_amount"]

    amount_out = 1 * 10 ** pool_info["coin_decimals"]

    denominator = reserve_out - amount_out
    amount_in_without_fee = reserve_in * amount_out / denominator
    amount_in = (
        amount_in_without_fee * LIQUIDITY_FEES_DENOMINATOR / LIQUIDITY_FEES_DENOMINATOR
        - LIQUIDITY_FEES_NUMERATOR
    )
    return amount_in / 10 ** pool_info["pc_decimals"]


class Liquidity:
    def __init__(
        self,
        rpc_endpoint: str,
        pool_id: str,
        secret_key: str,
        symbol: str,
        wallet_address: str,
        start_time,
    ):
        self.endpoint = rpc_endpoint
        self.client = Client(self.endpoint, commitment=Commitment("confirmed"))
        self.pool_id = pool_id
        self.is_active = self.get_dexscreener_stats()  # self.get_trade_activity()
        if not self.is_active:
            raise Exception("POOL IS ILLIQUID AF, ABORTING")
        print("Started fetching pool keys", pd.Timestamp.now() - start_time)
        self.pool_keys = fetch_pool_keys(self.pool_id)
        self.base_mint_str = self.pool_keys["str_base_mint"]
        print("Finished fetching pool keys", pd.Timestamp.now() - start_time)
        self.owner = Keypair.from_base58_string(secret_key)
        self.secret_key = secret_key
        self.wallet_address = wallet_address
        self.base_symbol, self.quote_symbol = symbol.split("/")
        self.sol_mint = "So11111111111111111111111111111111111111112"
        self.sol_pubkey = "4ec6WNxekXf9YoiBTXWnGhE5jfTSLTnsTU7EqPvEiBdA"
        self.open()
        print("Finished initializing liquidity pool")
        print("Trying to set token accounts...")
        self._get_accounts()

    def get_trade_activity(self):
        self._check_trade_validity()
        self.df_processedTx = pd.DataFrame(self.processedTxArr)
        self.df_processedTx = self.df_processedTx.sort_values(
            "blockTime", ascending=True
        )
        # get median time between transactions
        self.df_processedTx["time_diff"] = self.df_processedTx["blockTime"].diff()
        self.median_time_diff = self.df_processedTx["time_diff"].median()
        is_active = self.median_time_diff > pd.Timedelta(seconds=30)
        return is_active

    def get_dexscreener_stats(self):
        # use pool ID to hit api
        response = requests.get(
            url="https://api.dexscreener.com/latest/dex/pairs/solana/" + self.pool_id
        )
        target_stats = response.json()["pair"]
        # a couple checks to make sure we aren't gonna get fucked
        if sum(target_stats["txns"]["h1"].values()) < 20:
            print("Not enough txns in 1h")
            return False
        if sum(target_stats["txns"]["m5"].values()) < 10:
            print("not enough txns in 5m")
            return False
        if target_stats["volume"]["h1"] < 1000:
            print("not enough $volume in m5")
            return False
        return True

    def open(self):
        self.conn = AsyncClient(self.endpoint, commitment=Commitment("confirmed"))
        print("Made ASYNC client connection")

    async def close(self):
        await self.conn.close()
        print("Closed ASYNC client connection")

    def _check_trade_validity(self):
        lastSignature = None
        resultArr = []
        rounds = 0
        txCount = 0
        maxTxCount = 30

        def getTxDetail(txSignature):
            txSignature2 = solana.transaction.Signature.from_string(txSignature)
            tx = self.client.get_transaction(
                txSignature2, max_supported_transaction_version=0
            )
            tx = json.loads(tx.to_json())
            postTokenBalances = tx["result"]["meta"]["postTokenBalances"]
            preTokenBalances = tx["result"]["meta"]["preTokenBalances"]
            if postTokenBalances != preTokenBalances:
                print(explorerULRTx + txSignature)
                resultArr.append(tx)

        RaydiumPubKey = solana.rpc.types.Pubkey.from_string(self.str_base_mint)
        while True:
            print("round-" + str(rounds + 1))
            print("getting transactions")
            RaydiumPubKey = solana.rpc.types.Pubkey.from_string(self.base_mint_str)
            txs = self.client.get_signatures_for_address(
                RaydiumPubKey, limit=200, before=lastSignature
            ).to_json()
            txs = json.loads(txs)["result"]
            print("processing signatures")
            signatures = np.array([o["signature"] for o in txs])

            threads = list()
            for signature in signatures:
                txCount += 1
                x = threading.Thread(target=getTxDetail, args=(signature,))
                threads.append(x)
                x.start()
            for index, thread in enumerate(threads):
                thread.join()
            if txCount >= maxTxCount:
                break
            else:
                rounds += 1
                lastSignature = solana.transaction.Signature.from_string(
                    txs[-1]["signature"]
                )
            print(txCount)
        self.processedTxArr = []
        for tx in resultArr:
            self.processedTxArr.append(self.processTx(tx))

    def _get_accounts(self):
        try:
            self.base_token_account = get_token_account(
                self.endpoint, self.owner.pubkey(), self.pool_keys["base_mint"]
            )
        except:
            print("have to create a token account....")
            self.base_token_account = create_account(
                self.secret_key,
                self.wallet_address,
                self.pool_keys["program_id"],
                self.pool_keys["str_base_mint"],
            )
        print("Got base token account", self.pool_keys["str_base_mint"])
        print("Getting quote token account", self.pool_keys["str_quote_mint"])
        if self.pool_keys["str_quote_mint"] == self.sol_mint:
            self.quote_token_account = PublicKey.from_string(self.sol_pubkey)
        else:
            try:
                self.quote_token_account = get_token_account(
                    self.endpoint, self.owner.pubkey(), self.pool_keys["quote_mint"]
                )
            except:
                print("have to create a token account...")
                self.quote_token_account = create_account(
                    self.secret_key,
                    self.wallet_address,
                    self.pool_keys["program_id"],
                    self.pool_keys["str_quote_mint"],
                )

    @staticmethod
    def make_simulate_pool_info_instruction(accounts):
        keys = [
            AccountMeta(pubkey=accounts["amm_id"], is_signer=False, is_writable=False),
            AccountMeta(
                pubkey=accounts["authority"], is_signer=False, is_writable=False
            ),
            AccountMeta(
                pubkey=accounts["open_orders"], is_signer=False, is_writable=False
            ),
            AccountMeta(
                pubkey=accounts["base_vault"], is_signer=False, is_writable=False
            ),
            AccountMeta(
                pubkey=accounts["quote_vault"], is_signer=False, is_writable=False
            ),
            AccountMeta(pubkey=accounts["lp_mint"], is_signer=False, is_writable=False),
            AccountMeta(
                pubkey=accounts["market_id"], is_signer=False, is_writable=False
            ),
        ]
        data = POOL_INFO_LAYOUT.build(dict(instruction=12, simulate_type=0))
        return TransactionInstruction(keys, AMM_PROGRAM_ID, data)

    def make_swap_instruction(
        self,
        amount_in: int,
        token_account_in: PublicKey,
        token_account_out: PublicKey,
        accounts: dict,
        serum_program_id=SERUM_PROGRAM_ID,
    ) -> TransactionInstruction:
        print("Making a swap instruction...")
        keys = [
            AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
            AccountMeta(pubkey=accounts["amm_id"], is_signer=False, is_writable=True),
            AccountMeta(
                pubkey=accounts["authority"], is_signer=False, is_writable=False
            ),
            AccountMeta(
                pubkey=accounts["open_orders"], is_signer=False, is_writable=True
            ),
            AccountMeta(
                pubkey=accounts["target_orders"], is_signer=False, is_writable=True
            ),
            AccountMeta(
                pubkey=accounts["base_vault"], is_signer=False, is_writable=True
            ),
            AccountMeta(
                pubkey=accounts["quote_vault"], is_signer=False, is_writable=True
            ),
            AccountMeta(pubkey=serum_program_id, is_signer=False, is_writable=False),
            AccountMeta(
                pubkey=accounts["market_id"], is_signer=False, is_writable=True
            ),
            AccountMeta(pubkey=accounts["bids"], is_signer=False, is_writable=True),
            AccountMeta(pubkey=accounts["asks"], is_signer=False, is_writable=True),
            AccountMeta(
                pubkey=accounts["event_queue"], is_signer=False, is_writable=True
            ),
            AccountMeta(
                pubkey=accounts["market_base_vault"], is_signer=False, is_writable=True
            ),
            AccountMeta(
                pubkey=accounts["market_quote_vault"], is_signer=False, is_writable=True
            ),
            AccountMeta(
                pubkey=accounts["market_authority"], is_signer=False, is_writable=False
            ),
            AccountMeta(pubkey=token_account_in, is_signer=False, is_writable=True),
            AccountMeta(pubkey=token_account_out, is_signer=False, is_writable=True),
            AccountMeta(pubkey=self.owner.pubkey(), is_signer=True, is_writable=False),
        ]
        print("Finished making, building SWAP LAYOUT...")
        data = SWAP_LAYOUT.build(
            dict(instruction=9, amount_in=int(amount_in), min_amount_out=0)
        )
        return TransactionInstruction(
            accounts=keys, program_id=AMM_PROGRAM_ID, data=data
        )

    async def buy(self, amount, decimals="quote_decimals"):
        try:
            swap_tx = Transaction()
            signers = [self.owner]
            token_account_in = self.quote_token_account
            token_account_out = self.base_token_account
            amount_in = amount * 10 ** self.pool_keys[decimals]
            print("About to add swap BUY instruction to tx...")
            swap_tx.add(
                self.make_swap_instruction(
                    amount_in, token_account_in, token_account_out, self.pool_keys
                )
            )
            opts = TxOpts(skip_preflight=True, max_retries=3)
            print("Built swap tx instructions, ")
            return await self.conn.send_transaction(swap_tx, *signers, opts=opts)
        except:
            print("LAST RESORT: Failed to build, trying to use alternate serum id")
            swap_tx = Transaction()
            signers = [self.owner]
            token_account_in = self.quote_token_account
            token_account_out = self.base_token_account
            amount_in = amount * 10 ** self.pool_keys[decimals]
            swap_tx.add(
                self.make_swap_instruction(
                    amount_in,
                    token_account_in,
                    token_account_out,
                    self.pool_keys,
                    ALTERNATE_SERUM_ID,
                )
            )
            return await self.conn.send_transaction(swap_tx, *signers)

    async def sell(self, amount, decimals="base_decimals"):
        try:
            print("Building sell tx...")
            swap_tx = Transaction()
            signers = [self.owner]
            token_account_in = self.base_token_account
            token_account_out = self.quote_token_account
            amount_in = amount * 10 ** self.pool_keys[decimals]
            print("About to add swap SELL instruction to tx...")
            swap_tx.add(
                self.make_swap_instruction(
                    amount_in,
                    token_account_in,
                    token_account_out,
                    self.pool_keys,
                    SERUM_PROGRAM_ID,
                )
            )
            print("built, sending now...")
            return await self.conn.send_transaction(swap_tx, *signers)
        except:
            print(
                "Failed to make swap instruction with serum program id, using alternate"
            )
            swap_tx = Transaction()
            signers = [self.owner]
            token_account_in = self.base_token_account
            token_account_out = self.quote_token_account
            amount_in = amount * 10 ** self.pool_keys[decimals]
            swap_tx.add(
                self.make_swap_instruction(
                    amount_in,
                    token_account_in,
                    token_account_out,
                    self.pool_keys,
                    ALTERNATE_SERUM_ID,
                )
            )
            return await self.conn.send_transaction(swap_tx, *signers)

    async def simulate_get_market_info(self):
        recent_block_hash = (await self.conn.get_recent_blockhash())["result"]["value"][
            "blockhash"
        ]
        tx = Transaction(
            recent_blockhash=recent_block_hash, fee_payer=self.owner.pubkey()
        )
        tx.add(self.make_simulate_pool_info_instruction(self.pool_keys))
        signers = [self.owner]
        tx.sign(*signers)
        res = (await self.conn.simulate_transaction(tx))["result"]["value"]["logs"][1]
        pool_info = literal_eval(re.search("({.+})", res).group(0))
        return pool_info

    async def get_prices(self):
        pool_info = await self.simulate_get_market_info()
        return round(compute_buy_price(pool_info), 4), round(
            compute_sell_price(pool_info), 4
        )

    async def get_balance(self):
        base_token_balance = await self.conn.get_token_account_balance(
            self.base_token_account
        )
        base_token_balance = base_token_balance.value.ui_amount
        quote_token_balance = await self.conn.get_token_account_balance(
            self.quote_token_account
        )
        quote_token_balance = quote_token_balance.value.ui_amount
        return {
            self.base_symbol: base_token_balance,
            self.quote_symbol: quote_token_balance,
        }

    async def wait_for_updated_balance(self, balance_before: dict):
        balance_after = await self.get_balance()
        while balance_after == balance_before:
            await asyncio.sleep(1)
            balance_after = await self.get_balance()
        return balance_after

    def processTx(tx):
        txSignature = tx["result"]["transaction"]["signatures"][0]
        txSender = tx["result"]["transaction"]["message"]["accountKeys"][0]
        blockTime = tx["result"]["blockTime"]
        slot = tx["result"]["slot"]
        postTokenBalances = tx["result"]["meta"]["postTokenBalances"]
        preTokenBalances = tx["result"]["meta"]["preTokenBalances"]
        tokenBalances = []
        for pre, post in zip(preTokenBalances, postTokenBalances):
            change = 0
            if not (
                post["uiTokenAmount"]["uiAmount"] is None
                or pre["uiTokenAmount"]["uiAmount"] is None
            ):
                change = (
                    post["uiTokenAmount"]["uiAmount"] - pre["uiTokenAmount"]["uiAmount"]
                )
            owner = pre["owner"]
            token = pre["mint"]
            if change != 0:
                tokenBalances.append({"owner": owner, "token": token, "change": change})
        result = {
            "txSignature": txSignature,
            "sender": txSender,
            "blockTime": blockTime,
            "slot": slot,
            "tokenBalances": tokenBalances,
        }
        return result
