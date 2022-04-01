#!/usr/bin/env python3

# Copyright 2022 Todd Fratello
# This file is part of pyomcore.
#
# pyomcore is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyomcore is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyomcore. If not, see <https://www.gnu.org/licenses/>.

import sys
from .utils import *
from .verifier import Verifier, verify_chain


def check_dependency(worklist, verifiers, that_fpr, that_blockref):
    if not that_fpr in verifiers:
        print('warning: missing blockchain: ' + that_fpr, file=sys.stderr)
        return
    that_v = verifiers[that_fpr]
    # Check that the hash matches
    that_idx = that_blockref['idx']
    that_block_content = that_v.rootdir.joinpath(
        blockfilename(that_idx, block_ext_json)).read_bytes()
    if that_blockref['SHA-512'] != hashlib.sha512(that_block_content).hexdigest():
        raise Exception('check_dependency_chain: hash mismatch')
    if that_idx < that_v.nextidx:
        # already visited
        return
    for idx in range(that_v.nextidx, that_idx + 1):
        that_v.verify_block(idx)
    worklist.append(that_fpr)


def is_detached(verifiers, transaction_status):
    """Checks if an annulled transaction has at least one detached signature.
    Detached means that it refers to a block index that isn't included in
    the dependency chain.
    """
    for that_fpr, that_blockref in transaction_status.signatures.items():
        if not that_fpr in verifiers:
            print('warning: missing blockchain: ' + that_fpr, file=sys.stderr)
            # Benefit of doubt:
            return True
        that_v = verifiers[that_fpr]
        if that_blockref['idx'] >= that_v.nextidx:
            return True
    return False


def check_dependency_chain(mainrootdir, rootdirs):
    """Checks the consistency of your dependencies. Inconsistency can happen
    when somebody forks their blockchain. (Forking your blockchain is
    against the rules and will get you banned.) Blockchains are linked
    to other blockchains via confirmed transactions, creating a dependency
    chain. You are allowed to depend on a forked blockchain (because you
    were not aware of the fork when you created the dependency), but you
    are only allowed to depend on one branch of the fork. You cannot trade
    with a blockchain that depends on a different branch of the fork.
    If you want to trade with a blockchain that has a different branch of
    a fork in its dependency chain, then you need to use the 'annul_transaction'
    action to sever your connection to the wrong branch.

    mainrootdir is your blockchain and rootdirs are other blockchains that it
    depends on. Only dependencies that can be reached from mainrootdir are checked.
    """
    main_v = verify_chain(mainrootdir)
    # Add all the rootdirs to a dict.
    verifiers = {main_v.fpr: main_v}
    for rootdir in rootdirs:
        # Initialize a verifier, but don't iterate over the blocks yet.
        gpg_ctx = init_local_gpg(rootdir.joinpath(gnupg_dirname))
        v = Verifier(rootdir, gpg_ctx)
        if v.fpr in verifiers:
            raise Exception('check_dependency_chain: duplicate fpr: ' + v.fpr)
        verifiers[v.fpr] = v
    # recursive search, using a worklist
    worklist = [main_v.fpr]
    while len(worklist) > 0:
        this_fpr = worklist.pop()
        this_v = verifiers[this_fpr]
        for that_fpr, that_blockref in this_v.extra_connections.items():
            check_dependency(worklist, verifiers, that_fpr, that_blockref)
        for transaction_hash, transaction_status in this_v.transactions.items():
            if not transaction_status.is_confirmed():
                # Only confirmed transactions are included in the dependency chain
                continue
            for that_fpr, that_blockref in transaction_status.signatures.items():
                check_dependency(worklist, verifiers, that_fpr, that_blockref)
    # Check for annulled transactions that should have been reinstated: you aren't
    # allowed to cherry-pick which transactions to annul.
    for this_fpr, this_v in verifiers.items():
        for transaction_hash, transaction_status in this_v.transactions.items():
            if not transaction_status.is_annulled():
                continue
            if not is_detached(verifiers, transaction_status):
                raise Exception('annulled transaction should be reinstated: ' +
                                this_fpr + ': ' + transaction_hash)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('usage: check_dependency_chain path/to/my/pyom_repo path/to/other/pyom_repo1 path/to/other/pyom_repo2 ...',
              file=sys.stderr)
        sys.exit(1)
    mainrootdir = pathlib.Path(sys.argv[1]).resolve()
    rootdirs = list(map(lambda p: pathlib.Path(p).resolve(), sys.argv[2:]))
    check_dependency_chain(mainrootdir, rootdirs)
