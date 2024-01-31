"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g;
    return g = { next: verb(0), "throw": verb(1), "return": verb(2) }, typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.writeJsonFile = exports.getTimestamp = exports.mkdirIfNotExists = void 0;
var web3_js_1 = require("@solana/web3.js");
var fs = require("fs");
function mkdirIfNotExists(dir) {
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir);
    }
}
exports.mkdirIfNotExists = mkdirIfNotExists;
function getTimestamp() {
    return new Date().toISOString().replace(/\.\d+Z/i, "+0000");
}
exports.getTimestamp = getTimestamp;
function writeJsonFile(fileName, context) {
    fs.writeFileSync(fileName, "".concat(JSON.stringify(context, null, 2), "\n"));
}
exports.writeJsonFile = writeJsonFile;
var raydium_sdk_1 = require("@raydium-io/raydium-sdk");
var PublicKey4 = new web3_js_1.PublicKey("675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8");
var PublicKey5 = new web3_js_1.PublicKey("9KEPoZmtHUrBbhWN1v1KWLMkkvwY6WLtAVUCPRtRjP4z");
var programId = {
    4: PublicKey4,
    5: PublicKey5
};
// Helper function to check if a value is an object (but not an array or null)
function isObject(value) {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}
// The rewritten function
function customPoolKeys2JsonInfo(input) {
    if (input instanceof web3_js_1.PublicKey) {
        // Convert PublicKey to string
        return input.toBase58();
    }
    else if (Array.isArray(input)) {
        // Process each element in the array
        return input.map(customPoolKeys2JsonInfo);
    }
    else if (isObject(input)) {
        // Process each key-value pair in the object
        var result = {};
        for (var _i = 0, _a = Object.entries(input); _i < _a.length; _i++) {
            var _b = _a[_i], key = _b[0], value = _b[1];
            result[key] = customPoolKeys2JsonInfo(value);
        }
        return result;
    }
    else {
        // Return the input as is if it's neither PublicKey, array, nor object
        return input;
    }
}
function buildLiquidityPools(connection) {
    return __awaiter(this, void 0, void 0, function () {
        var liquidityDir, poolsKeys, unOfficial, _i, poolsKeys_1, poolKeys;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    liquidityDir = "./dist/liquidity";
                    return [4 /*yield*/, raydium_sdk_1.Liquidity.fetchAllPoolKeys(connection, programId)];
                case 1:
                    poolsKeys = _a.sent();
                    unOfficial = [];
                    for (_i = 0, poolsKeys_1 = poolsKeys; _i < poolsKeys_1.length; _i++) {
                        poolKeys = poolsKeys_1[_i];
                        if (raydium_sdk_1.MAINNET_OFFICIAL_LIQUIDITY_POOLS.includes(poolKeys.id.toBase58())) {
                            // do nothing
                        }
                        else {
                            unOfficial.push(customPoolKeys2JsonInfo(poolKeys));
                        }
                    }
                    // mainnet
                    writeJsonFile("mainnet.json", {
                        name: "Raydium Mainnet Liquidity Pools",
                        timestamp: getTimestamp(),
                        version: {
                            major: 1,
                            minor: 0,
                            patch: 0,
                        },
                        unOfficial: unOfficial,
                    });
                    return [2 /*return*/];
            }
        });
    });
}
(function () {
    return __awaiter(this, void 0, void 0, function () {
        var connection;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    connection = new web3_js_1.Connection("https://solana-mainnet.core.chainstack.com/00147e525c8e83a2f2c57f823fc40d96");
                    return [4 /*yield*/, buildLiquidityPools(connection)];
                case 1:
                    _a.sent();
                    return [2 /*return*/];
            }
        });
    });
})();
