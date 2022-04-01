# Summary of technical details

Seriously? What are you doing here? Stop wasting time and start trading!

Quick summary of PYOM technical details:

* Your blockchain is a numbered sequence of JSON files.
  * Every block is signed with your gpg key.
  * Every block includes the SHA-512 hash of the previous block to prevent tampering with the history.
  * Blocks can include links to other files in the git repo. SHA-512 hashes are used to prevent tampering.
* A transaction is a JSON file containing details of a trade between an arbitrary number of PYOMers.
  * Any PYOMer can propose a transaction, usually by creating a pull request on another PYOMer's GitHub repo.
  * A transaction is "pending" until all the participants "confirm" it by linking to it in their blockchain.
  * Every transaction has an expiry date.
    * If a transaction expires before every participant has confirmed it, you can mark it as cancelled on your blockchain.
  * If you don't agree to a transaction, just don't add it to your blockchain. It will expire.
* PYOM has two kinds of rules:
  * The first kind are the core rules, defined by the [pyomcore](https://github.com/toddfratello/pyomcore) code. The core rules are only concerned with blockchain integrity - things like checking file hashes and cryptographic signatures.
  * Everything else, including your PYOM currency, is handled by the second type of rule: smart contracts.
    * For example, [pyomcash](https://github.com/toddfratello/pyomcash) is a smart contract that defines the rules of PYOM currency.
* If you break the rules then nobody will trade with you and your currency will become worthless.
  * Before you trade without somebody, download their blockchain and run the verifier on it.
  * Also download and check the blockchains of the PYOMers that they traded with, directly or indirectly.
    * It is your responsibility to check the full dependency graph that you are connecting to by trading.
    * When PYOM takes off, services will pop up to do this checking for you. Until then, you need to do it yourself.
* Never rewrite the history of your blockchain.
  * Once you've added a block, you can never remove it or change it.
  * You are banned from trading if you rewrite your history.
  * If you are a victim of another PYOMer rewriting their history:
    * The core rules allow you to annul affected transactions, but you're not required to.
      * Smart contracts may impose penalties on annulled transactions.
    * It's only a problem if you want to trade with a PYOMer who has a different version of the history in their dependency chain.
      * To trade, one or both of you will need to annul enough affected transactions to make your histories consistent.
    * In the worst case, somebody rewriting their history could cause a partition, where two clusters of PYOMers can no longer trade with each other because they depend on different versions of the history.
      * That's why it's important to share information about PYOMers who have rewritten their history and ban them ASAP.
  * To prove that somebody rewrote their history, all you need is two blocks with the same block index and signed with the same gpg key, but with different file hashes.
    * You can (and should) record this proof on your blockchain.
      * This will prevent you from ever accidentally trading with that PYOMer again.
      * It warns other PYOMers.
* Your blockchain is public, but the rules don't tie it to a specific url.
  * You are free to change hosting provider whenever you like.
  * Your blockchain is allowed to go offline.
  * It's a good idea to keep backups of other blockchains that you trade with, in case they go offline.
* More about smart contracts:
  * They are git repos that you add to your PYOM repo as a [submodule](https://git-scm.com/docs/git-submodule).
  * They are optional: only add a smart contract to your blockchain if you are happy to follow its rules.
  * They can read and enforce rules on your entire blockchain.
    * Their rules apply to all future blocks and also retroactively to all previous blocks.
    * Don't agree to a smart contract that will break your blockchain!
    * Usually, a smart contract only cares about specific transactions.
      * For example, [pyomcash](https://github.com/toddfratello/pyomcash) ignores everything except pyomcash transactions.
  * Transactions usually require a specific smart contract to be installed on your blockchain.
    * For example pyomcash transactions require the pyomcash smart contract.
    * The transaction can require the smart contract to have one or more [signed tags](https://git-scm.com/book/en/v2/Git-Tools-Signing-Your-Work) to prevent anybody from cheating by replacing the smart contract.
      * Signed tags are preferred over a specific commit ID, to allow for bug fixes and other upgrades.
      * Requiring multiple signed tags can reduce the risk of a malicious change to the code.
