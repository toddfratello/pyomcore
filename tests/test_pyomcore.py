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
import pathlib
import shutil
import time
from datetime import timedelta
from pyomcore.utils import *
from pyomcore.verifier import Verifier, check_blockchain_dir, verify_chain
from pyomcore.initialize_blockchain import initialize_blockchain
from pyomcore.confirm_transactions import confirm_transactions
from pyomcore.add_ban import create_ban
from pyomcore.copy_bans import copy_bans
from pyomcore.check_dependency_chain import check_dependency_chain
from pyomcore.add_extra_connection import add_extra_connection
from pyomcore.remove_extra_connection import remove_extra_connection
from pyomcore.annul_transaction import annul_transaction
from pyomcore.reinstate_transaction import reinstate_transaction

tmpdir = pathlib.Path(sys.argv[1])
pyomcore_url = sys.argv[2]

tmpdir.mkdir(parents=True, exist_ok=True)
tmpdir = tmpdir.resolve()

users = []
gpg_dirs = []
rootdirs = []
participants = []

# initialize 4 users
for i in range(0, 4):
    name = f'user{i}'
    userdir = tmpdir.joinpath(name)
    userdir.mkdir(parents=True, exist_ok=True)
    # Create a directory to simulate the users ~/.gnupg
    gpg_dir = userdir.joinpath('gnupg')
    gpg_dir.mkdir(parents=True, exist_ok=True)
    gpg_ctx = init_local_gpg(gpg_dir)
    gpg_ctx.create_key(name, algorithm='rsa4096', sign=True, certify=True)
    rootdir = userdir.joinpath('pyom')
    rootdir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(['git', 'clone', pyomcore_url, rootdir.joinpath(
        smart_contracts_dirname).joinpath('pyomcore').as_posix()], capture_output=True)
    result.check_returncode()
    initialize_blockchain(gpg_ctx, rootdir)
    # Add to lists
    users.append(name)
    gpg_dirs.append(gpg_dir)
    rootdirs.append(rootdir)
    participants.append({
        'rootdir': rootdir,
        'locations_init': [],
        'protoblock_init': {}
    })
    print(f'created user{i}')

# 4-way transaction
protoblocks = create_transaction(participants, timedelta(days=1))
print('create transaction')

# Register transaction
for gpg_dir, rootdir, protoblock in zip(gpg_dirs, rootdirs, protoblocks):
    gpg_ctx = gpg.Context()
    gpg_ctx.home_dir = gpg_dir.as_posix()
    idx = most_recent_block_idx(rootdir)
    block = load_block(rootdir, idx)
    fpr = block['owner']['gpg']
    create_block(gpg_ctx, rootdir, idx+1, fpr, protoblock)
    print('register transaction', rootdir.parent.name)

# Confirm transaction
for gpg_dir, this_rootdir in zip(gpg_dirs, rootdirs):
    gpg_ctx = gpg.Context()
    gpg_ctx.home_dir = gpg_dir.as_posix()
    for that_rootdir in rootdirs:
        confirm_transactions(gpg_ctx, this_rootdir,
                             that_rootdir, confirm_only=False)
        print('confirm transaction', this_rootdir.parent.name,
              that_rootdir.parent.name)

check_dependency_chain(rootdirs[0], rootdirs[1:])
print('check_dependency_chain')

# new 4-way transaction with very short expiration
protoblocks = create_transaction(participants, timedelta(seconds=2))
print('create transaction')

# Only the first two users register the transaction before the expiry
for gpg_dir, rootdir, protoblock in list(zip(gpg_dirs, rootdirs, protoblocks))[0:2]:
    gpg_ctx = gpg.Context()
    gpg_ctx.home_dir = gpg_dir.as_posix()
    idx = most_recent_block_idx(rootdir)
    block = load_block(rootdir, idx)
    fpr = block['owner']['gpg']
    create_block(gpg_ctx, rootdir, idx+1, fpr, protoblock)
    print('register transaction', rootdir.parent.name)

# Let transaction expire
print('start sleep(3)')
time.sleep(3)
print('stop sleep(3)')

# Add some trivial blocks
for gpg_dir, rootdir in zip(gpg_dirs, rootdirs):
    gpg_ctx = gpg.Context()
    gpg_ctx.home_dir = gpg_dir.as_posix()
    idx = most_recent_block_idx(rootdir)
    block = load_block(rootdir, idx)
    fpr = block['owner']['gpg']
    create_block(gpg_ctx, rootdir, idx+1, fpr, {'actions': []})
    print('create trivial block', rootdir.parent.name)

# Attempt to confirm transaction
for gpg_dir, this_rootdir in zip(gpg_dirs, rootdirs):
    gpg_ctx = gpg.Context()
    gpg_ctx.home_dir = gpg_dir.as_posix()
    for that_rootdir in rootdirs:
        confirm_transactions(gpg_ctx, this_rootdir,
                             that_rootdir, confirm_only=False)
        print('confirm transaction', this_rootdir.parent.name,
              that_rootdir.parent.name)

# Test annulling a transaction
protoblocks = create_transaction(participants, timedelta(seconds=2))
transaction_hash = protoblocks[0]['actions'][-1]['transaction']['SHA-512']
print('create transaction')

# Register transaction
for gpg_dir, rootdir, protoblock in zip(gpg_dirs, rootdirs, protoblocks):
    gpg_ctx = gpg.Context()
    gpg_ctx.home_dir = gpg_dir.as_posix()
    idx = most_recent_block_idx(rootdir)
    block = load_block(rootdir, idx)
    fpr = block['owner']['gpg']
    create_block(gpg_ctx, rootdir, idx+1, fpr, protoblock)
    print('register transaction', rootdir.parent.name)

# Confirm transaction
for gpg_dir, this_rootdir in zip(gpg_dirs, rootdirs):
    gpg_ctx = gpg.Context()
    gpg_ctx.home_dir = gpg_dir.as_posix()
    for that_rootdir in rootdirs:
        confirm_transactions(gpg_ctx, this_rootdir,
                             that_rootdir, confirm_only=False)
        print('confirm transaction', this_rootdir.parent.name,
              that_rootdir.parent.name)

annul_transaction(gpg.Context(home_dir=gpg_dirs[0].as_posix(
)), rootdirs[0], transaction_hash, "test annul_transaction")
print('annul_transaction')
check_dependency_chain(rootdirs[0], rootdirs[1:])
print('check_dependency_chain')
reinstate_transaction(gpg.Context(
    home_dir=gpg_dirs[0].as_posix()), rootdirs[0], transaction_hash)
print('reinstate_transaction')
check_dependency_chain(rootdirs[0], rootdirs[1:])
print('check_dependency_chain')

# Fork user0's blockchain
forkdir = tmpdir.joinpath('fork')
shutil.copytree(tmpdir.joinpath('user0').as_posix(),
                forkdir.as_posix(), ignore=shutil.ignore_patterns('gnupg'))
forkrootdir = forkdir.joinpath('pyom')
# Add some blocks
for gpg_dir, rootdir in zip([gpg_dirs[0], gpg_dirs[0]], [rootdirs[0], forkrootdir]):
    gpg_ctx = gpg.Context()
    gpg_ctx.home_dir = gpg_dir.as_posix()
    idx = most_recent_block_idx(rootdir)
    block = load_block(rootdir, idx)
    fpr = block['owner']['gpg']
    create_block(gpg_ctx, rootdir, idx+1, fpr, {'actions': []})
    print('create trivial block', rootdir.parent.name)
    verify_chain(rootdir)
# Ban user0
for gpg_dir, rootdir in zip(gpg_dirs[1:2], rootdirs[1:2]):
    gpg_ctx = gpg.Context()
    gpg_ctx.home_dir = gpg_dir.as_posix()
    create_ban(gpg_ctx, rootdir, rootdirs[0], forkrootdir)
    print('ban user0', rootdir.parent.name)

add_extra_connection(gpg.Context(
    home_dir=gpg_dirs[0].as_posix()), rootdirs[0], rootdirs[1], 5)
print('add_extra_connection')
check_dependency_chain(rootdirs[0], rootdirs[1:])
print('check_dependency_chain')
remove_extra_connection(gpg.Context(
    home_dir=gpg_dirs[0].as_posix()), rootdirs[0], rootdirs[1])
print('remove_extra_connection')
check_dependency_chain(rootdirs[0], rootdirs[1:])
print('check_dependency_chain')

# Ban user0
for gpg_dir, rootdir in zip(gpg_dirs[2:4], rootdirs[2:4]):
    gpg_ctx = gpg.Context()
    gpg_ctx.home_dir = gpg_dir.as_posix()
    copy_bans(gpg_ctx, rootdir, [rootdirs[1]])
    print('ban user0', rootdir.parent.name)

# Verify
for rootdir in rootdirs:
    verify_chain(rootdir)
    print('verify', rootdir.parent.name)
