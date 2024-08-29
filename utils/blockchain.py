from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey  # type: ignore
from solders.keypair import Keypair  # type: ignore
from spl.token.instructions import get_associated_token_address
from loguru import logger
from utils.config import RPC_NODE


class SolanaClient:
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

    async def check_token_balance(self, mint: str):
        associate_token_address = get_associated_token_address(
            self.keypair.pubkey(), Pubkey.from_string(mint)
        )
        balance = await self.client.get_token_account_balance(associate_token_address)
        print(balance)
