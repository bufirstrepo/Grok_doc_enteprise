import os
import json
import urllib.request
import zipfile
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
            # Download as zip
            zip_req = urllib.request.Request(
                'https://api.github.com/repos/bufirstrepo/Grok_doc_enteprise/zipball/main',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/vnd.github+json'
                }
            )
            try:
                with urllib.request.urlopen(zip_req) as zip_resp:
                    with open('/tmp/repo.zip', 'wb') as f:
                        f.write(zip_resp.read())
                    print("Downloaded zip successfully")
                    
                    # Extract
                    with zipfile.ZipFile('/tmp/repo.zip', 'r') as zip_ref:
                        zip_ref.extractall('/tmp/repo_extracted')
                    
                    # Find the extracted folder
                    extracted_folders = os.listdir('/tmp/repo_extracted')
                    if extracted_folders:
                        src_folder = os.path.join('/tmp/repo_extracted', extracted_folders[0])
                        # Copy files to project directory
                        for item in os.listdir(src_folder):
                            src = os.path.join(src_folder, item)
                            dst = os.path.join('.', item)
                            if os.path.exists(dst):
                                if os.path.isdir(dst):
                                    shutil.rmtree(dst)
                                else:
                                    os.remove(dst)
                            if os.path.isdir(src):
                                shutil.copytree(src, dst)
                            else:
                                shutil.copy2(src, dst)
                        print("Files extracted and copied successfully")
            except urllib.error.HTTPError as e:
                print(f"HTTP Error: {e.code} - trying master branch")
                # Try master branch
                zip_req = urllib.request.Request(
                    'https://api.github.com/repos/bufirstrepo/Grok_doc_enteprise/zipball/master',
                    headers={
                        'Authorization': f'Bearer {access_token}',
                        'Accept': 'application/vnd.github+json'
                    }
                )
                with urllib.request.urlopen(zip_req) as zip_resp:
                    with open('/tmp/repo.zip', 'wb') as f:
                        f.write(zip_resp.read())
                    print("Downloaded zip successfully (master branch)")
                    
                    # Extract
                    with zipfile.ZipFile('/tmp/repo.zip', 'r') as zip_ref:
                        zip_ref.extractall('/tmp/repo_extracted')
                    
                    # Find the extracted folder
                    extracted_folders = os.listdir('/tmp/repo_extracted')
                    if extracted_folders:
                        src_folder = os.path.join('/tmp/repo_extracted', extracted_folders[0])
                        # Copy files to project directory
                        for item in os.listdir(src_folder):
                            src = os.path.join(src_folder, item)
                            dst = os.path.join('.', item)
                            if os.path.exists(dst):
                                if os.path.isdir(dst):
                                    shutil.rmtree(dst)
                                else:
                                    os.remove(dst)
                            if os.path.isdir(src):
                                shutil.copytree(src, dst)
                            else:
                                shutil.copy2(src, dst)
                        print("Files extracted and copied successfully")
        else:
            print("No access token found")
else:
    print("Missing environment variables")
