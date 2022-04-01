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


def add_smart_contract(gpg_ctx, rootdir, submodule_path):
    """Add a smart contract to the blockchain. This imports the gpg key of
    the smart contract developer and checks that the current commit has
    a signed tag.
    """
    v = verify_chain(rootdir)
    # The submodule should contain the public key of the smart contract's developer
    # and a unique uuid for the smart contract.
    keypath = submodule_path.joinpath(smartcontract_pubkey_filename)
    uuidpath = submodule_path.joinpath(smartcontract_uuid_filename)
    fpr = import_key(v.gpg_ctx, rootdir.joinpath(keypath).read_bytes())
    repodir = rootdir.joinpath(submodule_path)
    protoblock = {
        'actions': [
            {
                'type': 'import_gpg_key',
                'gpg': fpr,
                'keyfile': create_fileref(rootdir, 0, keypath),
                'git_remote_urls': git_repo_remote_urls(repodir)
            },
            {
                'type': 'link_file',
                'file': create_fileref(rootdir, 0, uuidpath)
            },
            {
                'type': 'verify_signed_tag',
                'gpg': fpr,
                'git_repo': create_pathref(0, submodule_path)
            }
        ]
    }
    v.append_block(gpg_ctx, protoblock)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('usage: add_smart_contract path/to/smart_contract', file=sys.stderr)
        sys.exit(1)
    rootdir = pathlib.Path.cwd()
    gpg_ctx = gpg.Context()
    add_smart_contract(gpg_ctx, rootdir, pathlib.Path(sys.argv[1]))
