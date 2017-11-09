pragma solidity ^0.4.17;

import "./token/ERC223_Token.sol";

contract ScryToken is ERC223Token {
    address public owner;

    function ScryToken (uint256 _initialAmount) {
        owner = msg.sender;
        _initialAmount = _initialAmount;                // Number of tokens * multiplier
        balances[owner] = _initialAmount;               // Give the creator all initial tokens
        totalSupply = _initialAmount;                   // set total supply
        name = "Scry.Info";
        decimals = 18;
        symbol = "SCRY";
    }
}