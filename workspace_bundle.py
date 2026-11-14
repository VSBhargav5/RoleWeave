"""Verified recovery of the shelf and all managed web artifacts into a new workspace."""
from collections import Counter
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from uuid import uuid4
import zipfile

from career_profile import unique_json
from application_draft import draft_snapshot, bound_profile
from cover_letter import letter_snapshot
from job_store import JobStore
from safe_export import publish_bytes

LIMIT=64*1024*1024
FORMAT='roleweave-workspace-v1'
PATTERNS={'drafts':r'[a-f0-9]{32}\.json', 'letters':r'[a-f0-9]{32}\.json', 'packets':r'[a-f0-9]{32}\.zip',
          'sources':r'[a-f0-9]{64}\.json', 'resume-imports':r'[a-f0-9]{64}\.(pdf|docx|txt)'}


def storage_path(path):
    """Use explicit Windows extended paths without changing system settings."""
    path=Path(path)
    if os.name!='nt':return path
    absolute=os.path.abspath(path)
    if absolute.startswith("\\\\?\\"):return Path(absolute)
    return Path("\\\\?\\UNC\\"+absolute[2:] if absolute.startswith("\\\\") else "\\\\?\\"+absolute)


def no_link(path):
    if path.is_symlink() or (hasattr(path,'is_junction') and path.is_junction()):
        raise ValueError('Linked workspace artifact paths are unsupported')


def valid_name(name):
    if name=='shelf.json':return True
    parts=name.split('/')
    return len(parts)==3 and parts[0]=='web-artifacts' and parts[1] in PATTERNS and re.fullmatch(PATTERNS[parts[1]],parts[2]) is not None


def shelf_bytes(store):
    with tempfile.TemporaryDirectory(prefix='roleweave-shelf-') as folder:
        path=Path(folder)/'shelf.json';store.backup(path);return path.read_bytes()


def captured_artifacts(root):
    no_link(root)
    if not root.exists():return {}
    result={};total=0
    for directory in root.iterdir():
        no_link(directory)
        if not directory.is_dir() or directory.name not in PATTERNS:
            raise ValueError('Unsupported managed artifact found; no incomplete backup was created')
        for path in directory.iterdir():
            no_link(path)
            name='web-artifacts/'+directory.name+'/'+path.name
            if not path.is_file() or not valid_name(name):
                raise ValueError('Unsupported or in-progress artifact found; finish the operation and retry backup')
            if len(result)>=1000:raise ValueError('Workspace bundle exceeds 1000 managed files')
            with path.open('rb') as source:payload=source.read(LIMIT-total+1)
            total+=len(payload)
            if total>LIMIT:raise ValueError('Workspace bundle exceeds 64 MiB')
            validate_artifact(name,payload)
            result[name]=payload
    return result


def validate_artifact(name,payload):
    if not valid_name(name):raise ValueError('Unsupported workspace archive path')
    if name.startswith('web-artifacts/drafts/'):
        draft_snapshot(payload)
    elif name.startswith('web-artifacts/letters/'):
        letter_snapshot(payload)
    elif name.startswith(('web-artifacts/sources/','web-artifacts/resume-imports/')):
        if hashlib.sha256(payload).hexdigest()!=Path(name).stem:
            raise ValueError('Original source filename and byte fingerprint disagree')


def export_bundle(store, artifacts):
    first=shelf_bytes(store)
    captured=captured_artifacts(artifacts)
    if first!=shelf_bytes(store) or captured!=captured_artifacts(artifacts):
        raise ValueError('Workspace changed during backup; finish other saves and retry')
    parts={'shelf.json':first}|captured
    for name,data in captured.items():
        if name.startswith('web-artifacts/drafts/'):bound_profile(store,draft_snapshot(data)[0])
    if sum(map(len,parts.values()))>LIMIT:raise ValueError('Workspace bundle exceeds 64 MiB')
    manifest={'format':FORMAT,'unencrypted':True,'managed_only':True,
              'files':{name:{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in parts.items()}}
    output=BytesIO()
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_STORED) as archive:
        for name,data in parts.items():archive.writestr(name,data)
        archive.writestr('manifest.json',json.dumps(manifest,ensure_ascii=True))
    if len(output.getvalue())>LIMIT:raise ValueError('Workspace bundle exceeds 64 MiB including its manifest')
    return output.getvalue()


def inspect_bundle(payload):
    if not isinstance(payload,bytes) or not 0<len(payload)<=LIMIT:
        raise ValueError('Choose a workspace ZIP of at most 64 MiB')
    try:
        with zipfile.ZipFile(BytesIO(payload)) as archive:
            entries=archive.infolist();names=[e.filename for e in entries]
            if len(entries)>1002 or len(names)!=len(set(names)) or 'manifest.json' not in names or 'shelf.json' not in names:
                raise ValueError('Unsupported or duplicate workspace bundle members')
            if sum(e.file_size for e in entries)>LIMIT or any(e.flag_bits&1 for e in entries):
                raise ValueError('Expanded workspace exceeds 64 MiB or is encrypted')
            if any(n!='manifest.json' and not valid_name(n) for n in names):
                raise ValueError('Unsupported workspace archive path')
            parts={}
            for info in entries:
                with archive.open(info) as source:data=source.read(min(info.file_size+1,LIMIT+1))
                if len(data)!=info.file_size:raise ValueError('Workspace member size differs')
                parts[info.filename]=data
        manifest=json.loads(parts.pop('manifest.json'),object_pairs_hook=unique_json)
        if (not isinstance(manifest,dict) or set(manifest)!={'format','unencrypted','managed_only','files'}
                or manifest['format']!=FORMAT or manifest['unencrypted'] is not True or manifest['managed_only'] is not True
                or not isinstance(manifest['files'],dict) or set(manifest['files'])!=set(parts)):
            raise ValueError('Unsupported workspace manifest')
        for name,data in parts.items():
            expected=manifest['files'][name]
            if not isinstance(expected,dict) or expected!={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} or type(expected.get('bytes')) is not int:
                raise ValueError('Workspace member fingerprint or size differs')
            if name!='shelf.json':validate_artifact(name,data)
        with tempfile.TemporaryDirectory(prefix='roleweave-validate-') as folder:
            path=Path(folder)/'shelf.json';path.write_bytes(parts['shelf.json'])
            store=JobStore(Path(folder)/'jobs.db');store.restore(path)
            for name,data in parts.items():
                if name.startswith('web-artifacts/drafts/'):bound_profile(store,draft_snapshot(data)[0])
            summary={'jobs':len(store.list_jobs()),'profiles':len(store.list_profiles()),'resumes':len(store.list_resumes()),
                     'artifacts':dict(Counter(name.split('/')[1] for name in parts if name!='shelf.json')),
                     'files':len(parts),'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}
        return parts,summary
    except (zipfile.BadZipFile,KeyError,TypeError,UnicodeError,RuntimeError,NotImplementedError,RecursionError) as exc:
        raise ValueError('Invalid or unsupported workspace bundle') from None


def restore_bundle(payload, parent):
    parts,summary=inspect_bundle(payload)  # Validate everything before reserving persistent output.
    parent=storage_path(parent);no_link(parent)
    identifier=uuid4().hex;stage=parent/('.stage-'+identifier);final=parent/identifier
    parent.mkdir(parents=True,exist_ok=True)
    stage.mkdir(exist_ok=False)
    source=stage/'shelf.json';publish_bytes(source,parts.pop('shelf.json'))
    store=JobStore(stage/'jobs.db');store.restore(source)
    for name,data in parts.items():
        destination=stage/name;destination.parent.mkdir(parents=True,exist_ok=True);publish_bytes(destination,data)
    marker={'format':FORMAT,'id':identifier,'complete':True,'summary':summary}
    publish_bytes(stage/'RECOVERY.json',json.dumps(marker,ensure_ascii=True).encode())
    stage.rename(final)
    return {'id':identifier,'summary':summary}


def recovered_database(parent, identifier):
    if not isinstance(identifier,str) or not re.fullmatch(r'[a-f0-9]{32}',identifier):
        raise ValueError('Choose a completed recovered workspace')
    parent=storage_path(parent);directory=parent/identifier
    for path in (parent,directory,directory/'RECOVERY.json',directory/'jobs.db'):no_link(path)
    with (directory/'RECOVERY.json').open('rb') as source:raw=source.read(1024*1024+1)
    if len(raw)>1024*1024:raise ValueError('Recovery marker exceeds its limit')
    marker=json.loads(raw,object_pairs_hook=unique_json)
    if not isinstance(marker,dict) or marker.get('format')!=FORMAT or marker.get('id')!=identifier or marker.get('complete') is not True:
        raise ValueError('Recovered workspace is incomplete')
    JobStore(directory/'jobs.db')
    return directory/'jobs.db'


def recovery_list(parent):
    parent=storage_path(parent);no_link(parent)
    if not parent.exists():return {'items':[],'issues':[]}
    items=[];issues=[]
    for index,path in enumerate(parent.iterdir()):
        if index>=100:
            issues.append('Recovery listing reached 100 directory entries; not all workspaces were inspected.')
            break
        if not re.fullmatch(r'[a-f0-9]{32}',path.name):continue
        try:
            recovered_database(parent,path.name)
            marker=json.loads((path/'RECOVERY.json').read_bytes(),object_pairs_hook=unique_json)
            items.append({'id':path.name,'summary':marker['summary']})
        except (ValueError,OSError,KeyError,sqlite3.Error):
            issues.append('A recovered workspace is incomplete or incompatible; its files were preserved.')
    return {'items':items,'issues':issues}
