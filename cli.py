"""Operator CLI; Docker setup and verification are explicit local operations."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from core import verify
from controller import Controller
from runtime import DockerRuntime, MODEL_IMAGE
from storage import Store


def main():
    p=argparse.ArgumentParser(prog='boundarylab');sub=p.add_subparsers(dest='cmd',required=True)
    prep=sub.add_parser('prepare');prep.add_argument('--with-model',action='store_true')
    sub.add_parser('doctor')
    run=sub.add_parser('run');run.add_argument('--profile',choices=['hardened','weak'],default='hardened');run.add_argument('--data',default='data')
    export=sub.add_parser('export');export.add_argument('run_id');export.add_argument('--data',default='data');export.add_argument('--output',required=True)
    check=sub.add_parser('verify');check.add_argument('bundle');check.add_argument('--checkpoint',required=True,help='Original separately retained checkpoint, not one supplied by evidence author')
    args=p.parse_args()
    if args.cmd=='prepare':
        if not shutil.which('docker'):p.error('Install and start Docker Desktop (Linux containers) or Docker Engine first')
        subprocess.run(['docker','build','-t','boundarylab-probe:local',str(Path(__file__).parent.resolve())],check=True)
        if args.with_model:subprocess.run(['docker','pull',MODEL_IMAGE],check=True)
    elif args.cmd=='doctor':
        import os
        result={'python':sys.version.split()[0],'docker_cli':bool(shutil.which('docker')),'model_configured':bool(os.environ.get('BOUNDARYLAB_MODEL'))}
        try:result.update(DockerRuntime('doctor').doctor())
        except Exception as error:result['docker_error']=str(error)
        print(json.dumps(result,indent=2))
    elif args.cmd=='run':
        store=Store(args.data);controller=Controller(store);run_id=controller.start(args.profile);controller.thread.join()
        print(json.dumps(store.export(run_id),indent=2))
    elif args.cmd=='export':
        Path(args.output).write_text(json.dumps(Store(args.data).export(args.run_id),indent=2),encoding='utf-8')
        print(args.output)
    elif args.cmd=='verify':
        try:
            bundle=json.loads(Path(args.bundle).read_text(encoding='utf-8'))
            checkpoint=json.loads(Path(args.checkpoint).read_text(encoding='utf-8'))
            ok=verify(bundle['events'],checkpoint)
        except (OSError,ValueError,KeyError,TypeError):ok=False
        print('VERIFIED' if ok else 'VERIFICATION FAILED');return 0 if ok else 1
    return 0

if __name__=='__main__':raise SystemExit(main())
