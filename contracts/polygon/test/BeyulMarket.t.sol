// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {BeyulMarket} from "../src/BeyulMarket.sol";

contract BeyulMarketSmokeTest {
    function testCreateMarket() external returns (bool) {
        BeyulMarket market = new BeyulMarket(address(this));
        market.createMarket(keccak256("btc-above-100k"));
        return market.marketCount() == 1;
    }
}
