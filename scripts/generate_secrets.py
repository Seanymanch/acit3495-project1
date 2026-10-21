"""One-time local demo secrets. Never commit generated contents."""
import secrets
from pathlib import Path
folder=Path(__file__).resolve().parents[1]/'secrets'
folder.mkdir(exist_ok=True)
for name in ['mysql_root_password','mysql_password','mongo_root_password','mongo_app_password','mongo_reader_password','jwt_secret','internal_token','demo_password']:
    path=folder/(name+'.txt')
    if path.exists():
        print(f'{name}: existing file preserved')
    else:
        path.write_text(secrets.token_urlsafe(32)+'\n', encoding='utf-8')
        print(f'{name}: generated')
print('Demo username: student')
print('Demo password: read secrets/demo_password.txt locally, do not commit or screenshot it')
