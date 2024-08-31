from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TokenAccountOpts
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
)
from utils.extractor import CPMM_POOL_INFO_LAYOUT


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
        associate_token_address = get_associated_token_address(_pubkey, mint)
        token_balance = await self.client.get_token_account_balance(
            associate_token_address
        )
        return token_balance.value.ui_amount

    async def get_token_accounts(self, mint: str):
        _pubkey = self.keypair.pubkey()
        try:
            account_data = await self.client.get_token_accounts_by_owner(
                _pubkey, TokenAccountOpts(mint=Pubkey.from_string(mint))
            )
            token_account = account_data.value[0].pubkey
            token_account_instructions = None
            return token_account, token_account_instructions
        except:
            token_account = get_associated_token_address(
                _pubkey, Pubkey.from_string(mint)
            )
            token_account_instructions = create_associated_token_account(
                _pubkey, _pubkey, Pubkey.from_string(mint)
            )
            return token_account, token_account_instructions

    async def get_token_account(self, mint: str):
        return (
            (
                await self.client.get_token_accounts_by_owner_json_parsed(
                    self.keypair.pubkey(),
                    TokenAccountOpts(mint=mint),
                )
            )
            .value[0]
            .pubkey
        )

    async def pool_info(self, amm_id: str):
        amm_data = (await self.client.get_account_info_json_parsed(amm_id)).value.data
        pool = CPMM_POOL_INFO_LAYOUT.parse(amm_data)

        pool_keys = {
            "configId": Pubkey.from_bytes(pool.configId),
            "poolCreator": Pubkey.from_bytes(pool.poolCreator),
            "vaultA": Pubkey.from_bytes(pool.vaultA),
            "vaultB": Pubkey.from_bytes(pool.vaultB),
            "mintLp": Pubkey.from_bytes(pool.mintLp),
            "mintA": Pubkey.from_bytes(pool.mintA),
            "mintB": Pubkey.from_bytes(pool.mintB),
            "mintProgramA": Pubkey.from_bytes(pool.mintProgramA),
            "mintProgramB": Pubkey.from_bytes(pool.mintProgramB),
            "observationId": Pubkey.from_bytes(pool.observationId),
            "bump": pool.bump,
            "status": pool.status,
            "lpDecimals": pool.lpDecimals,
            "mintDecimalA": pool.mintDecimalA,
            "mintDecimalB": pool.mintDecimalB,
            "lpAmount": pool.lpAmount,
            "protocolFeesMintA": pool.protocolFeesMintA,
            "protocolFeesMintB": pool.protocolFeesMintB,
            "fundFeesMintA": pool.fundFeesMintA,
            "fundFeesMintB": pool.fundFeesMintB,
            "openTime": pool.openTime,
        }
        return pool_keys
