import os
import json
import urllib.request

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
            # Get user info
            user_req = urllib.request.Request(
                'https://api.github.com/user',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/vnd.github+json'
                }
            )
            with urllib.request.urlopen(user_req) as user_resp:
                user = json.loads(user_resp.read().decode())
                print(f"GitHub User: {user.get('login')}")
            
            # Get repos
            repos_req = urllib.request.Request(
                'https://api.github.com/user/repos?sort=updated&per_page=10',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/vnd.github+json'
                }
            )
            with urllib.request.urlopen(repos_req) as repos_resp:
                repos = json.loads(repos_resp.read().decode())
                print("\nRecent Repositories:")
                for repo in repos:
                    print(f"- {repo['full_name']}: {repo.get('clone_url')}")
        else:
            print("No access token found")
else:
    print("Missing environment variables")
