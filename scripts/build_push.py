"""Build and push the four REAL Project 1 service images to GHCR.
Prerequisite: `docker login ghcr.io` with a credential allowed to write packages.
"""
import argparse
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SERVICES={'auth':'auth','analytics':'analytics','enter-data':'enter-data','show-results':'show-results'}
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--owner',required=True,help='GHCR account / organization, for example seanymanch')
    p.add_argument('--tag',required=True,help='Use a unique, immutable release tag, e.g. p2-v1')
    p.add_argument('--platform',default='linux/amd64',help='EKS t3.medium workers use linux/amd64')
    p.add_argument('--no-push',action='store_true')
    a=p.parse_args()
    owner=a.owner.lower()
    for service,folder in SERVICES.items():
        name=f'ghcr.io/{owner}/acit3495-{service}:{a.tag}'
        print('Building',name,flush=True)
        subprocess.run(['docker','build','--platform',a.platform,'-t',name,str(ROOT/folder)],check=True)
        if not a.no_push:
            print('Pushing',name,flush=True)
            subprocess.run(['docker','push',name],check=True)
    if a.no_push: print('Images built locally only; cannot deploy to EKS until images are pushed.')
if __name__=='__main__':main()
