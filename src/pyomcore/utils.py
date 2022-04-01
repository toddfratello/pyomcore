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

from datetime import datetime, timedelta, timezone
import copy
import gpg
import hashlib
import itertools
import json
import pathlib
import re
import stat
import subprocess

# Version number
pyom_version_number = 1

# Included in every block in the blockchain as a "magic number".
# See https://en.wikipedia.org/wiki/File_format#Magic_number
pyom_block_magic = 'bc1ae75a-7137-11ec-ab3c-2b53f48d31de'

# Included in every blockref as a magic number.
pyom_blockref_magic = '25a4e584-a916-11ec-99f3-bf52559e61a8'

# Included in every transaction as a magic number.
pyom_transaction_magic = '89371ff4-8c0b-11ec-af4e-8f95f2c69a61'

# Included in every fileref as a magic number. Makes it easy to search
# for filerefs and check that their file hashes are correct.
pyom_fileref_magic = '4885be82-7524-11ec-997c-f3c69ad4da31'

# Local files and directories
block0_pubkey_filename = pathlib.PurePath('public.key')
blockchain_dirname = pathlib.PurePath('blockchain')
transactions_dirname = pathlib.PurePath('transactions')
confirmations_dirname = pathlib.PurePath('confirmations')
cancellations_dirname = pathlib.PurePath('cancellations')
extra_connections_dirname = pathlib.PurePath('extra_connections')
banned_dirname = pathlib.PurePath('banned')
gnupg_dirname = pathlib.PurePath('gnupg')
smart_contracts_dirname = pathlib.PurePath('smart_contracts')

# Smart contract files and directories
smartcontract_pubkey_filename = pathlib.PurePath('public.key')
smartcontract_uuid_filename = pathlib.PurePath('pyom_smart_contract_uuid.txt')

# Filename extensions for blockchain files
block_ext_json = '.json'
block_ext_ref = '.ref.json'
block_ext_sig = '.ref.json.sig'


def init_local_gpg(gpgdir):
    """Create a gpg context in gpgdir (so that you can import other PYOMers gpg
    keys into a temporary directory rather than your ~/.gnupg).
    """
    gpgdir.mkdir(parents=True, exist_ok=True, mode=stat.S_IRWXU)
    gpg_ctx = gpg.Context()
    gpg_ctx.home_dir = gpgdir.as_posix()
    return gpg_ctx


def git_repo_current_commit_id(repodir):
    """Get the current commit ID of a git repo."""
    if not repodir.is_dir():
        raise Exception(
            'git_repo_current_commit_id: not a dir: ' + repodir.as_posix())
    result = subprocess.run(
        ['git', '-C', repodir.as_posix(), 'rev-parse', 'HEAD'], capture_output=True)
    result.check_returncode()
    commit_id = result.stdout.decode().strip()
    # check it's a hex number
    int(commit_id, 16)
    return commit_id


def git_repo_remote_url(repodir, name):
    """Get url of a named remote of a git repo."""
    args = ['git', '-C', repodir.as_posix(), 'config', '--get',
            'remote.' + name + '.url']
    result = subprocess.run(args, capture_output=True)
    result.check_returncode()
    return result.stdout.decode().strip()


def git_repo_remote_urls(repodir):
    """Get urls of the remotes of a git repo."""
    result = subprocess.run(
        ['git', '-C', repodir.as_posix(), 'remote'], capture_output=True)
    result.check_returncode()
    return dict(map(lambda name: (name, git_repo_remote_url(repodir, name)),
                    result.stdout.decode().splitlines()))


def git_list_signed_tags(gpg_ctx, repodir, commit_id):
    """List the signed tags for a specific commit."""
    env = {'GNUPGHOME': gpg_ctx.home_dir}
    list_result = subprocess.run(
        ['git', '-C', repodir.as_posix(), 'tag', '--points-at', commit_id], env=env, capture_output=True)
    list_result.check_returncode()
    # for each tag, check if it's signed by fpr
    for tagname in list_result.stdout.decode().splitlines():
        verify_result = subprocess.run(
            ['git', '-C', repodir.as_posix(), 'verify-tag', '--raw', tagname], env=env, capture_output=True)
        if verify_result.returncode == 0:
            for msg in verify_result.stderr.decode().splitlines():
                m = re.fullmatch(
                    r'\[GNUPG:\] VALIDSIG\s\S+\s\S+\s\S+\s\S+\s\S+\s\S+\s\S+\s\S+\s\S+\s(\S+)', msg)
                if m:
                    yield m.groups(0)[0]


def git_verify_signed_tag(gpg_ctx, repodir, commit_id, fpr):
    """Check that the git commit has a signed tag."""
    for tag_fpr in git_list_signed_tags(gpg_ctx, repodir, commit_id):
        if tag_fpr == fpr:
            return
    raise Exception('No tag signed by ' + fpr + ' in ' +
                    repodir.as_posix() + ' at commit ' + commit_id)


def folder_for_filename(filename):
    """filename = 'abcdefgh': returns 'ab/cd/ef'."""
    if len(filename) <= 4:
        return pathlib.PurePath(filename[0:2])
    else:
        return pathlib.PurePath(filename[0:2]).joinpath(folder_for_filename(filename[2:]))


def blockfilename(idx, ext):
    """idx = 0xABCD: returns 'blockchain/00/00/00/00/00/00/ab/cd/000000000000abcd.json'"""
    idxstr = f'{idx:0{16}x}'
    return blockchain_dirname.joinpath(folder_for_filename(idxstr)).joinpath(idxstr + ext)


def iter_dir_recursive(filename, reverse=False):
    """like: find . -type f"""
    if filename.exists():
        if filename.is_dir():
            for x in sorted(filename.iterdir(), reverse=reverse):
                yield from iter_dir_recursive(x, reverse)
        else:
            yield filename


def most_recent_block_idx(rootdir):
    """Find most recent block by searching blockchain directory in reverse alphabetic order."""
    for x in itertools.islice(iter_dir_recursive(rootdir.joinpath(blockchain_dirname), reverse=True), 3):
        m = re.fullmatch(r'([0-9a-f]+)\.json', x.name)
        if m:
            idx = int(m.groups(0)[0], 16)
            if x != rootdir.joinpath(blockfilename(idx, block_ext_json)):
                raise Exception(
                    'most_recent_block: bad filename: ' + x.as_posix())
            return idx
    raise Exception('most_recent_block failed in ' + rootdir.as_posix())


def create_fileref(rootdir, locidx, filename):
    """locidx is a symbolic name for the main directory that the file is
    in. It's replaced with an absolute path when the fileref is read.
    """
    content = rootdir.joinpath(filename).read_bytes()
    return {'pyom_fileref_magic': pyom_fileref_magic,
            'locidx': locidx,
            'filename': filename.as_posix(),
            'SHA-512': hashlib.sha512(content).hexdigest()
            }


def create_pathref(locidx, filename):
    """Like create_fileref, except without the SHA-512. Usually used for directories."""
    return {'locidx': locidx,
            'filename': filename.as_posix()
            }


def getprevhash(rootdir, idx):
    if idx == 0:
        filename = block0_pubkey_filename
    else:
        filename = blockfilename(idx-1, block_ext_json)
    return create_fileref(rootdir, 0, filename)


def load_block(rootdir, idx):
    return json.loads(rootdir.joinpath(blockfilename(idx, block_ext_json)).read_bytes())


def resolve_path(location_array, fileref):
    """Get the absolute path of a fileref or pathref."""
    rootdir = location_array[fileref['locidx']]
    filepath = pathlib.PurePath(fileref['filename'])
    if filepath.is_absolute():
        raise Exception('absolute path in fileref: ' + filepath.as_posix())
    fullpath = rootdir.joinpath(filepath).resolve()
    # Throws an exception on path traversal attempts
    fullpath.relative_to(rootdir)
    return fullpath


def load_fileref(location_array, fileref):
    """A fileref is a dict containing a file path and an expected SHA-512 hash."""
    if fileref['pyom_fileref_magic'] != pyom_fileref_magic:
        raise Exception('bad fileref magic number')
    fullpath = resolve_path(location_array, fileref)
    content = fullpath.read_bytes()
    if hashlib.sha512(content).hexdigest() != fileref['SHA-512']:
        raise Exception('hash mismatch on fileref: ' + fullpath.as_posix())
    return content


def create_block(gpg_ctx, rootdir, idx, fpr, protoblock, timestamp=None):
    """Add standard fields like 'idx' and 'prev', then write file and sign it."""
    if idx < 0:
        raise Exception('negative block index')
    if not timestamp:
        timestamp = datetime.now(timezone.utc)
    block = copy.deepcopy(protoblock)
    block['pyom_version'] = pyom_version_number
    block['pyom_block_magic'] = pyom_block_magic
    block['idx'] = idx
    if not 'owner' in block:
        block['owner'] = {}
    block['owner']['gpg'] = fpr
    block['prev'] = getprevhash(rootdir, idx)
    block['timestamp'] = timestamp.isoformat()
    # encode as json and compute gpg signature
    block_content = json.dumps(block, indent=2).encode('utf-8')
    # The blockref is a small file containing a hash of the block. The owner confirms the
    # block by gpg-signing the blockref. The indirection means that you only need to copy
    # the two blockrefs and signatures to prove that somebody forked their blockchain. It
    # protects you against somebody who forks their blockchain, but puts something offensive
    # in the new block to discourage you from copying it onto your own blockchain.
    blockref = {
        'pyom_version': pyom_version_number,
        'pyom_blockref_magic': pyom_blockref_magic,
        'gpg': fpr,
        'idx': idx,
        'SHA-512': hashlib.sha512(block_content).hexdigest()
    }
    blockref_content = json.dumps(blockref, indent=2).encode('utf-8')
    sig_content, sign_result = gpg_ctx.sign(
        blockref_content, mode=gpg.constants.sig.mode.DETACH)
    if len(sign_result.signatures) == 0:
        raise Exception('no signatures')
    if sign_result.signatures[0].fpr != fpr:
        raise Exception('signatures don\'t match. expected: ' +
                        fpr + ' actual: ' + sign_result.signatures[0].fpr)
    # write files
    block_path = rootdir.joinpath(blockfilename(idx, block_ext_json))
    block_path.parent.mkdir(parents=True, exist_ok=True)
    block_path.write_bytes(block_content)
    blockref_path = rootdir.joinpath(blockfilename(idx, block_ext_ref))
    blockref_path.write_bytes(blockref_content)
    sig_path = rootdir.joinpath(blockfilename(idx, block_ext_sig))
    sig_path.write_bytes(sig_content)
    return block


def create_block0(gpg_ctx, rootdir, fpr):
    protoblock = {
        'actions': [
            {
                'type': 'import_gpg_key',
                'gpg': fpr,
                'keyfile': create_fileref(rootdir, 0, block0_pubkey_filename),
                'git_remote_urls': git_repo_remote_urls(rootdir)
            }
        ]
    }
    create_block(gpg_ctx, rootdir, 0, fpr, protoblock)


def timestamp_path(timestamp):
    """Use a timestamp to create a unique directory name."""
    return pathlib.Path().joinpath(
        f'{timestamp.year:04}', f'{timestamp.month:02}', f'{timestamp.day:02}',
        f'{timestamp.isoformat()}'
    )


def mk_unique_path(basedir):
    timestamp = datetime.now(timezone.utc)
    return basedir.joinpath(timestamp_path(timestamp))


def create_transaction(participants, expiry_delta, transaction_init={'contracts': []}):
    timestamp = datetime.now(timezone.utc)
    transaction_path = transactions_dirname.joinpath(timestamp_path(timestamp))

    def process_this_participant(this_participant):
        this_rootdir = this_participant['rootdir']
        locations = copy.deepcopy(this_participant['locations_init'])
        protoblock = copy.deepcopy(this_participant['protoblock_init'])
        transaction = copy.deepcopy(transaction_init)
        if not 'actions' in protoblock:
            protoblock['actions'] = []
        if not 'numlocations' in transaction:
            transaction['numlocations'] = 0
        gpg_ctx = gpg.Context()
        gpg_ctx.home_dir = this_rootdir.joinpath(gnupg_dirname).as_posix()
        transaction['pyom_version'] = pyom_version_number
        transaction['pyom_transaction_magic'] = pyom_transaction_magic
        transaction['timestamp'] = timestamp.isoformat()
        transaction['expiry'] = (timestamp + expiry_delta).isoformat()
        # Make a directory for the transaction
        transaction_dir = this_rootdir.joinpath(transaction_path)
        transaction_dir.mkdir(parents=True, exist_ok=False)
        locations.append(create_pathref(0, transaction_path))
        locidx = transaction['numlocations']
        transaction['numlocations'] += 1

        def process_that_participant(that_participant):
            that_rootdir = that_participant['rootdir']
            idx = most_recent_block_idx(that_rootdir)
            recent_block = load_block(that_rootdir, idx)
            fpr = recent_block['owner']['gpg']
            # import and copy their gpg key (if necessary)
            if len(list(gpg_ctx.keylist(pattern=fpr))) != 1:
                # create sub-directory
                fpr_dir = pathlib.PurePath(fpr)
                transaction_dir.joinpath(fpr_dir).mkdir(
                    parents=False, exist_ok=False)
                key_content = that_rootdir.joinpath(
                    block0_pubkey_filename).read_bytes()
                gpg_ctx.key_import(key_content)
                key_filename = transaction_path.joinpath(
                    fpr_dir).joinpath(fpr + '.key')
                this_rootdir.joinpath(key_filename).write_bytes(key_content)
                # Get the url where the repo is currently hosted. The hosting location
                # can change, so this is only included as a helpful comment.
                remotes = git_repo_remote_urls(that_rootdir)
                import_action = {
                    'type': 'import_gpg_key',
                    'gpg': fpr,
                    'keyfile': create_fileref(this_rootdir, 0, key_filename),
                    'git_remote_urls': remotes
                }
                protoblock['actions'].append(import_action)
            return {'gpg': fpr}
        transaction['participants'] = list(
            map(process_that_participant, participants))
        transaction_content = json.dumps(transaction, indent=2).encode('utf-8')
        transaction_filename = transaction_path.joinpath('transaction.json')
        this_rootdir.joinpath(transaction_filename).write_bytes(
            transaction_content)
        register_action = {
            'type': 'register_transaction',
            'transaction': create_fileref(this_rootdir, 0, transaction_filename),
            'locations': locations
        }
        protoblock['actions'].append(register_action)
        protoblock_content = json.dumps(protoblock, indent=2).encode('utf-8')
        protoblock_filename = transaction_path.joinpath('protoblock.json')
        this_rootdir.joinpath(protoblock_filename).write_bytes(
            protoblock_content)
        return protoblock
    return list(map(process_this_participant, participants))


def export_block0_pubkey(gpg_ctx, rootdir):
    """Create public.key file. gpg_ctx should be ~/.gnupg, not the local
    one that's stored with the blockchain.
    """
    gpg_ctx.armor = True
    keys = list(gpg_ctx.keylist(secret=True))
    if len(keys) == 0:
        raise Exception(
            'You need to create a gpg key: gpg --full-generate-key')
    key = keys[0]
    content = gpg_ctx.key_export(pattern=key.fpr)
    rootdir.joinpath(block0_pubkey_filename).write_bytes(content)
    return key.fpr


def import_key(gpg_ctx, key_content):
    result = gpg_ctx.key_import(key_content)
    return result.imports[0].fpr


def walkjson(object):
    """Walk a json object recursively."""
    yield object
    if isinstance(object, dict):
        for key, value in object.items():
            yield from walkjson(value)
    elif isinstance(object, list):
        for value in object:
            yield from walkjson(value)
