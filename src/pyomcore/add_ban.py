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


def add_ban(gpg_ctx, v, fpr, idx, key_content, remotes, ref_content1, sig_content1, ref_content2, sig_content2):
    ban_dir1 = banned_dirname.joinpath(fpr).joinpath('fork1')
    ban_dir2 = banned_dirname.joinpath(fpr).joinpath('fork2')
    v.rootdir.joinpath(ban_dir1).mkdir(parents=True, exist_ok=True)
    v.rootdir.joinpath(ban_dir2).mkdir(parents=True, exist_ok=True)
    this_refpath1 = ban_dir1.joinpath(
        blockfilename(idx, block_ext_ref).name)
    this_sigpath1 = ban_dir1.joinpath(
        blockfilename(idx, block_ext_sig).name)
    this_refpath2 = ban_dir2.joinpath(
        blockfilename(idx, block_ext_ref).name)
    this_sigpath2 = ban_dir2.joinpath(
        blockfilename(idx, block_ext_sig).name)
    v.rootdir.joinpath(this_refpath1).write_bytes(ref_content1)
    v.rootdir.joinpath(this_sigpath1).write_bytes(sig_content1)
    v.rootdir.joinpath(this_refpath2).write_bytes(ref_content2)
    v.rootdir.joinpath(this_sigpath2).write_bytes(sig_content2)
    key_filename = banned_dirname.joinpath(fpr).joinpath(fpr + '.key')
    v.rootdir.joinpath(key_filename).write_bytes(key_content)
    protoblock = {
        'actions': [
            {
                'type': 'ban',
                'gpg': fpr,
                'keyfile': create_fileref(v.rootdir, 0, key_filename),
                'git_remote_urls': remotes,
                'block_ref1': create_fileref(v.rootdir, 0, this_refpath1),
                'block_sig1': create_fileref(v.rootdir, 0, this_sigpath1),
                'block_ref2': create_fileref(v.rootdir, 0, this_refpath2),
                'block_sig2': create_fileref(v.rootdir, 0, this_sigpath2)
            }
        ]
    }
    v.append_block(gpg_ctx, protoblock)


def create_ban(gpg_ctx, rootdir, forkdir1, forkdir2):
    """Ban a PYOMer who has forked their blockchain. gpg_ctx should be ~/.gnupg
    Searches the 2 blockchains to find the first mismatch.
    """
    v = verify_chain(rootdir)
    v1 = verify_chain(forkdir1)
    v2 = verify_chain(forkdir2)
    if v1.fpr != v2.fpr:
        raise Exception('forkdir1 and forkdir2 belong to different PYOMers')
    fpr = v1.fpr
    if v.is_banned(fpr):
        raise Exception('PYOMer is already banned: ' + fpr)
    numblocks1 = 1 + most_recent_block_idx(forkdir1)
    numblocks2 = 1 + most_recent_block_idx(forkdir2)
    for idx in range(0, min(numblocks1, numblocks2)):
        ref_content1 = forkdir1.joinpath(
            blockfilename(idx, block_ext_ref)).read_bytes()
        blockref1 = json.loads(ref_content1)
        ref_content2 = forkdir2.joinpath(
            blockfilename(idx, block_ext_ref)).read_bytes()
        blockref2 = json.loads(ref_content2)
        if blockref1['SHA-512'] != blockref2['SHA-512']:
            sig_content1 = forkdir1.joinpath(
                blockfilename(idx, block_ext_sig)).read_bytes()
            sig_content2 = forkdir2.joinpath(
                blockfilename(idx, block_ext_sig)).read_bytes()
            key_content = forkdir1.joinpath(
                block0_pubkey_filename).read_bytes()
            remotes = git_repo_remote_urls(forkdir1)
            remotes.update(git_repo_remote_urls(forkdir2))
            add_ban(gpg_ctx, v, fpr, idx, key_content, remotes,
                    ref_content1, sig_content1, ref_content2, sig_content2)
            return
    raise Exception('no fork found')


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print('usage: add_ban path/to/pyomfork1 path/to/pyomfork2', file=sys.stderr)
        sys.exit(1)
    rootdir = pathlib.Path.cwd()
    gpg_ctx = gpg.Context()
    create_ban(gpg_ctx, rootdir, pathlib.Path(
        sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]).resolve())
