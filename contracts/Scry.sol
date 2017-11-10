pragma solidity ^0.4.17;

import "./token/ERC223_Interface.sol";

contract Scry {
    address public owner;
    address public token_address;

    ERC223 token;

    function Scry(address _token) {
        require(_token != 0x0);

        owner = msg.sender;
        token_address = _token;
        token = ERC223(_token);
    }

    function tokenFallback(
        address _sender,
        uint256 _deposit,
        bytes _data)
        external
    {
        // Make sure we trust the token
        require(msg.sender == token_address);
    }
}