from solders.pubkey import Pubkey as PublicKey
from solders.keypair import Keypair
from solana.rpc.commitment import Commitment
from solana.rpc.async_api import AsyncClient
from solana.rpc.api import Client
from solana.transaction import Instruction as TransactionInstruction
from solana.transaction import AccountMeta, Transaction
from solana.rpc.types import TxOpts
import utils.account_helpers
import utils.layouts

TOKEN_PROGRAM_ID = PublicKey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ALTERNATE_SERUM_ID = PublicKey.from_string(
    "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin"
)
AMM_PROGRAM_ID = PublicKey.from_string("675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8")


class RaydiumExecutor:
    """
    RaydiumExecutor is a class that allows you to interact with the Raydium AMM
    rpc_endpoint: str: the rpc endpoint for the solana network
    pool_id: str: the pool id for the AMM
    wallet_secret: str: the secret key for the wallet
    wallet_address: str: the public key for the wallet
    pool_keys: dict: the keys for the pool. Can get from the Raydium API, or onchain.
    """
    def __init__(self,
                 rpc_endpoint: str,
                 pool_id: str,
                 wallet_secret: str,
                 wallet_address: str,
                 pool_keys: dict
                 ):
        self.rpc_endpoint = rpc_endpoint
        self.pool_id = pool_id  # string
        self.client = Client(rpc_endpoint, commitment=Commitment("confirmed"))
        self.conn = AsyncClient(self.rpc_endpoint, commitment=Commitment("confirmed"))
        self.pool_keys = pool_keys
        self.pool_pubkeys = {key: PublicKey.from_string(value) if isinstance(value,str) else value for key, value in pool_keys.items()}
        self.serum_program_id = PublicKey.from_string("srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX")
        self.owner = Keypair.from_base58_string(wallet_secret)
        self.wallet_address = wallet_address
        self.wallet_secret = wallet_secret
        # grab token accounts
        self.base_token_account = utils.account_helpers.create_account(
            self.wallet_secret,
            self.wallet_address,
            self.pool_keys["program_id"],
            self.pool_keys["base_mint"],
        )
        self.quote_token_account = utils.account_helpers.create_account(
            self.wallet_secret,
            self.wallet_address,
            self.pool_keys["program_id"],
            self.pool_keys["quote_mint"],
        ) # grabs the token account if it exists, otherwise makes it (this can take a while)

    def make_swap_instruction(self,
                              amount_in: int,
                              token_account_in: PublicKey,
                              token_account_out: PublicKey,
                              ) -> TransactionInstruction:
        """
        :param amount_in: amount of tokens to swap. Remember that this is pre-decimalized (i.e. 1 SOL = 10^9 lamports)
        :param token_account_in: token account to swap from
        :param token_account_out: token account to swap to
        :return: TransactionInstruction
        """
        # Swap instruction
        keys = self.format_accounts(token_account_in, token_account_out)
        data = utils.layouts.SWAP_LAYOUT.build(
            dict(instruction=9, amount_in=int(amount_in), min_amount_out=0)
        )
        return TransactionInstruction(
            accounts=keys,
            program_id=AMM_PROGRAM_ID,
            data=data
        )

    async def buy(self, amount, decimals="quote_decimals"):
        """
        :param amount: amount of tokens to buy (post-decimal) i.e. 0.5 sol or 1 sol
        :param decimals: choose where
        to get the decimalisation from. i.e "quote_decimals" or "base_decimals". Default is "quote_decimals". It is
        included in the pool keys from raydium.
        :return: None
        """
        swap_tx = Transaction()
        signers = [self.owner]
        token_account_in = self.quote_token_account
        token_account_out = self.base_token_account
        amount_in = amount * 10 ** self.pool_keys[decimals]
        swap_tx.add(
            self.make_swap_instruction(
                amount_in=amount_in,
                token_account_in=token_account_in,
                token_account_out=token_account_out
            )
        )
        opts = TxOpts(skip_preflight=True)
        await self.conn.send_transaction(swap_tx, *signers, opts=opts)

    async def sell(self, amount, decimals="base_decimals"):
        swap_tx = Transaction()
        signers = [self.owner]
        token_account_in = self.base_token_account
        token_account_out = self.quote_token_account
        amount_in = amount * 10 ** self.pool_keys[decimals]
        swap_tx.add(
            self.make_swap_instruction(
                amount_in=amount_in,
                token_account_in=token_account_in,
                token_account_out=token_account_out
            )
        )
        opts = TxOpts(skip_preflight=True)
        return await self.conn.send_transaction(swap_tx, *signers, opts=opts)

    def format_accounts(self, token_account_in: PublicKey, token_account_out: PublicKey):
        accounts = self.pool_pubkeys
        return [
            AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
            AccountMeta(pubkey=accounts["id"], is_signer=False, is_writable=True),
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
            AccountMeta(pubkey=self.serum_program_id, is_signer=False, is_writable=False),
            AccountMeta(
                pubkey=accounts["market_id"], is_signer=False, is_writable=True
            ),
            AccountMeta(pubkey=accounts["market_bids"], is_signer=False, is_writable=True),
            AccountMeta(pubkey=accounts["market_asks"], is_signer=False, is_writable=True),
            AccountMeta(
                pubkey=accounts["market_event_queue"], is_signer=False, is_writable=True
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

    async def get_balances(self):
        """
        Gets you the balances for the base and quote tokens of the pool
        :return: dict: the balances of the base and quote tokens
        """
        base_token_balance = await self.conn.get_token_account_balance(
            self.base_token_account
        )
        quote_token_balance = await self.conn.get_token_account_balance(
            self.quote_token_account
        )
        return {
            self.pool_keys['base_mint']: base_token_balance.value.ui_amount,
            self.pool_keys['quote_mint']: quote_token_balance.value.ui_amount
        }