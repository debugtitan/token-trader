from typing import List, Union
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import MemcmpOpts, TokenAccountOpts
from solders.pubkey import Pubkey  # type: ignore
from solders.keypair import Keypair  # type: ignore
from spl.token.instructions import (
    get_associated_token_address,
    create_associated_token_account,
)

from loguru import logger
from utils.config import (
    LAMPORTS_PER_SOL,
    RPC_NODE,
    RAYDIUM_LIQUIDITY_POOL,
    TOKEN_PROGRAM_ID,
    WSOL,
    RAYDIUM_AUTHORITY,
    RAYDIUM_CPMM,
    RAYDIUM_CPMM_AUTHORITY,
)
from utils.extractor import AMM_INFO_LAYOUT_V4_1, MARKET_LAYOUT


class SolanaClient:
    client = AsyncClient(RPC_NODE)

    def __init__(self, keys: str = None) -> None:
        try:
            self.keypair = Keypair.from_base58_string(str(keys))
            # logger.info(f"Keypair successfully initialized.{self.keypair.pubkey()}")
        except Exception as e:
            logger.error("Class instance error")

    async def check_health(self):
        """
        Performs a health check by verifying the connection status of the client.

        Returns:
            bool: True if the client is connected, False otherwise.
        """
        return await self.client.is_connected()

    async def wallet_address(self):
        if not self.keypair:
            raise ValueError("No Keys passed")
        return self.keypair.pubkey()

    async def balance(self):
        balance = await self.client.get_balance(self.keypair.pubkey())
        return balance.value / LAMPORTS_PER_SOL

    async def check_token_balance(self, mint: str):
        _pubkey = self.keypair.pubkey()
        associate_token_address = get_associated_token_address(
            _pubkey, Pubkey.from_string(mint)
        )
        token_balance = await self.client.get_token_account_balance(
            associate_token_address
        )
        return token_balance.value.ui_amount

    async def get_token_accounts(self, mint: str):
        _pubkey = self.keypair.pubkey()
        mint = Pubkey.from_string(mint)
        try:
            account_data = await self.client.get_token_accounts_by_owner(
                _pubkey, TokenAccountOpts(mint=mint)
            )
            token_account = account_data.value[0].pubkey
            token_account_instructions = None
            return token_account, token_account_instructions
        except:
            token_account = get_associated_token_address(_pubkey, mint)
            token_account_instructions = create_associated_token_account(
                _pubkey, _pubkey, mint
            )
            return token_account, token_account_instructions

    async def get_token_account(self, mint: str):
        return (
            (
                await self.client.get_token_accounts_by_owner_json_parsed(
                    self.keypair.pubkey(),
                    TokenAccountOpts(mint=Pubkey.from_string(mint)),
                )
            )
            .value[0]
            .pubkey
        )
