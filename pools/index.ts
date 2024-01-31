import { Connection, PublicKey } from "@solana/web3.js";
import * as fs from "fs";
export function mkdirIfNotExists(dir: string) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir);
  }
}

export function getTimestamp() {
  return new Date().toISOString().replace(/\.\d+Z/i, "+0000");
}

export function writeJsonFile(fileName: string, context: object) {
  fs.writeFileSync(fileName, `${JSON.stringify(context, null, 2)}\n`);
}

import { ApiPoolInfoItem, Liquidity, MAINNET_OFFICIAL_LIQUIDITY_POOLS, poolKeys2JsonInfo} from "@raydium-io/raydium-sdk" 

const PublicKey4 = new PublicKey("675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8")
const PublicKey5 = new PublicKey("9KEPoZmtHUrBbhWN1v1KWLMkkvwY6WLtAVUCPRtRjP4z")

const programId = {
    4: PublicKey4,
    5: PublicKey5
}

// Helper function to check if a value is an object (but not an array or null)
function isObject(value: any): value is Object {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

// The rewritten function
function customPoolKeys2JsonInfo(input: any): any {
  if (input instanceof PublicKey) {
    // Convert PublicKey to string
    return input.toBase58();
  } else if (Array.isArray(input)) {
    // Process each element in the array
    return input.map(customPoolKeys2JsonInfo);
  } else if (isObject(input)) {
    // Process each key-value pair in the object
    const result: any = {};
    for (const [key, value] of Object.entries(input)) {
      result[key] = customPoolKeys2JsonInfo(value);
    }
    return result;
  } else {
    // Return the input as is if it's neither PublicKey, array, nor object
    return input;
  }
}

async function buildLiquidityPools(connection: Connection) {
    const liquidityDir = "./dist/liquidity";
  
  
    // raydium v4
    const poolsKeys = await Liquidity.fetchAllPoolKeys(connection, programId);
  
    const unOfficial: ApiPoolInfoItem[] = [];

    for (const poolKeys of poolsKeys) {
        if (MAINNET_OFFICIAL_LIQUIDITY_POOLS.includes(poolKeys.id.toBase58())) {
          // do nothing
        } else {
          unOfficial.push(customPoolKeys2JsonInfo(poolKeys));
        }
      }
    
    // mainnet
    writeJsonFile(`mainnet.json`, {
      name: "Raydium Mainnet Liquidity Pools",
      timestamp: getTimestamp(),
      version: {
        major: 1,
        minor: 0,
        patch: 0,
      },
      unOfficial,
    });
}

(async function () {

  const connection = new Connection("https://solana-mainnet.core.chainstack.com/00147e525c8e83a2f2c57f823fc40d96");

  await buildLiquidityPools(connection);

})();