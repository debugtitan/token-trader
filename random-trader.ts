import bs58 from "bs58"
import BN from "bn.js"
import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'js-yaml';
import { Connection, Keypair, PublicKey } from "@solana/web3.js"
import { getAssociatedTokenAddressSync } from "@solana/spl-token"
import { Raydium, CurveCalculator } from "@raydium-io/raydium-sdk-v2"
import { Config } from "./config"

type TradeDirection = "BUY" | "SELL"

interface WalletData {
    walletAddress: string;
    privateKey: string;
    solBalance: number;
    tokenBal: number;
}

interface Wallet {
    privateKey: string;
    solBalance: number;
    tokenBal: number;
}


interface Wallets {
    [walletAddress: string]: Wallet;
}

interface WalletsYaml {
    [key: string]: {
        privateKey: string;
        solBalance: number;
        tokenBal: number;
    };
}

function delay(ms: number) {
    return new Promise( resolve => setTimeout(resolve, ms) );
}

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

async function makeSwap(direction: TradeDirection, secretKey: string, swapAmount: number): Promise<boolean> {
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
        return false
    }

    const outputAmount = new BN(tradeAmount * 10 ** 9)//
    const data = await raydium.cpmm.getPoolInfoFromRpc(Config.AMM_ID)
    if (data == null) {
        return false
    }
    const poolInfo = data.poolInfo
    const poolKeys = data.poolKeys
    const rpcData = data.rpcData

    if (poolInfo == null || rpcData == null) {
        return false
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

    const { txId } = await execute({ recentBlockHash: blockHash.value.blockhash, sendAndConfirm: false })


    console.log(`https://solscan.io/tx/${txId}`)
    await delay(20000)
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


function loadWallets(): Wallets {
    const fileContents = fs.readFileSync('wallets.yaml', 'utf8');
    return yaml.load(fileContents) as Wallets;;
}

async function tokenTrader() {
    const tradeDirection = getRandomTradeDirection();

    // Fetch all wallet data
    const wallets = loadWallets();

    // Calculate total token balances and SOL balances
    const allTokenBalances = Object.values(wallets).reduce((accumulator, wallet) => accumulator + wallet.tokenBal, 0);
    const allSolBalances = Object.values(wallets).reduce((accumulator, wallet) => accumulator + wallet.solBalance, 0);

    console.log(`Total SOL Balance: ${allSolBalances}`);
    console.log(`Total Token Balance: ${allTokenBalances}`);

    // Fetch token supply
    const tokenSupply = Config.TOKEN_SUPPLY; // Ensure Config.TOKEN_SUPPLY is defined

    // Calculate wallet holding percentage
    const holdingPercentage = (allTokenBalances / tokenSupply) * 100;

    console.log(`Holdings: ${holdingPercentage.toFixed(2)}%`);


    if (tradeDirection === "SELL" && holdingPercentage > Config.sellPercentage) {
        const tokenHoldingToSell = getTradeAmount(allTokenBalances);
        const percentageSell = (tokenHoldingToSell / allTokenBalances) * 100;

        console.log(`Amount to Sell: ${tokenHoldingToSell.toLocaleString()}`);
        console.log(`Percentage (%): ${percentageSell.toFixed(2)}`);

        let remainingAmountToSell = tokenHoldingToSell;

        // Logic for selling tokens
        for (const [walletAddress, wallet] of Object.entries(wallets)) {
            await delay(10000)
            const walletBalance = wallet.tokenBal;

            if (remainingAmountToSell <= 0) break;

            if (walletBalance === 0) {
                console.log(`Wallet ${walletAddress} has 0 tokens, skipping.`);
                continue;
            }

            const proportionalShare = (walletBalance / allTokenBalances) * tokenHoldingToSell;

            if (walletBalance < proportionalShare) {
                // we're selling all tokens
                const amountToSwap = walletBalance

                // Retry logic
                let swapSuccessful = false;
                while (!swapSuccessful) {
                    swapSuccessful = await makeSwap(tradeDirection, wallet.privateKey, walletBalance);
                    if (!swapSuccessful) {
                        console.log(`Swap failed for wallet ${walletAddress}. Retrying...`);
                    }
                }

                // Update wallet balance
                wallets[walletAddress].tokenBal -= amountToSwap;
                remainingAmountToSell -= amountToSwap;
            } else {
                // we're selling proportions
                const amountToSwap = proportionalShare;

                // Retry logic
                let swapSuccessful = false;
                while (!swapSuccessful) {
                    swapSuccessful = await makeSwap(tradeDirection, wallet.privateKey, proportionalShare);
                    if (!swapSuccessful) {
                        console.log(`Swap failed for wallet ${walletAddress}. Retrying...`);
                    }
                }

                // Update wallet balance
                wallets[walletAddress].tokenBal -= amountToSwap;
                remainingAmountToSell -= amountToSwap;
            }
        }
        return true

    } else if (tradeDirection === "BUY" && holdingPercentage > Config.sellPercentage) {
        const tokenHoldingToBuy = getTradeAmount(allSolBalances);
        const percentageBuy = (tokenHoldingToBuy / allSolBalances) * 100;

        console.log(`Amount to Buy: ${tokenHoldingToBuy.toLocaleString()}`);
        let remainingAmountToBuy = tokenHoldingToBuy;

        // Logic for buying tokens
        for (const [walletAddress, wallet] of Object.entries(wallets)) {
            await delay(10000)
            const walletBalance = wallet.solBalance;

            if (remainingAmountToBuy <= 0) break;

            if (walletBalance <= 0.0005) {
                console.log(`Wallet ${walletAddress} has 0 SOL, skipping.`);
                continue;
            }

            const proportionalShare = (walletBalance / allSolBalances) * tokenHoldingToBuy;

            if (walletBalance < proportionalShare) {
                // Retry logic
                let swapSuccessful = false;
                while (!swapSuccessful) {
                    swapSuccessful = await makeSwap(tradeDirection, wallet.privateKey, walletBalance);
                    if (!swapSuccessful) {
                        console.log(`Swap failed for wallet ${walletAddress}. Retrying...`);
                    }
                }

                // Update wallet balance
                wallets[walletAddress].tokenBal -= walletBalance;
                remainingAmountToBuy -= walletBalance;
            } else {
                // Retry logic
                let swapSuccessful = false;
                while (!swapSuccessful) {
                    swapSuccessful = await makeSwap(tradeDirection, wallet.privateKey, proportionalShare);
                    if (!swapSuccessful) {
                        console.log(`Swap failed for wallet ${walletAddress}. Retrying...`);
                    }
                }

                // Update wallet balance
                wallets[walletAddress].tokenBal -= proportionalShare;
                remainingAmountToBuy -= proportionalShare;
            }
        }
        return true
    }
}


function waitForNextTrade(): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, 5000000));
}



// save all wallet balance
async function fetchWalletSaveBalance() {
    // Read wallet secret keys from file
    const wallets = fs.readFileSync("Wallets.txt", 'utf-8').split('\n').map(wallet => wallet.trim()).filter(wallet => wallet !== '');

    // Fetch all token balances
    const tokenBalances = await Promise.all(wallets.map(secretKey => getWalletBalance(secretKey)));

    // Fetch all SOL balances
    const solBalances = await Promise.all(wallets.map(secretKey => getBalance(secretKey)));

    // Build the wallet data with public keys and balances
    const walletsData: WalletData[] = wallets.map((secretKey, index) => {
        const wallet = Keypair.fromSecretKey(bs58.decode(secretKey));
        const walletAddress = wallet.publicKey.toString();

        return {
            walletAddress,
            privateKey: secretKey,
            solBalance: solBalances[index],
            tokenBal: tokenBalances[index]
        };
    });


    const walletsYaml: WalletsYaml = walletsData.reduce((obj, wallet) => {
        obj[wallet.walletAddress] = {
            privateKey: wallet.privateKey,
            solBalance: wallet.solBalance,
            tokenBal: wallet.tokenBal
        };
        return obj;
    }, {} as WalletsYaml);

    fs.writeFileSync('wallets.yaml', yaml.dump(walletsYaml), 'utf8');
    return true;
}


(async () => {
    await fetchWalletSaveBalance()
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
