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

import pathlib
import subprocess
from .utils import *
from .verifier import verify_chain
from .add_smart_contract import add_smart_contract


def initialize_blockchain(gpg_ctx, rootdir):
    """Initialize a pyom directory with a blockchain. gpg_ctx should be ~/.gnupg"""
    for x in iter_dir_recursive(rootdir.joinpath(blockchain_dirname)):
        raise Exception('blockchain directory isn\'t empty: ' + x.as_posix())
    result = subprocess.run(
        ['git', '-C', rootdir.as_posix(), 'init'], capture_output=True)
    result.check_returncode()
    fpr = export_block0_pubkey(gpg_ctx, rootdir)
    create_block0(gpg_ctx, rootdir, fpr)
    init_local_gpg(rootdir.joinpath(gnupg_dirname))
    add_smart_contract(
        gpg_ctx, rootdir, smart_contracts_dirname.joinpath('pyomcore'))
    return verify_chain(rootdir)


if __name__ == "__main__":
    initialize_blockchain(gpg.Context(), pathlib.Path.cwd())
