"""Deploy prebuilt app images and statically declared Kubernetes resources.
Actions: namespace -> ConfigMaps/storage -> Kubernetes Secret -> databases -> services -> HPA.
This command never creates a cloud cluster, and never invents deployed results.
"""
import argparse
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def run(*argv, input_text=None):
    print('+', ' '.join(argv),flush=True)
    subprocess.run(argv,check=True,input=input_text,text=True)

def apply_file(name, owner=None, tag=None):
    text=(ROOT/'k8s'/name).read_text(encoding='utf-8')
    if owner is not None:
        text=text.replace('__OWNER__',owner.lower()).replace('__TAG__',tag)
    run('kubectl','apply','-f','-',input_text=text)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--owner',required=True,help='GHCR account. Must match pushed images')
    p.add_argument('--tag',required=True,help='Existing pushed image tag')
    p.add_argument('--image-pull-secret',help='Optional existing secret for private GHCR images')
    a=p.parse_args()
    if any(ch in a.owner for ch in '/ :') or any(ch in a.tag for ch in '/ :'):
        p.error('Invalid GHCR owner or tag characters')
    run('kubectl','cluster-info')
    apply_file('00-namespace.yaml')
    apply_file('10-init-configmaps.yaml')
    apply_file('11-storage-class.yaml')
    run('python' if __import__('os').name=='nt' else 'python3',str(ROOT/'scripts/create_k8s_secrets.py'))
    if a.image_pull_secret:
        run('kubectl','-n','acit3495','patch','serviceaccount','default','-p',
            '{"imagePullSecrets":[{"name":"'+a.image_pull_secret+'"}]}')
    apply_file('12-databases.yaml')
    print('Waiting for database pods; inspect describe pvc if storage fails.',flush=True)
    run('kubectl','-n','acit3495','rollout','status','statefulset/mysql','--timeout=600s')
    run('kubectl','-n','acit3495','rollout','status','statefulset/mongo','--timeout=600s')
    apply_file('20-apps.yaml',owner=a.owner,tag=a.tag)
    for name in ['auth','analytics','enter-data','show-results']:
        run('kubectl','-n','acit3495','rollout','status','deployment/'+name,'--timeout=600s')
    apply_file('21-auth-hpa.yaml')
    run('kubectl','-n','acit3495','get','pods,svc,hpa,pvc')
    print('\nSUCCESS: Kubernetes rollout completed. Run smoke test and real HPA measurements next.')
    print('Port-forward in two terminal windows:')
    print('  kubectl -n acit3495 port-forward svc/enter-data 5000:5000')
    print('  kubectl -n acit3495 port-forward svc/show-results 3000:3000')
if __name__=='__main__':main()
