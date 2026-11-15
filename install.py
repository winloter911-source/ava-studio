"""AVA release downloader. Verifies files before installing; preserves existing data."""
import argparse,hashlib,json,os,platform,re,shutil,stat,subprocess,sys,tempfile,time,urllib.request,zipfile
from pathlib import Path,PurePosixPath
REPO='winloter911-source/ava-studio'
EXPECTED_SHA256='dd01086695a9a575227dc2dbb0d903d3e225f0153bfb92b7ec12ea39f434c94d'
MAX_DOWNLOAD=1024**3
MAX_EXPANDED=2*1024**3

def safe_path(name):
 if not name or '\\' in name or ':' in name or name.startswith('/') or any(x in ('','.','..') for x in name.split('/')):raise ValueError('Unsafe archive path')
 return PurePosixPath(name)

def download(url,dest,limit):
 if not url.startswith('https://'):raise ValueError('HTTPS required')
 req=urllib.request.Request(url,headers={'User-Agent':'AVA-Studio-Installer','Accept':'application/vnd.github+json'})
 total=0;start=time.monotonic()
 with urllib.request.urlopen(req,timeout=30) as response,dest.open('wb') as out:
  if not response.geturl().startswith('https://'):raise ValueError('Insecure redirect')
  while True:
   chunk=response.read(1024*1024)
   if not chunk:break
   total+=len(chunk)
   if total>limit or time.monotonic()-start>1800:raise ValueError('Download exceeded its limit')
   out.write(chunk)

def fetch_release(work):
 meta=work/'release.json'
 try:download(f'https://api.github.com/repos/{REPO}/releases/latest',meta,2*1024**2)
 except Exception as e:raise ValueError('No accessible published latest release. Draft releases cannot be installed by members.') from e
 data=json.loads(meta.read_text())
 allowed={'AVA-Studio.zip','AVA-Studio-2026-11-15.zip'}
 assets=[a for a in data.get('assets',[]) if a.get('name') in allowed]
 if len(assets)!=1:raise ValueError('Release must contain exactly one AVA Studio ZIP asset.')
 url=assets[0].get('browser_download_url','')
 if not url.startswith(f'https://github.com/{REPO}/releases/download/'):raise ValueError('Unexpected release asset URL')
 archive=work/'AVA-Studio.zip';download(url,archive,MAX_DOWNLOAD);return archive

def verify(archive,expected=EXPECTED_SHA256):
 digest=hashlib.sha256()
 with archive.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):digest.update(block)
 if digest.hexdigest()!=expected:raise ValueError('Archive checksum mismatch. Nothing installed. Obtain matching installer and release from the owner.')
 with zipfile.ZipFile(archive) as z:
  entries=z.infolist()
  if len(entries)>20000 or sum(i.file_size for i in entries)>MAX_EXPANDED:raise ValueError('Oversized archive')
  seen=set();files=[]
  for i in entries:
   path=safe_path(i.filename.rstrip('/'));normalized=str(path).casefold()
   if normalized in seen:raise ValueError('Duplicate archive path')
   seen.add(normalized)
   mode=i.external_attr>>16
   if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0,stat.S_IFREG,stat.S_IFDIR)):raise ValueError('Unsupported archive file type')
   if not i.is_dir():files.append(str(path))
  roots={str(PurePosixPath(n).parent) for n in files if n.endswith('/MANIFEST.json') and len(PurePosixPath(n).parts)==2}
  if len(roots)!=1:raise ValueError('Expected one AVA application root')
  root=roots.pop();manifest_path=root+'/MANIFEST.json'
  if z.getinfo(manifest_path).file_size>8*1024**2:raise ValueError('Manifest too large')
  manifest=json.loads(z.read(manifest_path))
  if not isinstance(manifest,dict):raise ValueError('Invalid manifest')
  required={'Setup.command','Open Studio.command','INSTALL-AGENT.md','AGENTS.md','web_server.py'}
  if not required.issubset(manifest):raise ValueError('Incomplete app package')
  expected_files={manifest_path}
  for rel,record in manifest.items():
   safe_path(rel);name=root+'/'+rel;expected_files.add(name)
   if not isinstance(record,dict) or not re.fullmatch('[a-f0-9]{64}',record.get('sha256','')):raise ValueError('Invalid file checksum')
   payload=z.read(name)
   if len(payload)!=record.get('bytes') or hashlib.sha256(payload).hexdigest()!=record['sha256']:raise ValueError('File verification failed: '+rel)
  if set(files)!=expected_files:raise ValueError('Unverified files in archive')
 return root,manifest

def unpack(archive,dest,expected=EXPECTED_SHA256):
 dest=Path(dest).expanduser().absolute()
 if dest.exists() or dest.is_symlink():raise ValueError('Destination already exists; choose a new folder. Existing data will not be overwritten.')
 root,manifest=verify(archive,expected)
 dest.parent.mkdir(parents=True,exist_ok=True)
 stage=Path(tempfile.mkdtemp(prefix='.ava-install-',dir=dest.parent));reserved=False
 try:
  with zipfile.ZipFile(archive) as z:
   for rel in [*manifest,'MANIFEST.json']:
    target=stage/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(root+'/'+rel))
    target.chmod(0o755 if target.suffix in ('.sh','.command') else 0o644)
  # Atomic reservation prevents overwriting even an empty existing directory.
  dest.mkdir(mode=0o700);reserved=True
  for p in stage.iterdir():shutil.move(str(p),dest/p.name)
 except Exception:
  if reserved:print('Installation incomplete; keep the destination for diagnosis: '+str(dest),file=sys.stderr)
  raise
 finally:shutil.rmtree(stage,ignore_errors=True)
 return dest

def main():
 p=argparse.ArgumentParser();p.add_argument('--directory',default=str(Path.home()/'AVA Studio'));p.add_argument('--package',type=Path);p.add_argument('--verify-only',action='store_true');p.add_argument('--setup',action='store_true');a=p.parse_args()
 if a.verify_only:
  if not a.package:p.error('--verify-only requires --package')
  verify(a.package);print('Archive and file manifest verified. No installation or paid calls.');return
 if platform.system()!='Darwin' or int(platform.mac_ver()[0].split('.')[0])<14:raise ValueError('This build requires Apple Silicon macOS 14+.')
 chip=subprocess.run(['sysctl','-n','hw.optional.arm64'],capture_output=True,text=True).stdout.strip()
 if chip!='1':raise ValueError('This build requires Apple Silicon.')
 with tempfile.TemporaryDirectory(prefix='ava-download-') as tmp:
  archive=a.package or fetch_release(Path(tmp));dest=unpack(archive,a.directory)
 print('AVA Studio files installed: '+str(dest),flush=True)
 if a.setup:subprocess.run(['/bin/bash','Setup.command'],cwd=dest,check=True)
 print('Read INSTALL-AGENT.md in the installed folder, finish verification, then run Open Studio.command. Configure your own keys in Settings.')
if __name__=='__main__':
 try:main()
 except Exception as e:print('Installation stopped: '+str(e),file=sys.stderr);sys.exit(1)
