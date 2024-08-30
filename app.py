import asyncio
import random
from contextlib import suppress

from solders.keypair import Keypair  # type: ignore
from loguru import logger
from utils.raydium import RaydiumClient
from utils.config import TEST_TOKEN, TEST_AMM_KEY, read_private_keys, TOKEN_SUPPLY


def check_supply_holdings(wallet_holding: float):
    if wallet_holding >= 0.3 * TOKEN_SUPPLY:
        return True
    return False


async def main():
    """base runner"""
    wallets = read_private_keys()
    selected_key = random.choice(wallets)
    client = RaydiumClient(keys=selected_key)
    wallet_sol_balance = await client.balance()
    wallet_address = await client.wallet_address()
    wallet_token_balance = await client.check_token_balance(TEST_TOKEN)
    minimum_wallet_holdings = check_supply_holdings(wallet_token_balance)
    logger.info(
        f"""Wallet: {wallet_address}\nBal SOL: {wallet_sol_balance}\nToken Balance: {wallet_token_balance}"""
    )
    if minimum_wallet_holdings:
        sell_percentage = random.uniform(0.02, 0.1)  # Randomly select 2-10%
        amount_to_sell = wallet_token_balance * sell_percentage
        await client.make_sell_swap(TEST_AMM_KEY)
        logger.info(
            f"Performing sell: {amount_to_sell} of {TEST_TOKEN} from wallet {wallet_address}."
        )
    else:
        logger.info(f"Wallet {wallet_address} skipped due to insufficient holdings.\nHoldings: {wallet_token_balance}")


if __name__ == "__main__":
    with suppress(KeyboardInterrupt) as error:
        asyncio.run(main())
