from solana.rpc.api import Client
from spl.token.client import Token
from solana.transaction import Transaction
from solders.system_program import TransferParams, transfer
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.keypair import Keypair
from typing import Optional


class Solana_Simplified:
    def set_source_main_wallet_keypair(source_main_wallet_private_key: str):
        source_main_wallet_keypair = Keypair.from_base58_string(
            source_main_wallet_private_key
        )
        return source_main_wallet_keypair

    def set_main_wallet_publickey(main_wallet_address: str):
        main_wallet_public_key = Pubkey.from_string(main_wallet_address)
        return main_wallet_public_key

    def set_program_id_publickey(program_id: str):
        program_id_publickey = Pubkey.from_string(program_id)
        return program_id_publickey

    def set_token_address_publickey(token_address: str):
        token_address_publickey = Pubkey.from_string(token_address)
        return token_address_publickey

    def set_solana_client(
        development_url: Optional[
            str
        ] = "https://solana-mainnet.core.chainstack.com/00147e525c8e83a2f2c57f823fc40d96",
    ):
        solana_client = Client(development_url, timeout=30)
        return solana_client

    def set_spl_client(
        solana_client: Client,
        token_address_publickey: Pubkey,
        program_id_publickey: Pubkey,
        source_main_wallet_keypair: Keypair,
    ):
        spl_client = Token(
            conn=solana_client,
            pubkey=token_address_publickey,
            program_id=program_id_publickey,
            payer=source_main_wallet_keypair,
        )
        return spl_client

    def get_token_wallet_address_from_main_wallet_address(
        spl_client: Token, main_wallet_address: Pubkey
    ):
        try:
            token_wallet_address_public_key = (
                spl_client.get_accounts_by_owner(
                    owner=main_wallet_address, commitment=None, encoding="base64"
                )
                .value[0]
                .pubkey
            )
            print("Got the token account for the coin")
        except:
            token_wallet_address_public_key = (
                spl_client.create_associated_token_account(
                    owner=main_wallet_address,
                    skip_confirmation=False,
                    recent_blockhash=None,
                )
            )
            print("Created a token account for the coin")
        return token_wallet_address_public_key


def create_account(private_key, wallet_address, program_id, mint):
    main_wallet = wallet_address
    # program_id = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"  # eg: https://solscan.io/token/FpekncBMe3Vsi1LMkh6zbNq8pdM6xEbNiFsJBRcPbMDQ | FpekncBMe3Vsi1LMkh6zbNq8pdM6xEbNiFsJBRcPbMDQ
    # mint = "FucKu8jQcau6BkJkTSdUTC9KtuPCnToxvXnvnGcJe81D"  # eg: https://solscan.io/account/TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA | TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA
    source_main_wallet_keypair = Solana_Simplified.set_source_main_wallet_keypair(
        private_key
    )
    sender_pubkey = Solana_Simplified.set_main_wallet_publickey(main_wallet)
    program_pubkey = Solana_Simplified.set_program_id_publickey(program_id)
    token_address_pubkey = Solana_Simplified.set_token_address_publickey(mint)

    # set clients
    solana_client = Solana_Simplified.set_solana_client()
    spl_client = Solana_Simplified.set_spl_client(
        solana_client, token_address_pubkey, program_pubkey, source_main_wallet_keypair
    )

    # set and check sender token account
    sender_token_pubkey = (
        Solana_Simplified.get_token_wallet_address_from_main_wallet_address(
            spl_client, sender_pubkey
        )
    )

    return sender_token_pubkey
