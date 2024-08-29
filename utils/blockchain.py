from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey  # type: ignore
from solders.keypair import Keypair  # type: ignore
from spl.token.instructions import get_associated_token_address
from loguru import logger
from utils.config import LAMPORTS_PER_SOL, RPC_NODE


class SolanaClient:
    keypair = None

    def __init__(self, rpc: str = RPC_NODE, keys: str = None) -> None:
        try:
            self.client = AsyncClient(RPC_NODE)
            if keys:
                self.keypair = Keypair.from_base58_string(keys)
                logger.info(f"Keypair successfully initialized.{self.keypair.pubkey()}")
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

    async def balance(self, ignore_keypair=False, pubkey: str = None):
        if not self.keypair and not ignore_keypair:
            raise ValueError("No Keys passed")
        if ignore_keypair and not pubkey:
            raise ValueError("supply a keypair or pubkey")
        balance = await self.client.get_balance(
            Pubkey.from_string(str(pubkey)) if ignore_keypair else self.keypair.pubkey()
        )
        return balance.value / LAMPORTS_PER_SOL

    async def check_token_balance(
        self, mint: str, ignore_keypair: bool = False, pubkey: str = None
    ):
        if ignore_keypair and not pubkey:
            raise ValueError("supply a keypair or pubkey")
        if not self.keypair and not ignore_keypair:
            raise ValueError("supply keypair or pubkey")
        _pubkey = (
            Pubkey.from_string(pubkey) if ignore_keypair else self.keypair.pubkey()
        )
        associate_token_address = get_associated_token_address(
            _pubkey, Pubkey.from_string(mint)
        )
        token_balance = await self.client.get_token_account_balance(
            associate_token_address
        )
        return token_balance.value.ui_amount
