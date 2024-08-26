import socket
import os

def start_client(host='localhost', port=9091):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    
    username = input('Username: ')
    client_socket.send(username.encode())
    password = input('Password: ')
    client_socket.send(password.encode())
    
    auth_response = client_socket.recv(1024).decode()
    print(auth_response)
    if "Authentication failed" in auth_response:
        client_socket.close()
        return
    
    while True:
        request = input('myftp@shell$ ')
        command, *args = request.strip().split(maxsplit=1)
        client_socket.send(request.encode())
        
        if command == 'upload' and len(args) == 1:
            filename = args[0]
            if os.path.exists(filename):
                with open(filename, 'rb') as file:
                    file_content = file.read()
                client_socket.sendall(file_content + b"EOF")
                response = client_socket.recv(1024).decode()
                print(response)
            else:
                print(f"File '{filename}' not found.")
        
        elif command == 'download' and len(args) == 1:
            filename = args[0]
            with open(filename, 'wb') as f:
                while True:
                    data = client_socket.recv(1024)
                    if b"EOF" in data:
                        f.write(data.split(b"EOF")[0])
                        break
                    f.write(data)
            print(f"File '{filename}' downloaded.")
            continue
        
        elif command == 'ls' or command == 'exit' or command.startswith('adduser') or command.startswith('setquota') or command.startswith('deluser') or command == 'users':
            response = client_socket.recv(1024).decode()
            print(response)
        
        else:
            response = client_socket.recv(1024).decode()
            print(response)

        if command == 'exit':
            break

    client_socket.close()

if __name__ == '__main__':
    start_client()
