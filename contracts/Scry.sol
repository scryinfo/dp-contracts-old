pragma solidity ^0.4.17;

import "./token/ERC223_Interface.sol";
import "./ECVerify.sol";

contract Scry {
    address public owner;
    address public token_address;
    string constant prefix = "\x19Ethereum Signed Message:\n";

    ERC223 token;

    mapping (bytes32 => Channel) channels;

    // 28 (deposit) + 4 (block no)
    struct Channel {
        uint192 deposit; // mAX 2^192 == 2^6 * 2^18
        uint32 open_block_number; // UNIQUE for participants to prevent replay of messages in later channels
    }

    /*
     *  Events
     */

    event ChannelCreated(
        address indexed _sender,
        address indexed _receiver,
        uint192 _deposit);

    event Ev(address indexed _sender, uint192 _deposit, bytes data);

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
        
        // Ev(_sender, uint192(_deposit), _data);
        uint length = _data.length;

        // createChannel - receiver address (20 bytes + padding = 32 bytes)
        require(length == 20);
        address receiver = addressFromData(_data);
        createChannelPrivate(_sender, receiver, uint192(_deposit));
    }

    /*
     *  Public helper functions (constant)
     */

    /// @dev Returns the unique channel identifier used in the contract.
    /// @param _sender The address that sends tokens.
    /// @param _receiver The address that receives tokens.
    /// @param _open_block_number The block number at which a channel between the sender and receiver was created.
    /// @return Unique channel identifier.
    function getKey(
        address _sender,
        address _receiver,
        uint32 _open_block_number)
        public
        constant
        returns (bytes32 data)
    {
        return keccak256(_sender, _receiver, _open_block_number);
    }

    /// @dev Returns a hash of the balance message needed to be signed by the sender.
    /// @param _receiver The address that receives tokens.
    /// @param _open_block_number The block number at which a channel between the sender and receiver was created.
    /// @param _balance The amount of tokens owed by the sender to the receiver.
    /// @return Hash of the balance message.
    function getBalanceMessage(
        address _receiver,
        uint32 _open_block_number,
        uint192 _balance)
        public
        constant
        returns (string)
    {
        string memory str = concat("Receiver: 0x", addressToString(_receiver));
        str = concat(str, ", Balance: ");
        str = concat(str, uintToString(uint256(_balance)));
        str = concat(str, ", Channel ID: ");
        str = concat(str, uintToString(uint256(_open_block_number)));
        return str;
    }

    // 56014 gas cost
    /// @dev Returns the sender address extracted from the balance proof.
    /// @param _receiver The address that receives tokens.
    /// @param _open_block_number The block number at which a channel between the sender and receiver was created.
    /// @param _balance The amount of tokens owed by the sender to the receiver.
    /// @param _balance_msg_sig The balance message signed by the sender or receiver.
    /// @return Address of the balance proof signer.
    function verifyBalanceProof(
        address _receiver,
        uint32 _open_block_number,
        uint192 _balance,
        bytes _balance_msg_sig)
        public
        constant
        returns (address)
    {
        //GasCost('close verifyBalanceProof getBalanceMessage start', block.gaslimit, msg.gas);
        // Create message which should be signed by sender
        string memory message = getBalanceMessage(_receiver, _open_block_number, _balance);
        //GasCost('close verifyBalanceProof getBalanceMessage end', block.gaslimit, msg.gas);

        //GasCost('close verifyBalanceProof length start', block.gaslimit, msg.gas);
        // 2446 gas cost
        // TODO: improve length calc
        uint message_length = bytes(message).length;
        //GasCost('close verifyBalanceProof length end', block.gaslimit, msg.gas);

        //GasCost('close verifyBalanceProof uintToString start', block.gaslimit, msg.gas);
        string memory message_length_string = uintToString(message_length);
        //GasCost('close verifyBalanceProof uintToString end', block.gaslimit, msg.gas);

        //GasCost('close verifyBalanceProof concat start', block.gaslimit, msg.gas);
        // Prefix the message
        string memory prefixed_message = concat(prefix, message_length_string);
        //GasCost('close verifyBalanceProof concat end', block.gaslimit, msg.gas);

        prefixed_message = concat(prefixed_message, message);


        // Hash the prefixed message string
        bytes32 prefixed_message_hash = sha3(prefixed_message);

        // Derive address from signature
        address signer = ECVerify.ecverify(prefixed_message_hash, _balance_msg_sig);
        return signer;
    }

    /*
     *  Private functions
     */

    /// @dev Creates a new channel between a sender and a receiver, only callable by the Token contract.
    /// @param _sender The address that receives tokens.
    /// @param _receiver The address that receives tokens.
    /// @param _deposit The amount of tokens that the sender escrows.
    function createChannelPrivate(
        address _sender,
        address _receiver,
        uint192 _deposit)
        private
    {
        //GasCost('createChannel start', block.gaslimit, msg.gas);
        uint32 open_block_number = uint32(block.number);

        // Create unique identifier from sender, receiver and current block number
        bytes32 key = getKey(_sender, _receiver, open_block_number);

        require(channels[key].deposit == 0);
        require(channels[key].open_block_number == 0);

        // Store channel information
        channels[key] = Channel({deposit: _deposit, open_block_number: open_block_number});
        //GasCost('createChannel end', block.gaslimit, msg.gas);
        ChannelCreated(_sender, _receiver, _deposit);
    }

    /*
     *  Internal functions
     */

    // 2656 gas cost
    /// @dev Internal function for getting an address from tokenFallback data bytes.
    /// @param b Bytes received.
    /// @return Address resulted.
    function addressFromData (
        bytes b)
        internal
        constant
        returns (address)
    {
        bytes20 addr;
        assembly {
            // Read address bytes
            // Offset of 32 bytes, representing b.length
            addr := mload(add(b, 0x20))
        }
        return address(addr);
    }

    function memcpy(
        uint dest,
        uint src,
        uint len)
        private
    {
        // Copy word-length chunks while possible
        for(; len >= 32; len -= 32) {
            assembly {
                mstore(dest, mload(src))
            }
            dest += 32;
            src += 32;
        }

        // Copy remaining bytes
        uint mask = 256 ** (32 - len) - 1;
        assembly {
            let srcpart := and(mload(src), not(mask))
            let destpart := and(mload(dest), mask)
            mstore(dest, or(destpart, srcpart))
        }
    }

    // 3813 gas cost
    function concat(
        string _self,
        string _other)
        internal
        constant
        returns (string)
    {
        uint self_len = bytes(_self).length;
        uint other_len = bytes(_other).length;
        uint self_ptr;
        uint other_ptr;

        assembly {
            self_ptr := add(_self, 0x20)
            other_ptr := add(_other, 0x20)
        }

        var ret = new string(self_len + other_len);
        uint retptr;
        assembly { retptr := add(ret, 32) }
        memcpy(retptr, self_ptr, self_len);
        memcpy(retptr + self_len, other_ptr, other_len);
        return ret;
    }

    // 9613 gas
    function uintToString(
        uint v)
        internal
        constant
        returns (string)
    {
        bytes32 ret;
        if (v == 0) {
            ret = '0';
        }
        else {
             while (v > 0) {
                ret = bytes32(uint(ret) / (2 ** 8));
                ret |= bytes32(((v % 10) + 48) * 2 ** (8 * 31));
                v /= 10;
            }
        }

        bytes memory bytesString = new bytes(32);
        uint charCount = 0;
        for (uint j=0; j<32; j++) {
            byte char = byte(bytes32(uint(ret) * 2 ** (8 * j)));
            if (char != 0) {
                bytesString[j] = char;
                charCount++;
            }
        }
        bytes memory bytesStringTrimmed = new bytes(charCount);
        for (j = 0; j < charCount; j++) {
            bytesStringTrimmed[j] = bytesString[j];
        }

        return string(bytesStringTrimmed);
    }

    function addressToString(
        address x)
        internal
        constant
        returns (string)
    {
        bytes memory str = new bytes(40);
        for (uint i = 0; i < 20; i++) {
            byte b = byte(uint8(uint(x) / (2**(8*(19 - i)))));
            byte hi = byte(uint8(b) / 16);
            byte lo = byte(uint8(b) - 16 * uint8(hi));
            str[2*i] = char(hi);
            str[2*i+1] = char(lo);
        }
        return string(str);
    }

    function char(byte b)
        internal
        constant
        returns (byte c)
    {
        if (b < 10) return byte(uint8(b) + 0x30);
        else return byte(uint8(b) + 0x57);
    }
}