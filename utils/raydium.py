import asyncio, json, time
from solana.rpc.types import TxOpts, TokenAccountOpts
from solana.transaction import AccountMeta, Signature
from solders.instruction import Instruction  # type: ignore
import solders.system_program as system_program
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price  # type: ignore
from solders.keypair import Keypair  # type: ignore
from solders.pubkey import Pubkey  # type: ignore
from solders.transaction import VersionedTransaction  # type: ignore
from solders.message import MessageV0  # type: ignore
from spl.token.client import Token
from spl.token.instructions import close_account, CloseAccountParams
import spl.token.instructions as spl_token_instructions
from loguru import logger
from utils.blockchain import SolanaClient
from utils.config import (
    RPC_NODE,
    WSOL,
    LAMPORTS_PER_SOL,
    TOKEN_PROGRAM_ID,
    UNIT_BUDGET,
    UNIT_PRICE,
    OPEN_BOOK_PROGRAM_ID,
    RAYDIUM_LIQUIDITY_POOL,
)
from utils.extractor import ACCOUNT_LAYOUT, SWAP_LAYOUT


class RaydiumClient(SolanaClient):
    """Raydium helper"""

    def __init__(self, keys: str = None) -> None:
        super().__init__(keys=keys)

    def make_swap_instruction(
        self,
        amount_in: int,
        token_account_in: Pubkey,
        token_account_out: Pubkey,
        accounts: dict,
        owner: Keypair,
    ) -> Instruction:
        try:
            keys = [
                AccountMeta(
                    pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False
                ),
                AccountMeta(
                    pubkey=accounts["amm_id"], is_signer=False, is_writable=True
                ),
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
                AccountMeta(
                    pubkey=OPEN_BOOK_PROGRAM_ID, is_signer=False, is_writable=False
                ),
                AccountMeta(
                    pubkey=accounts["market_id"], is_signer=False, is_writable=True
                ),
                AccountMeta(pubkey=accounts["bids"], is_signer=False, is_writable=True),
                AccountMeta(pubkey=accounts["asks"], is_signer=False, is_writable=True),
                AccountMeta(
                    pubkey=accounts["event_queue"], is_signer=False, is_writable=True
                ),
                AccountMeta(
                    pubkey=accounts["market_base_vault"],
                    is_signer=False,
                    is_writable=True,
                ),
                AccountMeta(
                    pubkey=accounts["market_quote_vault"],
                    is_signer=False,
                    is_writable=True,
                ),
                AccountMeta(
                    pubkey=accounts["market_authority"],
                    is_signer=False,
                    is_writable=False,
                ),
                AccountMeta(pubkey=token_account_in, is_signer=False, is_writable=True),
                AccountMeta(
                    pubkey=token_account_out, is_signer=False, is_writable=True
                ),
                AccountMeta(pubkey=owner.pubkey(), is_signer=True, is_writable=False),
            ]

            data = SWAP_LAYOUT.build(
                dict(instruction=9, amount_in=int(amount_in), min_amount_out=0)
            )
            return Instruction(RAYDIUM_LIQUIDITY_POOL, data, keys)
        except:
            return None

    async def confirm_txn(
        self, txn_sig: Signature, max_retries: int = 20, retry_interval: int = 3
    ) -> bool:
        retries = 0

        while retries < max_retries:
            try:
                txn_res = await self.client.get_transaction(
                    txn_sig,
                    encoding="json",
                    commitment="confirmed",
                    max_supported_transaction_version=0,
                )
                txn_json = json.loads(txn_res.value.transaction.meta.to_json())

                if txn_json["err"] is None:
                    logger.info("Transaction confirmed... try count:", retries)
                    return True

                logger.error("Error: Transaction not confirmed. Retrying...")
                if txn_json["err"]:
                    logger.error("Transaction failed.")
                    return False
            except Exception as e:
                logger.info("Awaiting confirmation... try count:", retries)
                retries += 1
                time.sleep(retry_interval)

        logger.error("Max retries reached. Transaction confirmation failed.")
        return None

    async def make_buy_swap(self, pair: Pubkey, amount_in_sol: float):
        pool_keys = await self.pool_info(pair)
        # Check if pool keys exist
        if pool_keys is None:
            logger.error("No pools keys found...")
            return None

        # Determine the mint based on pool keys
        mint = (
            pool_keys["base_mint"]
            if str(pool_keys["base_mint"]) != WSOL
            else pool_keys["quote_mint"]
        )

        # swap amount
        amount_in = int(amount_in_sol * LAMPORTS_PER_SOL)

        # Get token account and token account instructions
        logger.info("getting token account")
        token_account, token_account_instructions = await self.get_token_account(mint)

        # Get minimum balance needed for token account
        logger.info("Getting minimum balance for token account...")
        balance_needed = Token.get_min_balance_rent_for_exempt_for_account(self.client)

        # Create a keypair for wrapped SOL (wSOL)
        wsol_account_keypair = Keypair()
        wsol_token_account = wsol_account_keypair.pubkey()

        instructions = []

        # Create instructions to create a wSOL account, include the amount in
        logger.info("Creating wSOL account instructions...")
        create_wsol_account_instructions = system_program.create_account(
            system_program.CreateAccountParams(
                from_pubkey=self.keypair.pubkey(),
                to_pubkey=wsol_account_keypair.pubkey(),
                lamports=int(balance_needed + amount_in),
                space=ACCOUNT_LAYOUT.sizeof(),
                owner=TOKEN_PROGRAM_ID,
            )
        )

        # Initialize wSOL account
        print("Initializing wSOL account...")
        init_wsol_account_instructions = spl_token_instructions.initialize_account(
            spl_token_instructions.InitializeAccountParams(
                account=wsol_account_keypair.pubkey(),
                mint=WSOL,
                owner=self.keypair.pubkey(),
                program_id=TOKEN_PROGRAM_ID,
            )
        )

        # Create swap instructions
        logger.info("Creating swap instructions...")
        swap_instructions = self.make_swap_instruction(
            amount_in, wsol_token_account, token_account, pool_keys, self.keypair
        )

        # Create close account instructions for wSOL account
        close_account_instructions = close_account(
            CloseAccountParams(
                TOKEN_PROGRAM_ID,
                wsol_token_account,
                self.keypair.pubkey(),
                self.keypair.pubkey(),
            )
        )

        # Append instructions to the list
        instructions.append(set_compute_unit_limit(UNIT_BUDGET))
        instructions.append(set_compute_unit_price(UNIT_PRICE))
        instructions.append(create_wsol_account_instructions)
        instructions.append(init_wsol_account_instructions)
        if token_account_instructions:
            instructions.append(token_account_instructions)
        instructions.append(swap_instructions)
        instructions.append(close_account_instructions)

        # Compile the message
        compiled_message = MessageV0.try_compile(
            self.keypair.pubkey(),
            instructions,
            [],
            await self.client.get_latest_blockhash().value.blockhash,
        )

        # Create and send transaction
        logger.info("Creating and sending transaction...")
        transaction = VersionedTransaction(
            compiled_message, [self.keypair, wsol_account_keypair]
        )
        txn_sig = await self.client.send_transaction(
            transaction,
            opts=TxOpts(skip_preflight=True, preflight_commitment="confirmed"),
        )
        logger.info("Transaction Signature:", txn_sig.value)

        # Confirm transaction
        logger.info("Confirming transaction...")
        txn = self.confirm_txn(txn_sig.value)
        if txn:
            logger.info("Moving to next trade")
            return
        # TODO: retry

    async def make_sell_swap(self, pair: Pubkey, amount_in_lamports: int):

        # Convert amount to integer
        amount_in = int(amount_in_lamports)
        pool_keys = await self.pool_info(pair)
        if pool_keys is None:
            logger.info("No pools keys found...")
            return None

        # Determine the mint based on pool keys
        mint = (
            pool_keys["base_mint"]
            if str(pool_keys["base_mint"]) != WSOL
            else pool_keys["quote_mint"]
        )

        token_account = (
            await self.client.get_token_accounts_by_owner(
                self.keypair.pubkey(), TokenAccountOpts(mint)
            )
            .value[0]
            .pubkey
        )

        # Get wSOL token account and instructions
        wsol_token_account, wsol_token_account_instructions = (
            await self.get_token_account(WSOL)
        )

        logger.info("Creating swap instructions...")
        swap_instructions = self.make_swap_instruction(
            amount_in, token_account, wsol_token_account, pool_keys, self.keypair
        )

        close_account_instructions = close_account(
            CloseAccountParams(
                TOKEN_PROGRAM_ID,
                wsol_token_account,
                self.keypair.pubkey(),
                self.keypair.pubkey(),
            )
        )

        # Initialize instructions list
        instructions = []
        instructions.append(set_compute_unit_limit(UNIT_BUDGET))
        instructions.append(set_compute_unit_price(UNIT_PRICE))
        if wsol_token_account_instructions:
            instructions.append(wsol_token_account_instructions)
        instructions.append(swap_instructions)
        instructions.append(close_account_instructions)

        # Compile the message
        compiled_message = MessageV0.try_compile(
            self.keypair.pubkey(),
            instructions,
            [],
            await self.client.get_latest_blockhash().value.blockhash,
        )

        # Create and send transaction
        transaction = VersionedTransaction(compiled_message, [self.keypair])
        txn_sig = await self.client.send_transaction(
            transaction,
            opts=TxOpts(skip_preflight=True, preflight_commitment="confirmed"),
        )

        logger.info("Transaction Signature:", txn_sig.value)

        # Confirm transaction
        print("Confirming transaction...")
        confirm = await self.confirm_txn(txn_sig.value)
        print(confirm)
