# Buyer initiates

Note Over Buyer: Acquire Token

Buyer->WebApp: fund?account=buyer&amount=100

WebApp->Buyer: "balance": 100

Note Over Buyer: Open channel to Seller

Buyer->WebApp: buyer/channel?amount=100

WebApp->Buyer: "create_block": 1418

Note Over Buyer: sign authorization to pay Seller

Buyer->WebApp: buyer/authorize?create_block=1418

WebApp->Buyer: "balance_sig":"ab...."

# Seller

Note Over Seller: verify authorization is valid

Seller->WebApp: seller/verify_balance?create_block=1418&balance_sig=ab..

WebApp->Seller: "verification":"OK"

Note Over Seller: crate data. upload to ipfs

Seller->WebApp: seller/upload -F 'data=@/tmp/x.txt'

WebApp->Seller: "CID":"op..", "size": "11"

# Verification

Title: Verification

Note Over Verifier: Download data

Verifier->WebApp: seller/download?CID=op...

WebApp->Verifier: data

Note Over Verifier: sign data

Verifier->WebApp: verifier/sign?CID=op...

WebApp->Verifier: "verification_sig":"kl.."

# Settlement

Title: Settlement

Note Over Seller: check signature & close transaction

Seller->WebApp:seller/close?CID=&balance_sig=ab..&verification_sig=kl..&create_block

WebApp->Seller: "close_block": 1778
