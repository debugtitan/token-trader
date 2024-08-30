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
    WSOL,
    RAYDIUM_AUTHORITY,
)
from utils.extractor import AMM_INFO_LAYOUT_V4_1, MARKET_LAYOUT


class SolanaClient:
    keypair = None
    client = AsyncClient(RPC_NODE)

    def __init__(self, rpc: str = RPC_NODE, keys: str = None) -> None:
        try:
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

    async def get_token_account(
        self, mint: str, ignore_keypair: bool = False, pubkey: str = None
    ):
        if ignore_keypair and not pubkey:
            raise ValueError("supply a keypair or pubkey")
        if not self.keypair and not ignore_keypair:
            raise ValueError("supply keypair or pubkey")
        _pubkey = (
            Pubkey.from_string(pubkey) if ignore_keypair else self.keypair.pubkey()
        )
        try:
            account_data = await self.client.get_token_accounts_by_owner(
                _pubkey, TokenAccountOpts(mint)
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

    async def pool_info(self, amm_id):
        data = (
            await self.client.get_account_info_json_parsed(Pubkey.from_string(str(amm_id)))
        ).value.data
        _data_decoded = AMM_INFO_LAYOUT_V4_1.parse(data)
        OPEN_BOOK_PROGRAM = Pubkey.from_bytes(_data_decoded.serumProgramId)
        marketId = Pubkey.from_bytes(_data_decoded.serumMarket)
        market_info = (
            await self.client.get_account_info_json_parsed(marketId)
        ).value.data

        pool_decoded = MARKET_LAYOUT.parse(market_info)
        pool_keys = {
            "amm_id": str(amm_id),
            "base_mint": str(Pubkey.from_bytes(pool_decoded.base_mint)),
            "quote_mint": str(Pubkey.from_bytes(pool_decoded.quote_mint)),
            "lp_mint": str(Pubkey.from_bytes(_data_decoded.lpMintAddress)),
            "version": 4,
            "base_decimals": _data_decoded.coinDecimals,
            "quote_decimals": _data_decoded.pcDecimals,
            "lpDecimals": _data_decoded.coinDecimals,
            "programId": str(RAYDIUM_LIQUIDITY_POOL),
            "authority": str(RAYDIUM_AUTHORITY),
            "open_orders": str(Pubkey.from_bytes(_data_decoded.ammOpenOrders)),
            "target_orders": str(Pubkey.from_bytes(_data_decoded.ammTargetOrders)),
            "base_vault": str(Pubkey.from_bytes(_data_decoded.poolCoinTokenAccount)),
            "quote_vault": str(Pubkey.from_bytes(_data_decoded.poolPcTokenAccount)),
            "withdrawQueue": str(Pubkey.from_bytes(_data_decoded.poolWithdrawQueue)),
            "lpVault": str(Pubkey.from_bytes(_data_decoded.poolTempLpTokenAccount)),
            "marketProgramId": str(OPEN_BOOK_PROGRAM),
            "market_id": str(marketId),
            "market_authority": str(
                Pubkey.create_program_address(
                    [bytes(marketId)]
                    + [bytes([pool_decoded.vault_signer_nonce])]
                    + [bytes(7)],
                    OPEN_BOOK_PROGRAM,
                )
            ),
            "market_base_vault": str(Pubkey.from_bytes(pool_decoded.base_vault)),
            "market_quote_vault": str(Pubkey.from_bytes(pool_decoded.quote_vault)),
            "bids": str(Pubkey.from_bytes(pool_decoded.bids)),
            "asks": str(Pubkey.from_bytes(pool_decoded.asks)),
            "event_queue": str(Pubkey.from_bytes(pool_decoded.event_queue)),
            "pool_open_time": _data_decoded.poolOpenTime,
        }
        logger.info(pool_keys)

    # AMM ID should be hard coded in a config
    async def fetch_amm_id(self, mint):

        memcmp_opts_1 = MemcmpOpts(offset=400, bytes=str(mint))
        memcmp_opts_2 = MemcmpOpts(offset=432, bytes=str(WSOL))
        filters: List[Union[int, MemcmpOpts]] = [752, memcmp_opts_1, memcmp_opts_2]
        resp = await self.client.get_program_accounts(
            Pubkey.from_string(str(RAYDIUM_LIQUIDITY_POOL)),
            encoding="base64",
            filters=filters,
        )
        return resp.value[0].pubkey
