import asyncio
import random
import time
from contextlib import suppress
from loguru import logger
from utils.raydium import RaydiumClient
from utils.config import TEST_TOKEN, TEST_AMM_KEY, read_private_keys


def get_sell_amount(wallet_holding: float):
    percentage_to_sell = random.uniform(2, 10)  # random 2-10%
    sell_amount = (percentage_to_sell / 100) * wallet_holding
    return sell_amount


async def main():
    """base runner"""
    wallets = read_private_keys()
    selected_key = random.choice(wallets)
    client = RaydiumClient(keys=selected_key)
    wallet_sol_balance = await client.balance()
    wallet_address = await client.wallet_address()
    wallet_token_balance = await client.check_token_balance(TEST_TOKEN)
    sell_holdings = get_sell_amount(wallet_token_balance)
    if sell_holdings <= 0:
        logger.error("Invalid sell amount. Aborting swap.")
        return
    logger.info(
        f"""Performing Sell \n\nWallet: {wallet_address}\nBal SOL: {wallet_sol_balance}\nToken Balance: {wallet_token_balance}\nAmount to sell: {sell_holdings}"""
    )
    await client.make_sell_swap(TEST_AMM_KEY, int(sell_holdings * 10**9))


if __name__ == "__main__":
    with suppress(KeyboardInterrupt) as error:
        while True:
            asyncio.run(main())
            time.sleep(60)
