import os
import json
import urllib.request
import subprocess
import shutil

hostname = os.environ.get('REPLIT_CONNECTORS_HOSTNAME')
x_replit_token = None

if os.environ.get('REPL_IDENTITY'):
    x_replit_token = 'repl ' + os.environ['REPL_IDENTITY']
elif os.environ.get('WEB_REPL_RENEWAL'):
    x_replit_token = 'depl ' + os.environ['WEB_REPL_RENEWAL']

if x_replit_token and hostname:
    req = urllib.request.Request(
        f'https://{hostname}/api/v2/connection?include_secrets=true&connector_names=github',
        headers={
            'Accept': 'application/json',
            'X_REPLIT_TOKEN': x_replit_token
        }
    )
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        connection = data.get('items', [{}])[0]
        settings = connection.get('settings', {})
        access_token = settings.get('access_token') or settings.get('oauth', {}).get('credentials', {}).get('access_token')
        
        if access_token:
            # Clone to temp directory
            temp_dir = '/tmp/repo_clone'
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            clone_url = f"https://{access_token}@github.com/bufirstrepo/Grok_doc_enteprise.git"
            result = subprocess.run(['git', 'clone', clone_url, temp_dir], capture_output=True, text=True)
            print("Clone output:", result.stdout, result.stderr)
            
            # Move all files except .git to current directory
            for item in os.listdir(temp_dir):
                src = os.path.join(temp_dir, item)
                dst = os.path.join('.', item)
                if os.path.exists(dst):
                    if os.path.isdir(dst):
                        shutil.rmtree(dst)
                    else:
                        os.remove(dst)
                shutil.move(src, dst)
            print("Files moved successfully")
        else:
            print("No access token found")
else:
    print("Missing environment variables")
