"""New model switch: offline fixtures only, NO 70GB downloads."""
import hashlib
import io
from pathlib import Path
import tempfile
import threading
import time
import unittest

from model_variants import (
    ModelDownloadError, ModelDownloadCancelled, TIERS, shard_names, parse_tree,
    model_manifest, sc117_official_args, install_parent, download_one,
    download_sc117,
)
from terminal_backend import build_official_command, TerminalError
from guide_rules import GUIDES
from beginner_help import HINTS
from mascot import STAGE_POSES, TIPS
from session import Session

class FakeResponse(io.BytesIO):
    def __init__(self, payload, status=200, headers=None):
        super().__init__(payload)
        self.status=status
        self.headers=headers or {}
    def geturl(self):return 'https://cas-bridge.xethub.hf.co/test'

class VariantTests(unittest.TestCase):
    def test_tiers_and_shards(self):
        for tier in TIERS:
            names=shard_names(tier)
            self.assertEqual(len(names),2)
            self.assertTrue(names[0].endswith('00001-of-00002.gguf'))
            self.assertIn(tier,names[0])
        with self.assertRaises(ModelDownloadError):shard_names('IQ3_S & del')

    def test_sc117_cmd_points_to_its_own_gguf_and_data_dir(self):
        for tier in TIERS:
            args=sc117_official_args(tier,['--gpu','1'])
            cmd=build_official_command(args)
            self.assertIn('--setup --family qwen --model '+tier,cmd)
            self.assertIn('--gguf-dir ..\\SC117-GGUF\\'+tier,cmd)
            self.assertIn('--data-dir ..\\Strata-data',cmd)
            self.assertTrue(cmd.endswith('--gpu 1'))
        self.assertEqual(build_official_command(), 'cmd.exe /d /q /c call START-HERE.bat')
        with self.assertRaises(TerminalError):build_official_command(['--family','qwen','--model','IQ3_S'])
        with self.assertRaises(TerminalError):build_official_command(sc117_official_args('IQ3_S')+['--yes'])
        with self.assertRaises(TerminalError):build_official_command(sc117_official_args('IQ3_S')[:-2]+['--data-dir','..\\Bad'])

    def test_tree_requires_two_shards_and_sha(self):
        tier='IQ3_S'
        entries=[{'path':f'{tier}/{name}','size':48_000_000_000,
                  'lfs':{'oid':hashlib.sha256(name.encode()).hexdigest()}} for name in shard_names(tier)]
        self.assertEqual(parse_tree(entries,tier)[0][1],48_000_000_000)
        with self.assertRaises(ModelDownloadError):parse_tree(entries[:1],tier)
        with self.assertRaises(ModelDownloadError):parse_tree([dict(entries[0],lfs={}),entries[1]],tier)
        sha='a'*40
        urls=[]
        def fetch(url):
            urls.append(url)
            return {'sha':sha} if len(urls)==1 else entries
        got, _=model_manifest(tier,fetch=fetch)
        self.assertEqual(got,sha)
        self.assertIn(sha,urls[1])

    def test_full_download_checksum_and_no_overwrite(self):
        payload=b'GGUF'+b'x'*500
        digest=hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'model.gguf'
            download_one(dest,'https://huggingface.co/fake',len(payload),digest,lambda x:None,None,
                         opener=lambda req,timeout:FakeResponse(payload))
            self.assertEqual(dest.read_bytes(),payload)
            download_one(dest,'https://huggingface.co/fake',len(payload),digest,lambda x:None,None,
                         opener=lambda req,timeout:self.fail('must not download again'))
            dest.write_bytes(payload[:-1]+b'!')
            with self.assertRaises(ModelDownloadError):
                download_one(dest,'https://huggingface.co/fake',len(payload),digest,lambda x:None,None,
                             opener=lambda req,timeout:self.fail('must not overwrite invalid'))

    def test_range_resume(self):
        payload=b'GGUF'+b'abcd'*32
        digest=hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'model.gguf'
            dest.with_name(dest.name+'.part').write_bytes(payload[:11])
            def opener(req,timeout):
                self.assertEqual(req.get_header('Range'),'bytes=11-')
                return FakeResponse(payload[11:],206,{'Content-Range':f'bytes 11-{len(payload)-1}/{len(payload)}'})
            download_one(dest,'https://huggingface.co/fake',len(payload),digest,lambda x:None,None,opener=opener)
            self.assertEqual(dest.read_bytes(),payload)
            self.assertFalse(dest.with_name(dest.name+'.part').exists())

    def test_server_not_supporting_resume_keeps_part(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'model.gguf'
            part=dest.with_name(dest.name+'.part')
            part.write_bytes(b'abc')
            with self.assertRaises(ModelDownloadError):
                download_one(dest,'https://huggingface.co/fake',6,'0'*64,lambda x:None,None,
                             opener=lambda req,timeout:FakeResponse(b'abcdef'))
            self.assertEqual(part.read_bytes(),b'abc')

    def test_cancellation_does_not_commit_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'model.gguf'
            cancel=threading.Event();cancel.set()
            with self.assertRaises(ModelDownloadCancelled):
                download_one(dest,'https://huggingface.co/fake',100,'0'*64,lambda x:None,cancel)
            self.assertFalse(dest.exists())

    def test_sc117_model_acquisition_only_uses_dedicated_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp);seen=[]
            def manifest(tier):
                return 'e'*40,[(f'{tier}/{n}',1,'0'*64) for n in shard_names(tier)]
            def downloader(dest,url,size,digest,log,cancel):
                seen.append((dest,url));dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b'GGUF')
            # We stub the network/disk payload, so no pretend SHA validation here.
            folder=download_sc117('IQ2_XS',source,lambda x:None,None,manifest=manifest,downloader=downloader)
            self.assertEqual(folder,install_parent(source)/'SC117-GGUF'/'IQ2_XS')
            self.assertEqual(len(seen),2)
            self.assertTrue(all('/resolve/'+'e'*40+'/' in url for _,url in seen))
            self.assertFalse((source/'Strata-data').exists())
            self.assertTrue((folder/'SC117_DOWNLOAD_RECORD.json').is_file())

    def test_ui_stages_including_mascot(self):
        for code in ('sc117_download','sc117_prepare'):
            self.assertIn(code,GUIDES)
            self.assertIn(code,HINTS)
            self.assertIn(code,TIPS)
            self.assertIn(code,STAGE_POSES)

class SessionIntegration(unittest.TestCase):
    def test_no_sc117_launch_before_download_finishes(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)
            started=[]
            class FakeBackend:
                def __init__(self,emit): self.emit=emit
                def start(self,folder,args=None):started.append((folder,args))
                def is_alive(self):return False
            def source(parent, log, cancel):
                folder=parent/'Strata-Official';folder.mkdir(parents=True)
                for name in ('START-HERE.bat','SETUP.bat','setup.py','LICENSE'):
                    (folder/name).write_text('',encoding='utf-8')
                (folder/'.strata-easy-tw-source.json').write_text('{}')
                return folder,'a'*40,'f'*64
            class Port:
                occupied=False;healthy=False;reason=''
            def model_fail(tier,base,log,cancel):raise ModelDownloadError('simulate network fail')
            session=Session(backend_factory=FakeBackend,downloader=source,
                            model_downloader=model_fail,probe=lambda:Port())
            session.start('download',target,variant='sc117',tier='IQ3_S')
            end=time.monotonic()+2
            while session.active() and time.monotonic()<end:time.sleep(.01)
            self.assertFalse(started)
            self.assertTrue(any('network fail' in str(p) for k,p in session.drain(100) if k=='error'))

if __name__=='__main__':unittest.main()
