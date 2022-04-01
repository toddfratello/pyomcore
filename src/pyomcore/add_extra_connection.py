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


def add_extra_connection(gpg_ctx, this_rootdir, that_rootdir, that_idx):
    this_v = verify_chain(this_rootdir)
    that_v = verify_chain(that_rootdir)
    dirname = mk_unique_path(extra_connections_dirname.joinpath(that_v.fpr))
    this_rootdir.joinpath(dirname).mkdir(parents=True, exist_ok=True)
    this_refpath = dirname.joinpath(
        blockfilename(that_idx, block_ext_ref).name)
    this_sigpath = dirname.joinpath(
        blockfilename(that_idx, block_ext_sig).name)
    this_rootdir.joinpath(this_refpath).write_bytes(
        that_rootdir.joinpath(blockfilename(that_idx, block_ext_ref)).read_bytes())
    this_rootdir.joinpath(this_sigpath).write_bytes(
        that_rootdir.joinpath(blockfilename(that_idx, block_ext_sig)).read_bytes())
    protoblock = {
        'actions': [
            {
                'type': 'add_extra_connection',
                'gpg': that_v.fpr,
                'block_ref': create_fileref(this_rootdir, 0, this_refpath),
                'block_sig': create_fileref(this_rootdir, 0, this_sigpath),
            }
        ]
    }
    this_v.append_block(gpg_ctx, protoblock)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(
            'usage: add_extra_connection path/to/other/pyom <block number>', file=sys.stderr)
        sys.exit(1)
    rootdir = pathlib.Path.cwd()
    gpg_ctx = gpg.Context()
    add_extra_connection(gpg_ctx, rootdir, pathlib.Path(
        sys.argv[1]).resolve(), int(sys.argv[2]))
