# Print Your Own Money (PYOM)

Everybody's doing it: Central banks are printing trillions, most of it going straight into the pockets of their [Wall Street buddies](https://www.newyorker.com/news/our-columnists/wall-streets-pandemic-bonanza). Satoshi Nakamoto created bitcoin and [mined around 5% of the total supply for himself](https://en.wikipedia.org/wiki/Satoshi_Nakamoto#Development_of_bitcoin) before the rest of us knew what was happening. The Ethereum founders went one better and ["premined" 10% of the supply for themselves](https://www.coindesk.com/markets/2020/07/11/sale-of-the-century-the-inside-story-of-ethereums-2014-premine/). NFT "artists" are minting money with hyperlinks to second-rate JPGs.

If they can do it, why not you and me too? Welcome to the Print Your Own Money (PYOM) project. Read on for simple instructions on how to create your own cryptocurrency, with you in full control - you'll be the central banker of your own currency, with the power to print like JPow. And it's free to get started: all you need is a GitHub account.

# How does it work?

Every PYOMer has their own currency on their own blockchain. You print as much of your own currency as you like, and use it to trade with other PYOMers. For example, [here's]() a trade that I did with my buddy [Zac](https://github.com/zacveli): I gave him 420 of my Todds in exchange for 420 of his Zacs. But there's no rule that says that a Todd is worth exactly the same as a Zac, so maybe the next we trade it will be 69 Todds for 42069 Zacs. Other PYOMers can also trade your currency. For example, Zac could trade some of the 420 Todds that he got from me with his brother [Chad](https://github.com/chadveli).

Other cryptocurrencies have designed their own networking protocols, proof-of-work algorithms, even new programming languages. That sounds like a lot of work, so PYOM doesn't do that. Instead, embracing the "move fast and break things" motto, PYOM is hacked together from a hodgepodge of off-the-shelf tools, like [git](https://git-scm.com/downloads) for record keeping and networking, [GnuPG](https://gnupg.org/) for cryptography, and [JSON](https://en.wikipedia.org/wiki/JSON) for the blockchain format. Don't worry, we'll slap a web interface on this thing soon and nobody'll need to know how the sausage was made.

Remember how back in 2007 "one billion" still seemed like a big number? These days, anything less than a trillion is chump change, so you're going to need to print some big numbers if you want to keep up with the pros. That's why PYOM uses [Python](https://www.python.org/), which has [unlimited precision integers](https://docs.python.org/3/library/stdtypes.html#numeric-types-int-float-complex). Other programming languages might stop you from printing beyond 2147483647, but Python will take you to the moon. 🚀

# How to get started

Create a [GitHub](https://github.com/) account. You don't *have* to use GitHub (PYOM works on any git platform), but it's the simplest way to get started.

Use [this template](https://github.com/toddfratello/pyom_template/generate) to create a new public git repository. Name it something like "pyom_mygithubhandle", so that your repo has a unique name. Later you'll fork other people's PYOM repositories to trade with them, so you'll want your repo to have a different name than theirs.

Install [git](https://git-scm.com/downloads) and [Python](https://www.python.org/).

Install [GnuPG](https://gnupg.org/) and [create a keypair](https://docs.github.com/en/authentication/managing-commit-signature-verification/generating-a-new-gpg-key). It's also a good idea to set up [commit signing](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits), but it's not required.

Now run these commands to initialize your repository:

```bash
mkdir ~/pyom
cd ~/pyom
git clone --recursive git@github.com:myname/pyom_mygithubhandle.git  # replace with url of your repository
cd pyom_mygithubhandle  # replace with name of your repository
pip3 install ./smart_contracts/pyomcore
pip3 install ./smart_contracts/pyomcash
python3 -m pyomcore.initialize_blockchain
git add .
git commit -m "Block 0"
git push
```

## How to trade

Trading is a 3-step process. Using a trade between Zac and Chad as an example, here's how it works:

1. Zac proposes a trade by sending Chad a [pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests). Zac also signs the trade by adding it to his own blockchain.
2. Chad merges the pull request, then signs the trade by adding it to his own blockchain and confirms it by copying Zac's signature from Zac's blockchain.
3. Zac confirms the trade by copying Chad's signature from Chad's blockchain.

<details><summary>Detailed instructions</summary>
<br>

If these instructions seem a bit cumbersome, it's because PYOM is built on [git](https://git-scm.com). This is all totally normal for git - you'll get used to it.

Zac goes to [pyom_chadveli](https://github.com/chadveli/pyom_chadveli) and clicks the "fork" button. Then he runs these commands:

```bash
cd ~/pyom
mkdir pyom_zacveli_deps  # Create a directory for blockchains of other PYOMers
cd pyom_zacveli_deps
git clone --recursive https://github.com/zacveli/pyom_chadveli.git  # Zac's fork of pyom_chadveli
git remote add upstream https://github.com/chadveli/pyom_chadveli.git
cd pyom_chadveli
python3 -m pyomcore.verifier  # check that Chad hasn't broken the pyomcore rules
python3 -m pyomcash.verifier  # check that Chad hasn't broken the pyomcash rules
cd ~/pyom/pyom_zacveli
python3 -m pyomcore.check_dependency_chain . ~/pyom/pyom_zacveli_deps/*  # check dependencies
python3 -m pyomcash.propose_simple_trade ~/pyom/pyom_zacveli_deps/pyom_chadveli 69 420  # Trade 69 Zacs for 420 Chads
git add .
git commit -m "Trade with Chad"  # commit on main branch
git push  # Upload transaction to Zac's pyom repo on GitHub
cd ~/pyom/pyom_zacveli_deps/pyom_chadveli
git checkout -b TradeWithZac  # Create new branch for the trade
git add .
git commit -m "Trade with Zac"  # commit on TradeWithZac branch
git push  # Upload transaction to Zac's fork of Chad's pyom repo on GitHub
```

Then Zac creates a [pull request]() on GitHub and Chad merges it. But Chad also needs to add a new block to his blockchain to sign and confirm the transaction:

```bash
cd ~/pyom/pyom_chadveli_deps/pyom_zacveli
git fetch --all
git checkout main
git merge upstream/main
git push  # Chad's fork of pyom_zacveli is now up-to-date
python3 -m pyomcore.verifier  # check that Zac hasn't broken the pyomcore rules
python3 -m pyomcash.verifier  # check that Zac hasn't broken the pyomcash rules
cd ~/pyom/pyom_chadveli
git pull  # Download the transaction
python3 -m pyomcore.create_block transactions/2022/04/01/<timestamp>/protoblock.json
python3 -m pyomcore.confirm_transactions ~/pyom/pyom_chadveli_deps/pyom_zacveli
git add .
git commit -m "Confirm trade with Zac"  # commit on main branch
git push  # Upload transaction to Chad's pyom repo on GitHub
```

Finally, Zac runs same sequence of commands to confirm that Chad signed the transaction:

```bash
cd ~/pyom/pyom_zacveli_deps/pyom_chadveli
git fetch --all
git checkout main
git merge upstream/main
git push  # Zac's fork of pyom_chadveli is now up-to-date
python3 -m pyomcore.verifier  # check that Chad hasn't broken the pyomcore rules
python3 -m pyomcash.verifier  # check that Chad hasn't broken the pyomcash rules
cd ~/pyom/pyom_zacveli
python3 -m pyomcore.confirm_transactions ~/pyom/pyom_zacveli_deps/pyom_chadveli
git add .
git commit -m "Confirm trade with Zac"  # commit on main branch
git push  # Upload transaction to Zac's pyom repo on GitHub
```

</details>

# Technical details

We all know blockchain is the future. Who cares about the technical details? Stop wasting time and start trading! If it really matters to you then you should read the [pyomcore](https://github.com/toddfratello/pyomcore) source code. Otherwise, [here's](/doc/TechnicalDetails.md) a quick summary. Feel free to skip it.

# Frequently asked questions

## What will my currency be worth?

1 Bitcoin is worth 1 Bitcoin and the same principle is true for your currency - except if you break the pyomcore rules, in which case it's *definitely* worthless.

## How do I make my currency valuable and get super-rich?

1. Use your imagination: We live in a world where [hyperlinks to pixelated JPGs are worth millions](https://news.bitcoin.com/bandana-wearing-cryptopunk-nft-smashes-records-selling-for-23-million-in-ethereum/), so with a bit of creativity you should be able to convince other people to swap their antiquated fiat money for your high-tech cryptocurrency.
2. Ride on the coattails of others: Trade your currency with as many other PYOMers as possible, so that if one of them hits the jackpot then you can wet your beak too.

## Why doesn't PYOM use proof-of-work?

Other cryptocurrencies use [proof-of-work](https://en.wikipedia.org/wiki/Proof_of_work) as a rate-limiting mechanism: it stops other people from printing new currency too quickly, which would make your stake worthless. But PYOM doesn't need it because you control your own supply. Infinite supply for you, finite for everybody else: learn what it feels like to create inflation, rather than being on the receiving end!

It's regrettable that PYOM doesn't use proof-of-work, because every cryptocurrency ought to have waste and environmental destruction as a core feature. It just doesn't feel quite right without it, does it? Let's hope there's an innovator out there who'll invent a clever way to shoehorn it in!

## Is PYOM web3-ready?

Yes: it's distributed, it's crypto, and it's got blockchain. Add some hype and you're all set for web3!

## GitHub is not decentralized and it's owned by Microsoft

1. That's true.
2. Other git hosting services are available.
3. git itself is decentralized, so you can host your PYOM project on multiple sites and keep offline backups.
4. When you trade your currency with another PYOMer, they have an incentive to keep a backup of your blockchain for verification purposes.

## When did the PYOM project start?

[April 1, 2022]()

## Is PYOM a joke?

* No more so than dogecoin, which has reached a market cap of [billions](https://fortune.com/2021/02/11/dogecoin-price-rise-creator-market-cap/).
* You might think that PYOM is a ridiculous idea, but ask yourself: didn't you think the same thing when you first heard about all the other cryptocurrencies? Who's laughing now?

## Is PYOM a scam?

Not at this time, but like all cryptocurrencies, it has potential! When PYOM takes off, there's a 100% probability that some enterprising charlatans will find a way to use it for fraud!

## How do you pronounce PYOM?

[Like the sound of a passing Lambo.](https://www.urbandictionary.com/define.php?term=Pyom)
