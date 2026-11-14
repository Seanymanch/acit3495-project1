"""Set real public UI URLs after optional LoadBalancer addresses are allocated."""
import argparse, subprocess
p=argparse.ArgumentParser()
p.add_argument('--enter',required=True,help='Fully qualified http(s) URL of Enter Data')
p.add_argument('--results',required=True,help='Fully qualified http(s) URL of Show Results')
a=p.parse_args()
for url in [a.enter,a.results]:
    if not (url.startswith('http://') or url.startswith('https://')):
        p.error('Use URLs beginning http:// or https://')
subprocess.run(['kubectl','-n','acit3495','set','env','deployment/enter-data',f'SHOW_RESULTS_URL={a.results}'],check=True)
subprocess.run(['kubectl','-n','acit3495','set','env','deployment/show-results',f'ENTER_PUBLIC_URL={a.enter}'],check=True)
subprocess.run(['kubectl','-n','acit3495','rollout','status','deployment/enter-data'],check=True)
subprocess.run(['kubectl','-n','acit3495','rollout','status','deployment/show-results'],check=True)
print('Public links updated; open both sites and run the end-to-end smoke test.')
