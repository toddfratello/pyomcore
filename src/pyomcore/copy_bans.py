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
from .add_ban import add_ban


def copy_bans(gpg_ctx, mainrootdir, rootdirs):
    """Copy information about banned users from the other blockchains"""
    main_v = verify_chain(mainrootdir)
    for rootdir in rootdirs:
        v = verify_chain(rootdir)
        for fpr, action in v.banned.items():
            if not main_v.is_banned(fpr):
                key_content = load_fileref([rootdir], action['keyfile'])
                remotes = action['git_remote_urls']
                ref_content1 = load_fileref([rootdir], action['block_ref1'])
                sig_content1 = load_fileref([rootdir], action['block_sig1'])
                ref_content2 = load_fileref([rootdir], action['block_ref2'])
                sig_content2 = load_fileref([rootdir], action['block_sig2'])
                blockref1 = json.loads(ref_content1)
                idx = blockref1['idx']
                add_ban(gpg_ctx, main_v, fpr, idx, key_content, remotes,
                        ref_content1, sig_content1, ref_content2, sig_content2)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('usage: copy_bans path/to/my/pyom_repo path/to/other/pyom_repo1 path/to/other/pyom_repo2 ...',
              file=sys.stderr)
        sys.exit(1)
    mainrootdir = pathlib.Path(sys.argv[1]).resolve()
    rootdirs = list(map(lambda p: pathlib.Path(p).resolve(), sys.argv[2:]))
    gpg_ctx = gpg.Context()
    copy_bans(gpg_ctx, mainrootdir, rootdirs)
