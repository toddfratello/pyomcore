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


def copy_block(this_rootdir, this_subdir, that_rootdir, that_idx):
    this_blockpath = this_subdir.joinpath(
        blockfilename(that_idx, block_ext_json).name)
    this_blockrefpath = this_subdir.joinpath(
        blockfilename(that_idx, block_ext_ref).name)
    this_sigpath = this_subdir.joinpath(
        blockfilename(that_idx, block_ext_sig).name)
    this_rootdir.joinpath(this_blockpath.parent).mkdir(
        parents=True, exist_ok=True)
    this_rootdir.joinpath(this_blockpath).write_bytes(
        that_rootdir.joinpath(blockfilename(that_idx, block_ext_json)).read_bytes())
    this_rootdir.joinpath(this_blockrefpath).write_bytes(
        that_rootdir.joinpath(blockfilename(that_idx, block_ext_ref)).read_bytes())
    this_rootdir.joinpath(this_sigpath).write_bytes(
        that_rootdir.joinpath(blockfilename(that_idx, block_ext_sig)).read_bytes())
    return {
        'block': create_fileref(this_rootdir, 0, this_blockpath),
        'block_ref': create_fileref(this_rootdir, 0, this_blockrefpath),
        'block_sig': create_fileref(this_rootdir, 0, this_sigpath)
    }


def confirm_transactions(gpg_ctx, this_rootdir, that_rootdir, confirm_only=True):
    """Look for transactions that can be confirmed in this_rootdir because
    they were accepted in that_rootdir. gpg_ctx should be ~/.gnupg
    """
    confirm_actions = []
    this_v = verify_chain(this_rootdir)
    that_v = verify_chain(that_rootdir)
    for transaction_hash, this_transaction_status in this_v.transactions.items():
        if not this_transaction_status.is_pending():
            continue
        if that_v.fpr not in this_transaction_status.pending_participants:
            continue
        if transaction_hash in that_v.transactions:
            if confirm_only and len(this_transaction_status.pending_participants) > 1:
                raise Exception('Can\'t confirm because you\'re not the last participant. ' +
                                'Use sign_transactions.py to sign without confirming.')
            timestamp = datetime.now(timezone.utc)
            confirmation_path = mk_unique_path(confirmations_dirname)
            that_transaction_status = that_v.transactions[transaction_hash]
            that_idx = that_transaction_status.block_idx
            sign_action = copy_block(
                this_rootdir, confirmation_path, that_rootdir, that_idx)
            sign_action['type'] = 'sign_transaction'
            sign_action['gpg'] = that_v.fpr
            sign_action['transaction'] = {'SHA-512': transaction_hash}
            confirm_actions.append(sign_action)
            if len(this_transaction_status.pending_participants) == 1:
                confirm_action = {
                    'type': 'confirm_transaction',
                    'transaction': {'SHA-512': transaction_hash}
                }
                confirm_actions.append(confirm_action)
        else:
            # Check if transaction can be cancelled (because it has expired)
            transaction = this_transaction_status.transaction
            transaction_timestamp = datetime.fromisoformat(
                transaction['timestamp'])
            expiry_timestamp = datetime.fromisoformat(transaction['expiry'])
            # Search backwards to first block after the expiry
            end_idx = None
            that_idx = most_recent_block_idx(that_rootdir)
            while True:
                that_block = load_block(that_rootdir, that_idx)
                that_timestamp = datetime.fromisoformat(
                    that_block['timestamp'])
                if that_timestamp < expiry_timestamp:
                    break
                end_idx = that_idx
                that_idx -= 1
            # If end_idx is None, then no evidence for cancellation yet
            if not end_idx is None:
                that_idx = end_idx
                cancellation_path = mk_unique_path(cancellations_dirname)
                # Search backwards to first block before transaction
                blocks = []
                while True:
                    blocks.insert(0, copy_block(
                        this_rootdir, cancellation_path, that_rootdir, that_idx))
                    that_block = load_block(that_rootdir, that_idx)
                    that_timestamp = datetime.fromisoformat(
                        that_block['timestamp'])
                    if that_timestamp < transaction_timestamp:
                        break
                    that_idx -= 1
                cancel_action = {
                    'type': 'cancel_transaction',
                    'gpg': that_v.fpr,
                    'transaction': {'SHA-512': transaction_hash},
                    'blocks': blocks
                }
                confirm_actions.append(cancel_action)

    if len(confirm_actions) == 0:
        return
    protoblock = {'actions': confirm_actions}
    this_v.append_block(gpg_ctx, protoblock)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('usage: confirm_transactions path/to/other/pyom_repo', file=sys.stderr)
        sys.exit(1)
    rootdir = pathlib.Path.cwd()
    gpg_ctx = gpg.Context()
    confirm_transactions(gpg_ctx, rootdir, pathlib.Path(
        sys.argv[1]).resolve(), confirm_only=True)
