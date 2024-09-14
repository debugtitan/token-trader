import bs58 from "bs58"
import BN from "bn.js"
import * as fs from 'fs';
import { Connection, Keypair, PublicKey } from "@solana/web3.js"
import { getAssociatedTokenAddressSync } from "@solana/spl-token"
import { Raydium, TxVersion, CurveCalculator } from "@raydium-io/raydium-sdk-v2"
import dotenv from "dotenv";

dotenv.config({
    path: ".env",
});

type TradeDirection = "BUY" | "SELL"


function getRandomWallet(filePath: string = "Wallets.txt"): string {
    const data = fs.readFileSync(filePath, 'utf-8');
    const keys = data.split(/\r?\n/).filter(key => key.trim() !== '');
    const randomIndex = Math.floor(Math.random() * keys.length);
    return keys[randomIndex];
}

function getTradeAmount(walletHolding: number | null): number | 0 {
    if (walletHolding === null) {
        return 0;
    }
    const percentageToSell = Math.random() * (10 - 2) + 2; // random 2-10%
    const sellAmount = (percentageToSell / 100) * walletHolding;
    return sellAmount;
}

function getRandomTradeDirection(): TradeDirection {
    return Math.floor(Math.random() * 2) === 0 ? "BUY" : "SELL";
}

class RandomTrader {
    private solanaConnection: Connection;
    private wallet: Keypair;
    private raydium: Raydium | null = null;
    private MINT: PublicKey = new PublicKey("8Eewax7ooBdi5nwkp7VwittjEV9mVWAGhN1KVRJroeMR")
    private AMM_ID = "ATDyH3UarK8wEbjwKwzFgzvNsw7UCC2uaTWFaEHZAxLW"
    private WSOL: PublicKey = new PublicKey("So11111111111111111111111111111111111111112");
    allPoolKeysJson: any[] = [];

    constructor(secretKey: string) {
        this.solanaConnection = new Connection("https://aged-skilled-aura.solana-mainnet.quiknode.pro/f3204506cd69556a1bd269333d423d4978204581");
        this.wallet = Keypair.fromSecretKey(bs58.decode(secretKey));

    }

    /**
     * Initializes the Raydium instance by loading necessary data.
     * 
     * @returns {Promise<void>} A promise that resolves once the Raydium instance is successfully loaded.
     */

    /**get wallet token balance */
    async getTokenBalance() {
        const associateTokenAccount = getAssociatedTokenAddressSync(this.MINT, this.wallet.publicKey);
        return (await this.solanaConnection.getTokenAccountBalance(associateTokenAccount)).value.uiAmount
    }

    /** get wallet solana balance */
    async getBalance() {
        return await this.solanaConnection.getBalance(this.wallet.publicKey)
    }

    async main(direction: TradeDirection) {
        const raydium = await Raydium.load({
            connection: this.solanaConnection,
            owner: this.wallet,
            disableLoadToken: false
        });
        let swapResult;
        let baseIn: boolean;

        if (raydium == null) {
            return
        }
        const solBalance = await this.getBalance() / 10 ** 9
        const tokenBalance = await this.getTokenBalance()
        const tradeAmount = direction === "BUY" ? getTradeAmount(solBalance) : getTradeAmount(tokenBalance)
        console.log(`Wallet: ${this.wallet.publicKey}\nSOL: ${solBalance}\nTAKY: ${tokenBalance}\n${direction} Amount: ${tradeAmount}`)


        const outputAmount = new BN(tradeAmount * 10 ** 9)//
        const data = await raydium.cpmm.getPoolInfoFromRpc(this.AMM_ID)
        if (data == null) {
            return
        }
        const poolInfo = data.poolInfo
        const poolKeys = data.poolKeys
        const rpcData = data.rpcData

        if (poolInfo == null || rpcData == null) {
            return
        }

        if (direction === "BUY") {
            baseIn = true
            swapResult = CurveCalculator.swap(
                outputAmount,
                baseIn ? rpcData.baseReserve : rpcData.quoteReserve,
                baseIn ? rpcData.quoteReserve : rpcData.baseReserve,
                rpcData.configInfo!.tradeFeeRate
            )


        } else {
            baseIn = false
            swapResult = CurveCalculator.swap(
                outputAmount,
                baseIn ? rpcData.baseReserve : rpcData.quoteReserve,
                baseIn ? rpcData.quoteReserve : rpcData.baseReserve,
                rpcData.configInfo!.tradeFeeRate
            )
        }

        if (tradeAmount < 0.01) {
            console.log("amount less than 0.01", tradeAmount)
            return true
        }

        // ALWAYS NOTE ACTUAL AMOUNT MIGHT NOT BE SOLD "PRICE IMPACT, HIGH VOTALITY, LOW LIQUIDITY"
        const { execute } = await raydium.cpmm.swap({
            poolInfo,
            poolKeys,
            inputAmount: outputAmount,
            swapResult,
            slippage: 0.001, // range: 1skipPreflight: false,  ~ 0.0001, means 100% ~ 0.01%
            baseIn,
            // optional: set up priority fee here
            computeBudgetConfig: {
                units: 6000000,
                microLamports: 100000000,
            },
        })


        const blockHash = await this.solanaConnection.getLatestBlockhashAndContext("finalized")
        console.log(blockHash.value)
        const { txId } = await execute({ recentBlockHash: blockHash.value.blockhash, sendAndConfirm: false })
        console.log(`swapped: ${poolInfo.mintA.symbol} to ${poolInfo.mintB.symbol}:`, {
            txId: `https://solscan.io/tx/${txId}`,
        })
        return true

    }

}



(async () => {
    const tradeDirection = getRandomTradeDirection()
    const wallets = fs.readFileSync("Wallets.txt", 'utf-8').split('\n').map(wallet => wallet.trim()).filter(wallet => wallet !== '');
    console.log(`Trade Direction: ${tradeDirection}`, wallets)
})();

function waitForNextTrade(): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, 5000));
}




//while (canTrade) {
//     const wallet = getRandomWallet();
//     const direction = getRandomTradeDirection();
//     const trader = new RandomTrader(wallet);

//     // try {
//     //     const performTrade = await trader.main(direction);
//     //     console.log(`Trade has ended: ${performTrade}`);

//     //     if (performTrade) {
//     //         canTrade = true;
//     //     } else {
//     //         canTrade = false;
//     //     }
//     // } catch (error) {
//     //     console.log(`Error during trade: ${error}`);
//     //     canTrade = false;
//     // }

//     // if (!canTrade) {
//     //     console.log('Waiting before next trade...');
//     //     await waitForNextTrade();
//     //     canTrade = true;
//     // }
// }