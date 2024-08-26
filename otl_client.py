import socket
import time

def send_command(client_socket, command):
    client_socket.send(command.encode())
    time.sleep(0.1)  # небольшая задержка для обработки сервером
    response = client_socket.recv(1024).decode()
    return response

def test_server(host='localhost', port=9091):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    
    try:
        # Авторизация администратора
        client_socket.send('admin'.encode())
        time.sleep(0.1)
        client_socket.send('admin'.encode())
        response = client_socket.recv(1024).decode()
        if "Authentication successful" not in response:
            print("Error: Authentication failed for admin")
            return
        
        # Тестирование команды 'users'
        response = send_command(client_socket, 'users')
        if 'admin' not in response or 'user1' not in response or 'user2' not in response:
            print("Error: 'users' command failed")
            return
        
        # Тестирование команды 'adduser'
        response = send_command(client_socket, 'adduser newuser newpassword 5000')
        if "User newuser added with quota 5000 bytes" not in response:
            print("Error: 'adduser' command failed")
            return

        # Проверка, что новый пользователь добавлен
        response = send_command(client_socket, 'users')
        if 'newuser' not in response:
            print("Error: 'users' command failed to list new user")
            return
        
        # Тестирование команды 'setquota'
        response = send_command(client_socket, 'setquota newuser 10000')
        if "Quota for user newuser set to 10000 bytes" not in response:
            print("Error: 'setquota' command failed")
            return
        
        # Тестирование команды 'deluser'
        response = send_command(client_socket, 'deluser newuser')
        if "User newuser deleted" not in response:
            print("Error: 'deluser' command failed")
            return
        
        # Тестирование команды 'ls' для пустой папки
        response = send_command(client_socket, 'ls')
        if response.strip() != "Directory is empty":
            print("Error: 'ls' command failed for empty directory")
            return
        
        # Тестирование команды 'mkdir'
        send_command(client_socket, 'mkdir test_folder')
        response = send_command(client_socket, 'ls')
        if response.strip() == "Directory is empty":
            print("Error: 'mkdir' command failed")
            return
        
        # Тестирование команды 'rmdir'
        response = send_command(client_socket, 'rmdir test_folder')
        response = send_command(client_socket, 'ls')
        if 'test_folder' in response:
            print("Error: 'rmdir' command failed")
            return
        
        # Тестирование команды 'upload'
        response = send_command(client_socket, 'upload test.txt')
        print("proverka")
        # time.sleep(0.1)
        # response = client_socket.recv(1024).decode()
        if "File 'test.txt' uploaded." not in response:
            print("Error: 'upload' command failed")
            return
        
        # Тестирование команды 'download'
        send_command(client_socket, 'download test.txt')
        time.sleep(0.1)
        # response = client_socket.recv(1024).decode()
        if "File 'test.txt' downloaded." not in response:
            print("Error: 'download' command failed")
            return
        
        # Тестирование команды 'rm'
        send_command(client_socket, 'rm test.txt')
        response = send_command(client_socket, 'ls')
        if 'test.txt' in response:
            print("Error: 'rm' command failed")
            return
        
        print("All tests passed successfully.")
    
    finally:
        send_command(client_socket, 'exit')
        client_socket.close()

if __name__ == '__main__':
    test_server()
