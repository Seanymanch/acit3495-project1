"""Create Kubernetes Secret from existing Project 1 secret files, without writing generated YAML to disk."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
NAMES = ('mysql_root_password','mysql_password','mongo_root_password','mongo_app_password',
         'mongo_reader_password','jwt_secret','internal_token','demo_password')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--namespace',default='acit3495')
    a=p.parse_args()
    d=ROOT/'secrets'
    missing=[name for name in NAMES if not (d/f'{name}.txt').is_file()]
    if missing:
        sys.exit('Missing local secrets: '+', '.join(missing)+'\nRun: python scripts/generate_secrets.py')
    cmd=['kubectl','create','secret','generic','acit3495-secrets','-n',a.namespace]
    for name in NAMES: cmd.append(f'--from-file={name}={d / (name+".txt")}')
    cmd+=['--dry-run=client','-o','json']
    payload=subprocess.run(cmd,check=True,capture_output=True,text=True).stdout
    # Do not echo the secret data; kubectl apply reads it on stdin.
    result=subprocess.run(['kubectl','apply','-f','-'],input=payload,check=True,capture_output=True,text=True)
    print('Created/updated acit3495-secrets in namespace',a.namespace)
    print('Secret values were not printed or saved as Kubernetes manifests.')
if __name__=='__main__': main()
