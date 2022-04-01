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
from .confirm_transactions import confirm_transactions

# Same as confirm_transactions.py, except less strict. confirm_transactions.py only
# signs if you're the last participant and can confirm instantly. sign_transactions.py
# signs even if you're not the last participant to sign.
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('usage: confirm_transactions path/to/other/pyom_repo', file=sys.stderr)
        sys.exit(1)
    rootdir = pathlib.Path.cwd()
    gpg_ctx = gpg.Context()
    confirm_transactions(gpg_ctx, rootdir, pathlib.Path(
        sys.argv[1]).resolve(), confirm_only=False)
