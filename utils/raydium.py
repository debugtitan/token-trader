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
    WSOL,
    LAMPORTS_PER_SOL,
    TOKEN_PROGRAM_ID,
    UNIT_BUDGET,
    UNIT_PRICE,
    RAYDIUM_CPMM_AUTHORITY,
    RAYDIUM_CPMM,
    BASE_VAULT,
    QUOTE_VAULT,
)
from utils.extractor import ACCOUNT_LAYOUT, SWAP_LAYOUT


class RaydiumClient(SolanaClient):
    """Raydium helper"""

    def __init__(self, keys: str = None) -> None:
        super().__init__(keys=keys)

    def make_swap_instruction(
        self,
        amount_in: int,
        amm_id: Pubkey,
        token_account_in: Pubkey,
        token_account_out: Pubkey,
        owner: Keypair,
    ) -> Instruction:
        try:
            keys = [
                AccountMeta(
                    pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False
                ),
                AccountMeta(pubkey=amm_id, is_signer=False, is_writable=True),
                AccountMeta(
                    pubkey=RAYDIUM_CPMM_AUTHORITY, is_signer=False, is_writable=False
                ),
                AccountMeta(pubkey=BASE_VAULT, is_signer=False, is_writable=True),
                AccountMeta(pubkey=QUOTE_VAULT, is_signer=False, is_writable=True),
                AccountMeta(pubkey=token_account_in, is_signer=False, is_writable=True),
                AccountMeta(
                    pubkey=token_account_out, is_signer=False, is_writable=True
                ),
                AccountMeta(pubkey=owner.pubkey(), is_signer=True, is_writable=False),
            ]

            data = SWAP_LAYOUT.build(
                dict(instruction=9, amount_in=int(amount_in), min_amount_out=0)
            )
            return Instruction(RAYDIUM_CPMM, data, keys)
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

    async def make_sell_swap(self, pair: Pubkey, amount_in_lamports: int, mint: str):

        # Convert amount to integer
        amount_in = int(amount_in_lamports)
        token_account = await self.get_token_account(mint)

        # Get wSOL token account and instructions
        wsol_token_account, wsol_token_account_instructions = (
            await self.get_token_accounts(WSOL)
        )

        logger.info("Creating swap instructions...")
        swap_instructions = self.make_swap_instruction(
            amount_in,
            pair,
            token_account,
            wsol_token_account,
            self.keypair,
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
            (await self.client.get_latest_blockhash()).value.blockhash,
        )

        # Create and send transaction
        transaction = VersionedTransaction(compiled_message, [self.keypair])
        txn_sig = await self.client.send_transaction(
            transaction,
            opts=TxOpts(skip_preflight=True, preflight_commitment="confirmed"),
        )

        logger.info("Transaction Signature:", txn_sig.value)

        # # Confirm transaction
        # print("Confirming transaction...")
        # confirm = await self.confirm_txn(txn_sig.value)
        # print(confirm)
