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
from enum import Enum
from .utils import *


def check_fileref(location_array, object):
    """If the object is a fileref, check the hash"""
    if isinstance(object, dict):
        if 'pyom_fileref_magic' in object:
            if object['pyom_fileref_magic'] == pyom_fileref_magic:
                # This checks the hash
                load_fileref(location_array, object)


def check_filerefs_json(location_array, json):
    """Recursively check the filerefs in a json object."""
    for obj in walkjson(json):
        check_fileref(location_array, obj)


def check_blockchain_dir(rootdir):
    """Check the contents of the blockchain directory. Returns the number of blocks."""
    n = 0
    for filename in iter_dir_recursive(rootdir.joinpath(blockchain_dirname)):
        idx = n // 3
        ext = block_ext_json if n % 3 == 0 else (
            block_ext_ref if n % 3 == 1 else block_ext_sig)
        expected = rootdir.joinpath(blockfilename(idx, ext))
        if filename != expected:
            raise Exception('unexpected file in blockchain dir: ' +
                            filename.as_posix() + ' expected: ' + expected.as_posix())
        n += 1
    return n // 3


def check_valid_blockref(blockref, fpr):
    if len(blockref) != 5:
        raise Exception('wrong number of fields in blockref')
    if blockref['pyom_blockref_magic'] != pyom_blockref_magic:
        raise Exception('bad pyom_blockref_magic')
    if blockref['pyom_version'] != pyom_version_number:
        raise Exception('bad pyom version in blockref')
    if blockref['gpg'] != fpr:
        raise Exception('fpr mismatch in blockref')
    if not isinstance(blockref['idx'], int):
        raise Exception('idx is not an int in blockref')
    if not isinstance(blockref['SHA-512'], str):
        raise Exception('SHA-512 is not a str in blockref')
    if len(blockref['SHA-512']) != 128:
        raise Exception('SHA-512 incorrect length in blockref')


def check_blockref_sig(gpg_ctx, fpr, blockref_content, sig_content):
    """Check that the blockref is gpg-signed."""
    verify_data, verify_result = gpg_ctx.verify(blockref_content, sig_content)
    if len(verify_result.signatures) == 0 or verify_result.signatures[0].fpr != fpr:
        raise Exception('blockref has bad signature')
    blockref = json.loads(blockref_content)
    check_valid_blockref(blockref, fpr)
    return blockref


def check_block_sig(gpg_ctx, fpr, block_content, blockref_content, sig_content):
    """Check that block_txt is the JSON for a block. It needs to contain
    pyom_block_magic and be signed by the correct owner.
    """
    blockref = check_blockref_sig(gpg_ctx, fpr, blockref_content, sig_content)
    block = json.loads(block_content)
    if blockref['idx'] != block['idx']:
        raise Exception('idx mismatch in blockref')
    if blockref['SHA-512'] != hashlib.sha512(block_content).hexdigest():
        raise Exception('SHA-512 mismatch in blockref')
    if block['pyom_block_magic'] != pyom_block_magic:
        raise Exception('bad pyom_block_magic')
    if block['owner']['gpg'] != fpr:
        raise Exception('bad owner')
    return block


def check_register_transaction_timestamp(block_timestamp, transaction):
    transaction_timestamp = datetime.fromisoformat(transaction['timestamp'])
    expiry_timestamp = datetime.fromisoformat(transaction['expiry'])
    # Expect: transaction_timestamp < block_timestamp < expiry_timestamp
    if not (transaction_timestamp < block_timestamp):
        # Transaction should be created before the block.
        raise Exception('bad transaction timestamp')
    if not (block_timestamp < expiry_timestamp):
        # The transaction must added to the blockchain before it expires
        # or it is considered abandoned.
        raise Exception('bad transaction expiry')


def block_registers_transaction(transaction_hash, block):
    for action in block['actions']:
        if action['type'] == 'register_transaction':
            if transaction_hash == action['transaction']['SHA-512']:
                return True
    return False


class TransactionState(Enum):
    """Permitted state transations:
    PENDING -> CANCELLED  ('cancel_transaction')
    PENDING -> CONFIRMED  ('confirm_transaction')
    CONFIRMED -> ANNULLED  ('annul_transaction')
    ANNULLED -> CONFIRMED  ('reinstate_transaction')
    """
    PENDING = 0
    CONFIRMED = 1
    CANCELLED = 2
    ANNULLED = 3


class TransactionStatus(object):
    def __init__(self, transaction, block_idx):
        self.transaction = transaction
        self.block_idx = block_idx
        self.pending_participants = set(
            map(lambda p: p['gpg'], transaction['participants']))
        self.signatures = {}
        self.state = TransactionState.PENDING

    def remove_pending_participant(self, fpr):
        if not fpr in self.pending_participants:
            raise Exception(
                'remove_pending_participant: fpr not found: ' + fpr)
        self.pending_participants.remove(fpr)

    def is_pending(self):
        return (self.state == TransactionState.PENDING)

    def is_confirmed(self):
        return (self.state == TransactionState.CONFIRMED)

    def is_annulled(self):
        return (self.state == TransactionState.ANNULLED)


class Verifier(object):
    def __init__(self, rootdir, gpg_ctx):
        self.rootdir = rootdir
        self.location_array_root = [self.rootdir]
        self.nextidx = 0
        self.gpg_ctx = gpg_ctx
        self.fpr = import_key(self.gpg_ctx, self.rootdir.joinpath(
            block0_pubkey_filename).read_bytes())
        self.known_gpg_keys = {self.fpr: {}}
        self.transactions = {}
        self.banned = {}
        self.extra_connections = {}

    def is_banned(self, fpr):
        return (fpr in self.banned)

    def verify_block(self, idx):
        if idx != self.nextidx:
            raise Exception('unexpected idx')
        self.nextidx += 1
        # Load files
        block_path = self.rootdir.joinpath(blockfilename(idx, block_ext_json))
        block_content = block_path.read_bytes()
        blockref_path = self.rootdir.joinpath(
            blockfilename(idx, block_ext_ref))
        blockref_content = blockref_path.read_bytes()
        sig_path = self.rootdir.joinpath(blockfilename(idx, block_ext_sig))
        sig_content = sig_path.read_bytes()
        # Check gpg signature
        block = check_block_sig(self.gpg_ctx, self.fpr,
                                block_content, blockref_content, sig_content)
        # Check fields
        if block['pyom_version'] != pyom_version_number:
            raise Exception('bad pyom version in block')
        if block['prev'] != getprevhash(self.rootdir, idx):
            raise Exception('bad prev hash')
        if block['idx'] != idx:
            raise Exception('bad index')
        timestamp = datetime.fromisoformat(block['timestamp'])
        if not (timestamp < datetime.now(timezone.utc)):
            raise Exception('timestamp is in the future')
        if idx > 0:
            prevtimestamp = datetime.fromisoformat(
                load_block(self.rootdir, idx-1)['timestamp'])
            if not (prevtimestamp < timestamp):
                raise Exception('invalid timestamp')
        block_timestamp = datetime.fromisoformat(block['timestamp'])
        self.verify_block_body(block_timestamp, idx, block)

    def verify_block_body(self, block_timestamp, block_idx, block):
        check_filerefs_json(self.location_array_root, block)
        self.verify_block_actions(block_timestamp, block_idx, block['actions'])

    def verify_block_actions(self, block_timestamp, block_idx, actions):
        for action in actions:
            t = action['type']
            if t == 'import_gpg_key':
                self.verify_import_gpg_key(action)
            elif t == 'ban':
                self.verify_ban(action)
            elif t == 'register_transaction':
                self.verify_register_transaction(
                    block_timestamp, block_idx, action)
            elif t == 'sign_transaction':
                self.verify_sign_transaction(action)
            elif t == 'confirm_transaction':
                self.verify_confirm_transaction(action)
            elif t == 'cancel_transaction':
                self.verify_cancel_transaction(action)
            elif t == 'annul_transaction':
                self.verify_annul_transaction(action)
            elif t == 'reinstate_transaction':
                self.verify_reinstate_transaction(action)
            elif t == 'add_extra_connection':
                self.verify_add_extra_connection(action)
            elif t == 'remove_extra_connection':
                del self.extra_connections[action['gpg']]
            elif t == 'verify_signed_tag':
                # Check that a git repo has a signed tag.
                fpr = action['gpg']
                self.verify_fpr(fpr)
                repodir = resolve_path(
                    self.location_array_root, action['git_repo'])
                commit_id = git_repo_current_commit_id(repodir)
                git_verify_signed_tag(self.gpg_ctx, repodir, commit_id, fpr)
            elif t == 'link_file':
                # Link an arbitrary file to the blockchain. Hash is checked to
                # prevent file contents from changing.
                load_fileref(self.location_array_root, action['file'])
            else:
                raise Exception('unknown action type: ' + t)

    def verify_import_gpg_key(self, action):
        fpr = action['gpg']
        result = self.gpg_ctx.key_import(
            load_fileref(self.location_array_root, action['keyfile']))
        if result.imports[0].fpr != fpr:
            raise Exception(
                'import_gpg_key: fingerprint doesn\'t match')
        remotes = action['git_remote_urls']
        for name, url in remotes.items():
            if not (isinstance(name, str) and isinstance(url, str)):
                raise Exception(
                    'import_gpg_key: invalid git_remote_urls')
        self.known_gpg_keys[fpr] = remotes
        return fpr

    def verify_ban(self, action):
        """Ban another PYOMer because they have forked their blockchain."""
        fpr = self.verify_import_gpg_key(action)
        if self.is_banned(fpr):
            raise Exception('verify_ban: already banned')
        ref_content1 = load_fileref(
            self.location_array_root, action['block_ref1'])
        sig_content1 = load_fileref(
            self.location_array_root, action['block_sig1'])
        ref_content2 = load_fileref(
            self.location_array_root, action['block_ref2'])
        sig_content2 = load_fileref(
            self.location_array_root, action['block_sig2'])
        block_ref1 = check_blockref_sig(
            self.gpg_ctx, fpr, ref_content1, sig_content1)
        block_ref2 = check_blockref_sig(
            self.gpg_ctx, fpr, ref_content2, sig_content2)
        if block_ref1['idx'] != block_ref2['idx']:
            raise Exception('verify_ban: block idx mismatch')
        if block_ref1['SHA-512'] == block_ref2['SHA-512']:
            raise Exception('verify_ban: hashes are the same')
        self.banned[fpr] = action

    def verify_register_transaction(self, block_timestamp, block_idx, action):
        """Add a transaction to the blockchain. Is it "pending" until all participants sign it."""
        transaction_txt = load_fileref(
            self.location_array_root, action['transaction'])
        transaction_hash = action['transaction']['SHA-512']
        transaction = json.loads(transaction_txt)
        # Create a new location_array for the transaction.
        if transaction['numlocations'] != len(action['locations']):
            raise Exception(
                'register_transaction: locations have different lengths')
        location_array_transaction = list(map(
            lambda loc: resolve_path(self.location_array_root, loc),
            action['locations']))
        if transaction_hash in self.transactions:
            raise Exception(
                'register_transaction: duplicate transaction:\n' + transaction_hash)
        self.verify_transaction(
            location_array_transaction, block_timestamp, transaction)
        transaction_status = TransactionStatus(transaction, block_idx)
        transaction_status.remove_pending_participant(self.fpr)
        self.transactions[transaction_hash] = transaction_status

    def verify_transaction(self, location_array, block_timestamp, transaction):
        if transaction['pyom_version'] != pyom_version_number:
            raise Exception('bad pyom_version in transaction')
        if transaction['pyom_transaction_magic'] != pyom_transaction_magic:
            raise Exception('bad pyom_transaction_magic')
        check_filerefs_json(location_array, transaction)
        check_register_transaction_timestamp(block_timestamp, transaction)
        for p in transaction['participants']:
            fpr = p['gpg']
            self.verify_fpr(fpr)
            if self.is_banned(fpr):
                raise Exception('banned participant: ' + fpr)
        for contract in transaction['contracts']:
            contractdir = resolve_path(location_array, contract['path'])
            # Check the smart contract's uuid.
            uuid_content = contractdir.joinpath(
                smartcontract_uuid_filename).read_bytes()
            uuid_hash = hashlib.sha512(uuid_content).hexdigest()
            if uuid_hash != contract['uuid_hash']['SHA-512']:
                raise Exception('smart contract uuid mismatch')
            # Check the current commit is signed by the author(s) of the smart contract.
            commit_id = git_repo_current_commit_id(contractdir)
            for author in contract['authors']:
                fpr = author['gpg']
                self.verify_fpr(fpr)
                git_verify_signed_tag(
                    self.gpg_ctx, contractdir, commit_id, fpr)

    def verify_sign_transaction(self, this_action):
        """Another participant has agreed to a transaction by adding it to their
        own blockchain. This action links to the relevant block and signature.
        """
        fpr = this_action['gpg']
        self.verify_fpr(fpr)
        transaction_hash = this_action['transaction']['SHA-512']
        transaction_status = self.transactions[transaction_hash]
        if not transaction_status.is_pending():
            raise Exception('sign_transaction: transaction is not PENDING')
        transaction = transaction_status.transaction
        # Load block and check signature
        block_txt = load_fileref(
            self.location_array_root, this_action['block'])
        block_ref = load_fileref(
            self.location_array_root, this_action['block_ref'])
        block_sig = load_fileref(
            self.location_array_root, this_action['block_sig'])
        block = check_block_sig(
            self.gpg_ctx, fpr, block_txt, block_ref, block_sig)
        # Check block timestamp
        block_timestamp = datetime.fromisoformat(block['timestamp'])
        check_register_transaction_timestamp(block_timestamp, transaction)
        if not block_registers_transaction(transaction_hash, block):
            raise Exception('sign_transaction: transaction not found')
        transaction_status.remove_pending_participant(fpr)
        transaction_status.signatures[fpr] = json.loads(block_ref)

    def verify_confirm_transaction(self, action):
        """After all the participants have signed a transaction, it can move from
        PENDING to CONFIRMED.
        """
        transaction_hash = action['transaction']['SHA-512']
        transaction_status = self.transactions[transaction_hash]
        if not transaction_status.is_pending():
            raise Exception('confirm_transaction: transaction is not PENDING')
        if len(transaction_status.pending_participants) != 0:
            raise Exception('confirm_transaction: ' + transaction_hash +
                            'unconfirmed partipants: ' +
                            str(transaction_status.pending_participants))
        transaction_status.state = TransactionState.CONFIRMED

    def verify_cancel_transaction(self, this_action):
        """One of the participants has not registered the transaction before it expired,
        so it is cancelled.
        """
        fpr = this_action['gpg']
        self.verify_fpr(fpr)
        transaction_hash = this_action['transaction']['SHA-512']
        transaction_status = self.transactions[transaction_hash]
        if not transaction_status.is_pending():
            raise Exception('cancel_transaction: transaction is not PENDING: ' +
                            str(transaction_status.state))
        if fpr not in transaction_status.pending_participants:
            raise Exception('cancel_transaction: not a pending participant')
        transaction = transaction_status.transaction
        transaction_timestamp = datetime.fromisoformat(
            transaction['timestamp'])
        expiry_timestamp = datetime.fromisoformat(transaction['expiry'])
        blocks = this_action['blocks']
        numblocks = len(blocks)
        if numblocks < 2:
            raise Exception('cancel_transaction: at least 2 blocks required')
        for i in range(0, numblocks):
            # Load block and check signature
            block_txt = load_fileref(
                self.location_array_root, blocks[i]['block'])
            block_ref = load_fileref(
                self.location_array_root, blocks[i]['block_ref'])
            block_sig = load_fileref(
                self.location_array_root, blocks[i]['block_sig'])
            block = check_block_sig(
                self.gpg_ctx, fpr, block_txt, block_ref, block_sig)
            if block_registers_transaction(transaction_hash, block):
                print(transaction_hash)
                print(block)
                raise Exception(
                    'cancel_transaction: transaction is registered')
            block_timestamp = datetime.fromisoformat(block['timestamp'])
            if i == 0:
                # Check that the first block is older than the transaction
                start_idx = block['idx']
                if transaction_timestamp < block_timestamp:
                    raise Exception(
                        'cancel_transaction: first block is too recent')
            else:
                if block['idx'] != start_idx + i:
                    raise Exception(
                        'cancel_transaction: blocks are not in sequence')
            if i == numblocks - 1:
                # Check that the last block is more recent than the transaction expiry
                if block_timestamp < expiry_timestamp:
                    raise Exception(
                        'cancel_transaction: last block is too old')
        # Cancel the transaction
        transaction_status.state = TransactionState.CANCELLED

    def verify_annul_transaction(self, action):
        """Annulling a transaction is usually unnecessary. It's only needed if
        you want to trade with a blockchain that has a different branch of a
        forked blockchain in its dependency chain. It lets you sever the
        connections between your blockchain and the wrong branch of the fork.
        There are two deterrents against annulling transactions for no reason:
        1. check_dependency_chain.py prevents you from trading with blockchains
           that you have annulled a transaction with.
        2. Smart contracts may impose penalties on annulled transactions.
        """
        transaction_hash = action['transaction']['SHA-512']
        transaction_status = self.transactions[transaction_hash]
        if not transaction_status.is_confirmed():
            raise Exception('annul_transaction: transaction is not CONFIRMED')
        # Check there's a comment explaining why this transaction was annulled.
        if not isinstance(action['explanation'], str):
            raise Exception('annul_transaction: explanation is not a str')
        transaction_status.state = TransactionState.ANNULLED

    def verify_reinstate_transaction(self, action):
        """Undo a previous 'annul_transaction' action."""
        transaction_hash = action['transaction']['SHA-512']
        transaction_status = self.transactions[transaction_hash]
        if not transaction_status.is_annulled():
            raise Exception(
                'reinstate_transaction: transaction is not ANNULLED')
        transaction_status.state = TransactionState.CONFIRMED

    def verify_add_extra_connection(self, action):
        """Extra connections are optional and rarely needed. If one of the PYOMers in
        your dependency chain has annulled a transaction and check_dependency_chain.py
        will error unless it takes that into account, then you can add an extra
        connection to guide it. You can remove extra connections when they are no
        longer needed, or replace them so that they point to a different block index.
        """
        fpr = action['gpg']
        self.verify_fpr(fpr)
        ref_content1 = load_fileref(
            self.location_array_root, action['block_ref'])
        sig_content1 = load_fileref(
            self.location_array_root, action['block_sig'])
        block_ref = check_blockref_sig(
            self.gpg_ctx, fpr, ref_content1, sig_content1)
        self.extra_connections[fpr] = block_ref

    def verify_fpr(self, fpr):
        if fpr not in self.known_gpg_keys:
            raise Exception('unknown gpg key: ' + fpr)

    def append_block(self, gpg_ctx, protoblock):
        """Utility for creating a new block at the end of the chain."""
        block_timestamp = datetime.now(timezone.utc)
        self.verify_block_body(block_timestamp, self.nextidx, protoblock)
        create_block(gpg_ctx, self.rootdir, self.nextidx,
                     self.fpr, protoblock, block_timestamp)


def verify_chain(rootdir):
    numblocks = check_blockchain_dir(rootdir)
    if numblocks == 0:
        raise Exception('no blocks found')
    gpg_ctx = init_local_gpg(rootdir.joinpath(gnupg_dirname))
    v = Verifier(rootdir, gpg_ctx)
    for idx in range(0, numblocks):
        try:
            v.verify_block(idx)
        except Exception as e:
            print(f'Error in block {idx}:', e, file=sys.stderr)
            raise Exception(f'Blockchain verification failed in block {idx}')
    return v


if __name__ == "__main__":
    verify_chain(pathlib.Path.cwd())
