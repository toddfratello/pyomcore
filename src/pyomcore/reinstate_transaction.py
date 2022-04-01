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


def reinstate_transaction(gpg_ctx, rootdir, transaction_hash):
    v = verify_chain(rootdir)
    protoblock = {
        'actions': [
            {
                'type': 'reinstate_transaction',
                'transaction': {'SHA-512': transaction_hash}
            }
        ]
    }
    v.append_block(gpg_ctx, protoblock)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('usage: reinstate_transaction transaction_hash', file=sys.stderr)
        sys.exit(1)
    rootdir = pathlib.Path.cwd()
    gpg_ctx = gpg.Context()
    reinstate_transaction(gpg_ctx, rootdir, sys.argv[1])
