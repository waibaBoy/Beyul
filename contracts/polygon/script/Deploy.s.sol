// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {BeyulMarket} from "../src/BeyulMarket.sol";

contract DeployBeyulMarket {
    function deploy(address oracle) external returns (BeyulMarket) {
        return new BeyulMarket(oracle);
    }
}
