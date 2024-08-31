import json, time
from solana.rpc.types import TxOpts
from solana.transaction import AccountMeta, Signature, Transaction
from solders.instruction import Instruction, CompiledInstruction  # type: ignore
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price  # type: ignore
from solders.keypair import Keypair  # type: ignore
from solders.pubkey import Pubkey  # type: ignore
from solders.transaction import VersionedTransaction  # type: ignore
from solders.message import MessageV0  # type: ignore
from spl.token.instructions import close_account, CloseAccountParams
from spl.token.constants import TOKEN_2022_PROGRAM_ID
from loguru import logger
from utils.blockchain import SolanaClient
from utils.config import (
    TEST_AMM_KEY,
    WSOL,
    TOKEN_PROGRAM_ID,
    UNIT_BUDGET,
    UNIT_PRICE,
    RAYDIUM_CPMM_AUTHORITY,
    RAYDIUM_CPMM,
    RAYDIUM_LIQUIDITY_POOL,
)
from utils.extractor import SWAP_LAYOUT


class RaydiumClient(SolanaClient):
    """Raydium helper"""

    def __init__(self, keys: str = None) -> None:
        super().__init__(keys=keys)

    def make_swap_instruction(
        self,
        amount_in: int,
        token_account_in: Pubkey,
        token_account_out: Pubkey,
        account: dict,
        owner: Keypair,
    ) -> Instruction:

        data = SWAP_LAYOUT.build(dict(amountInMax=int(amount_in), amountOut=0))
        swap_instruction = Instruction(
            RAYDIUM_CPMM,
            accounts=[
                AccountMeta(pubkey=owner.pubkey(), is_signer=True, is_writable=False),
                AccountMeta(
                    pubkey=RAYDIUM_CPMM_AUTHORITY, is_signer=False, is_writable=False
                ),
                AccountMeta(
                    pubkey=account["configId"], is_signer=False, is_writable=False
                ),
                AccountMeta(pubkey=TEST_AMM_KEY, is_signer=False, is_writable=True),
                AccountMeta(pubkey=token_account_in, is_signer=False, is_writable=True),
                AccountMeta(
                    pubkey=token_account_out, is_signer=False, is_writable=True
                ),
                AccountMeta(
                    pubkey=account["vaultA"], is_signer=False, is_writable=True
                ),
                AccountMeta(
                    pubkey=account["vaultB"], is_signer=False, is_writable=True
                ),
                AccountMeta(
                    pubkey=account["mintProgramA"], is_signer=False, is_writable=False
                ),
                AccountMeta(
                    pubkey=account["mintProgramB"], is_signer=False, is_writable=False
                ),
                AccountMeta(
                    pubkey=account["mintA"], is_signer=False, is_writable=False
                ),
                AccountMeta(
                    pubkey=account["mintB"], is_signer=False, is_writable=False
                ),
                AccountMeta(
                    pubkey=account["observationId"], is_signer=False, is_writable=True
                ),
            ],
            data=data,
        )
        return swap_instruction

    async def make_sell_swap(self, pair: Pubkey, amount_in_lamports: int, mint: str):
        pool_keys = await self.pool_info(TEST_AMM_KEY)
        # Convert amount to integer
        amount_in = int(amount_in_lamports)
        token_account = await self.get_token_account(mint)

        # Get wSOL token account and instructions
        wsol_token_account, wsol_token_account_instructions = (
            await self.get_token_accounts(WSOL)
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

        print(swap_instructions)
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
            [instruction for instruction in instructions],
            [],
            (await self.client.get_latest_blockhash()).value.blockhash,
        )

        # # Create and send transaction
        # logger.info("Creating and sending transaction...")
        transaction = VersionedTransaction(compiled_message, [self.keypair])

        txn_sig = await self.client.send_transaction(
            transaction,
            # self.keypair,
            opts=TxOpts(skip_preflight=False, preflight_commitment="confirmed"),
        )
        logger.info("Transaction Signature:", txn_sig.value)
        return
