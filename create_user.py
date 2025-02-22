import sys
from librouteros import connect

# MikroTik API credentials and connection details
router_api = {
    'host': '192.168.88.1',  # Replace with your router's IP address
    'username': 'admin',
    'password': 'A35QOGURSS'  # Replace with your router's password
}

def create_user(username, password, profile):
    try:
        api = connect(**router_api)
        api(cmd='/ip/hotspot/user/add', name=username, password=password, profile=profile)
        print(f'User {username} created successfully')
    except Exception as e:
        print(f'Failed to create user: {e}')

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python create_user.py <username> <password> <profile>")
        sys.exit(1)
    username = sys.argv[1]
    password = sys.argv[2]
    profile = sys.argv[3]
    create_user(username, password, profile)