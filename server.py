import os
import shutil
import socket
import threading
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger()

# Файлы для логирования
file_handler_conn = logging.FileHandler('connections.log')
file_handler_ops = logging.FileHandler('operations.log')
file_handler_auth = logging.FileHandler('auth.log')

file_handler_conn.setLevel(logging.INFO)
file_handler_ops.setLevel(logging.INFO)
file_handler_auth.setLevel(logging.INFO)

conn_logger = logging.getLogger('connections')
ops_logger = logging.getLogger('operations')
auth_logger = logging.getLogger('auth')

conn_logger.addHandler(file_handler_conn)
ops_logger.addHandler(file_handler_ops)
auth_logger.addHandler(file_handler_auth)

# Директория для данных пользователей
USERS_DIR = os.path.join(os.getcwd(), 'users')
if not os.path.exists(USERS_DIR):
    os.makedirs(USERS_DIR)

# Простая база данных пользователей
users_db = {
    'admin': {'password': 'admin', 'role': 'admin', 'quota': 100 * 1024},  # Квота None для неограниченного пространства
    'user1': {'password': 'password1', 'role': 'user', 'quota': 1},  # 10KB quota for testing
    'user2': {'password': 'password2', 'role': 'user', 'quota': 20 * 1024}  # 20KB quota for testing
}

# Функция для проверки использования квоты
def get_used_space(user_dir):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(user_dir):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

def check_quota(user_dir, username):
    total_size = get_used_space(user_dir)
    quota = users_db[username]['quota']
    if quota:
        logger.info(f"User {username} is using {total_size} out of {quota} bytes.")
    return total_size <= quota if quota else True

def authenticate(client_socket):
    try:
        
        username = client_socket.recv(1024).decode().strip()
        
        password = client_socket.recv(1024).decode().strip()
        if username in users_db and users_db[username]['password'] == password:
            auth_logger.info(f"User {username} logged in")
            client_socket.send("Authentication successful.\n".encode())
            return username
        else:
            auth_logger.warning(f"Failed login attempt for username {username}")
            client_socket.send("Authentication failed.\n".encode())
            client_socket.close()
            return None
    except Exception as e:
        auth_logger.error(f"Error during authentication: {str(e)}")
        client_socket.close()
        return None

def receive_large_data(client_socket):
    data = b""
    while True:
        part = client_socket.recv(1024)
        if b"EOF" in part:
            data += part.split(b"EOF")[0]  # Remove the EOF marker
            break
        data += part
    return data.decode()

def process_request(client_socket, username):
    user_dir = os.path.join(USERS_DIR, username)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    
    while True:
        try:
            request = client_socket.recv(1024).decode().strip()
            if not request:
                break
            ops_logger.info(f"User {username} request: {request}")
            command, *args = request.split(maxsplit=1)

            if command == 'ls':
                files = os.listdir(user_dir)
                response = '; '.join(files) if files else 'Directory is empty'
                client_socket.send(response.encode())
            
            elif command == 'mkdir' and len(args) == 1:
                os.makedirs(os.path.join(user_dir, args[0]))
                response = "folder created"
                client_socket.send(response.encode())
            
            elif command == 'rmdir' and len(args) == 1:
                shutil.rmtree(os.path.join(user_dir, args[0]))
                response = "folder deleated"
                client_socket.send(response.encode())
            
            elif command == 'rm' and len(args) == 1:
                os.remove(os.path.join(user_dir, args[0]))
                response = "file deleated"
                client_socket.send(response.encode())
            
            elif command == 'rename' and len(args) == 1:
                old_name, new_name = args[0].split()
                os.rename(os.path.join(user_dir, old_name), os.path.join(user_dir, new_name))
            
            elif command == 'upload' and len(args) == 1:
                filename = args[0]
                filecontent = receive_large_data(client_socket)
                filepath = os.path.join(user_dir, filename)
                file_size = len(filecontent)

                # Check quota before writing the file
                if get_used_space(user_dir) + file_size > users_db[username]['quota']:
                    client_socket.send("Quota exceeded. Upload failed.\n".encode())
                    continue

                with open(filepath, 'w') as f:
                    f.write(filecontent)
                
                response = f"File '{filename}' uploaded."
                client_socket.send(response.encode())
            
            elif command == 'download' and len(args) == 1:
                filename = args[0]
                filepath = os.path.join(user_dir, filename)
                if os.path.exists(filepath):
                    with open(filepath, 'rb') as f:
                        while True:
                            data = f.read(1024)
                            if not data:
                                break
                            client_socket.sendall(data)
                    client_socket.send(b"EOF")
            
            elif command == 'exit':
                response = 'Goodbye!'
                client_socket.send(response.encode())
                break
            
            elif command == 'users' and users_db[username]['role'] == 'admin':
                response = "; ".join([f"{user}: {users_db[user]['quota']} bytes" for user in users_db])
                client_socket.send(response.encode())
            
            elif command == 'setquota' and users_db[username]['role'] == 'admin' and len(args) == 1:
                user_quota = args[0].split()
                if len(user_quota) == 2 and user_quota[0] in users_db:
                    users_db[user_quota[0]]['quota'] = int(user_quota[1])
                    response = f"Quota for user {user_quota[0]} set to {user_quota[1]} bytes."
                else:
                    response = "Invalid command or user."
                client_socket.send(response.encode())

            elif command == 'deluser' and users_db[username]['role'] == 'admin' and len(args) == 1:
                del_username = args[0]
                if del_username in users_db:
                    del users_db[del_username]
                    shutil.rmtree(os.path.join(USERS_DIR, del_username))
                    response = f"User {del_username} deleted."
                else:
                    response = "User not found."
                client_socket.send(response.encode())
            
            elif command == 'adduser' and users_db[username]['role'] == 'admin' and len(args) == 1:
                new_user_info = args[0].split()
                if len(new_user_info) == 3:
                    new_username, new_password, new_quota = new_user_info
                    if new_username not in users_db:
                        register_user(new_username, new_password, quota=int(new_quota))
                        response = f"User {new_username} added with quota {new_quota} bytes."
                    else:
                        response = "User already exists."
                else:
                    response = "Invalid command format. Use: adduser <username> <password> <quota>"
                client_socket.send(response.encode())
            
            else:
                continue
        
        except Exception as e:
            continue
    
    client_socket.close()

def register_user(username, password, role='user', quota=None):
    if username not in users_db:
        users_db[username] = {'password': password, 'role': role, 'quota': quota}
        user_dir = os.path.join(USERS_DIR, username)
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
        auth_logger.info(f"User {username} registered with role {role}")
        return True
    else:
        auth_logger.warning(f"Registration attempt for existing username {username}")
        return False

def handle_client_connection(client_socket):
    username = authenticate(client_socket)
    if username:
        process_request(client_socket, username)

def start_server(host='localhost', port=9091):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)
    conn_logger.info(f"Server listening on {host}:{port}")
    
    while True:
        client_socket, addr = server_socket.accept()
        conn_logger.info(f"Accepted connection from {addr}")
        
        client_handler = threading.Thread(target=handle_client_connection, args=(client_socket,))
        client_handler.start()

if __name__ == '__main__':
    # Пример регистрации новых пользователей
    register_user('user1', 'password1', quota=1)  # 10KB quota for testing
    register_user('user2', 'password2', quota=20*1024)  # 20KB quota for testing
    register_user('admin', 'admin', role='admin', quota=100*1024)  # Admin user with no quota
    
    start_server()
