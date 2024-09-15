import bs58 from "bs58"
import BN from "bn.js"
import * as fs from 'fs';
import { Connection, Keypair, PublicKey } from "@solana/web3.js"
import { getAssociatedTokenAddressSync } from "@solana/spl-token"
import { Raydium, CurveCalculator } from "@raydium-io/raydium-sdk-v2"
import { Config } from "./config"

type TradeDirection = "BUY" | "SELL"


function getTradeAmount(walletHolding: number | null): number | 0 {
    if (walletHolding === null) {
        return 0;
    }

    const minPercentage = Math.min(Config.randomTrade1, Config.randomTrade2);
    const maxPercentage = Math.max(Config.randomTrade1, Config.randomTrade2);
    const percentageToSell = Math.random() * (maxPercentage - minPercentage) + minPercentage;
    const sellAmount = (percentageToSell / 100) * walletHolding;
    return sellAmount;
}


async function makeSwap(direction: TradeDirection, secretKey: string, swapAmount: number) {
    const client = new Connection("https://aged-skilled-aura.solana-mainnet.quiknode.pro/f3204506cd69556a1bd269333d423d4978204581");

    const wallet = Keypair.fromSecretKey(bs58.decode(secretKey));
    const tradeAmount = swapAmount
    const raydium = await Raydium.load({
        connection: client,
        owner: wallet,
        disableLoadToken: false
    });
    let swapResult;
    let baseIn: boolean;

    if (raydium == null) {
        return
    }

    const outputAmount = new BN(tradeAmount * 10 ** 9)//
    const data = await raydium.cpmm.getPoolInfoFromRpc(Config.AMM_ID)
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
            units: 60000,
            microLamports: 1000000,
        },
    })


    const blockHash = await client.getLatestBlockhashAndContext("finalized")
    console.log(blockHash.value)
    const { txId } = await execute({ recentBlockHash: blockHash.value.blockhash, sendAndConfirm: false })
    console.log(`swapped: ${poolInfo.mintA.symbol} to ${poolInfo.mintB.symbol}:`, {
        txId: `https://solscan.io/tx/${txId}`,
    })
    return true

}


function getRandomTradeDirection(): TradeDirection {
    //return "SELL"
    return Math.floor(Math.random() * 2) === 0 ? "BUY" : "SELL";
}

async function getWalletBalance(secretKey: string): Promise<number> {
    const wallet = Keypair.fromSecretKey(bs58.decode(secretKey));
    const connection = new Connection('https://api.mainnet-beta.solana.com')
    const associateTokenAccount = getAssociatedTokenAddressSync(Config.MINT, wallet.publicKey);

    try {
        return (await connection.getTokenAccountBalance(associateTokenAccount)).value.uiAmount || 0;
    } catch (error) {
        return 0;
    }
};

async function getBalance(secretKey: string): Promise<number> {
    const wallet = Keypair.fromSecretKey(bs58.decode(secretKey));
    const connection = new Connection('https://api.mainnet-beta.solana.com')
    return await connection.getBalance(wallet.publicKey) / 10 ** 9 || 0
}

const getTotalSupply = async () => {
    const connection = new Connection('https://api.mainnet-beta.solana.com')
    return await connection.getTokenSupply(new PublicKey("8Eewax7ooBdi5nwkp7VwittjEV9mVWAGhN1KVRJroeMR"))

}

async function tokenTrader() {
    const tradeDirection = getRandomTradeDirection()

    // wallets
    const wallets = fs.readFileSync("Wallets.txt", 'utf-8').split('\n').map(wallet => wallet.trim()).filter(wallet => wallet !== '');

    console.log(`\nTrade Direction: ${tradeDirection}`)

    //fetch all wallet balance
    const balances = await Promise.all(wallets.map(secretKey => getWalletBalance(secretKey)));

    // total balance 
    const allWalletBalances: number = balances.reduce((accumulator, currentValue) => {
        return accumulator + currentValue
    }, 0);

    //SOL balances
    const solBalances = await Promise.all(wallets.map(secretKey => getBalance(secretKey)));

    //total sol balance
    const allSolBalances = solBalances.reduce((accumulator, currentValue) => {
        return accumulator + currentValue
    }, 0);


    //fetch token supply
    const tokenSupply = (await getTotalSupply()).value.uiAmount ?? 0

    //wallet percentage value
    const holdingPercentage = (allWalletBalances / tokenSupply) * 100;

    console.log(`Token Supply ${tokenSupply?.toLocaleString()}\n\nHoldings:${holdingPercentage.toFixed(2)}(%)\n\nBalances ${allWalletBalances.toLocaleString()}\n\nSOL: ${allSolBalances}\n`)

    let tradeAmount: number;

    // if direction is buy then continue
    if (tradeDirection === "SELL" && holdingPercentage > Config.sellPercentage) {
        //get our sell percentage
        const tokenHoldingToSell = getTradeAmount(allWalletBalances)
        const percentageSell = (tokenHoldingToSell / allWalletBalances) * 100

        console.log("Amount to sell", tokenHoldingToSell.toLocaleString(), "\nPercentage (%):", percentageSell.toFixed(2))


        //use this here to keep track of amount sold
        let remainingAmountToSell = tokenHoldingToSell;

        //logic checking each wallet has tokens to perfom transaction
        for (let i = 0; i < wallets.length && remainingAmountToSell > 0; i++) {
            const walletBalance = balances[i];
            const walletAddress = wallets[i];

            if (walletBalance === 0) {
                console.log(`Wallet ${walletAddress} has 0 tokens, skipping.`);
                continue;
            }

            // distribute tokens to all wallets
            /**you can't distribute equally, some might be empty so need to share base on (%) */
            const proportionalShare = (walletBalance / allWalletBalances) * tokenHoldingToSell;


            if (walletBalance < proportionalShare) {
                //sell all tokens from this wallet
                await makeSwap(tradeDirection, walletAddress, proportionalShare)
                remainingAmountToSell -= walletBalance;
            } else {
                // wallet has all proportion shared to them
                await makeSwap(tradeDirection, walletAddress, proportionalShare)
                remainingAmountToSell -= proportionalShare;
            }

            console.log(`Remaining amount to sell: ${remainingAmountToSell.toFixed(2)}`)

        }
        return true

    } else if (tradeDirection === "BUY" && holdingPercentage > Config.sellPercentage) {
        //get our buy percentage
        const tokenHoldingToBuy = getTradeAmount(allSolBalances)
        const percentageSell = (tokenHoldingToBuy / allSolBalances) * 100

        console.log("Amount to buy", tokenHoldingToBuy.toLocaleString(), "\nPercentage (%):", percentageSell.toFixed(2))


        //use this here to keep track of amount to buy
        let remainingAmountToBuy = tokenHoldingToBuy;

        //logic checking each wallet has tokens to perfom transaction
        for (let i = 0; i < wallets.length && remainingAmountToBuy > 0; i++) {
            const walletBalance = balances[i];
            const walletAddress = wallets[i];

            if (walletBalance === 0) {
                console.log(`Wallet ${walletAddress} has 0 tokens, skipping.`);
                continue;
            }

            // distribute tokens to all wallets
            /**you can't distribute equally, some might be empty so need to share base on (%) */
            const proportionalShare = (walletBalance / allWalletBalances) * tokenHoldingToBuy;


            if (walletBalance < proportionalShare) {
                //sell all tokens from this wallet
                await makeSwap(tradeDirection, walletAddress, proportionalShare)
                remainingAmountToBuy -= walletBalance;
            } else {
                // wallet has all proportion shared to them
                await makeSwap(tradeDirection, walletAddress, proportionalShare)
                remainingAmountToBuy -= proportionalShare;
            }

            console.log(`Remaining amount to sell: ${remainingAmountToBuy.toFixed(2)}`)

        }
        return true

    }

}

function waitForNextTrade(): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, 200000)); //20 secs
}

(async () => {
    let canTrade = true;

    while (canTrade) {

        try {
            const performTrade = await tokenTrader();
            console.log(`Trade has ended: ${performTrade}`);

            if (performTrade) {
                canTrade = true;
            } else {
                canTrade = false;
            }
        } catch (error) {
            console.log(`Error during trade: ${error}`);
            canTrade = false;
        }

        if (!canTrade) {
            console.log('Waiting before next trade...');
            await waitForNextTrade();
            canTrade = true;
        }
    }
})();