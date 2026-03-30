// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

contract BeyulMarket {
    address public owner;
    address public settlementOracle;
    uint256 public marketCount;

    struct Market {
        bytes32 marketId;
        bool settled;
        uint256 outcome;
    }

    mapping(uint256 => Market) public markets;

    constructor(address oracle_) {
        owner = msg.sender;
        settlementOracle = oracle_;
    }

    function createMarket(bytes32 marketId) external returns (uint256 id) {
        require(msg.sender == owner, "only owner");

        id = ++marketCount;
        markets[id] = Market({
            marketId: marketId,
            settled: false,
            outcome: 0
        });
    }

    function settleMarket(uint256 id, uint256 outcome) external {
        require(msg.sender == settlementOracle, "only oracle");
        require(!markets[id].settled, "already settled");

        markets[id].settled = true;
        markets[id].outcome = outcome;
    }
}
