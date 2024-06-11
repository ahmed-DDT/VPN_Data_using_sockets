import socket
import threading
import json
import os
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor


data_store = {}
conn_store = {}
lock = threading.Lock()
SOCKET_TIMEOUT = 60  # seconds
HOST = '0.0.0.0'
PORT = 445
COMMAND_SOCK_ADD = "/tmp/server_socket_1"

def handle_client(conn, addr):
    print(f"Client connected: {addr}")
    unique_id = None
    conn.settimeout(SOCKET_TIMEOUT)
    more = False
    chunk_data = b""

    try:
        while True:
            try:
                data = conn.recv(1048576)
                if not data:
                    break
                try:
                    if more:
                        user_data = json.loads((chunk_data + data).decode())
                        if unique_id is None:
                            unique_id = user_data['ip']
                        print(f"Data received from client {unique_id}.")
                        more = False
                        chunk_data = b""
                    else:
                        user_data = json.loads(data.decode())
                        if unique_id is None:
                            unique_id = user_data['ip']
                        print(f"Data received from client {unique_id}.")
                    print(user_data)
                except json.JSONDecodeError:
                    more = True
                    chunk_data += data
                    print("Chunck received")
                    continue
                
                with lock:
                    data_store[unique_id] = user_data
                    conn_store[unique_id] = conn
            except (ConnectionResetError, socket.timeout) as exp:
                print(f"Error: {exp}")
                break
    except Exception as exp:
        print(f"Error: {exp}")
    finally:
        with lock:
            if unique_id in data_store:
                del data_store[unique_id]
                del conn_store[unique_id]
        conn.close()

def start_server(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen()
        print("Server listening on port", port)
        with ThreadPoolExecutor(max_workers=20) as executor:
            while True:
                try:
                    conn, addr = s.accept()
                    print(f"Connection established with {addr}")
                    executor.submit(handle_client, conn, addr)
                except OSError as e:
                    if e.errno == 24:  # Too many open files
                        print("Too many open files. Adjusting ulimit or reducing connections.")
                    else:
                        raise

def command_server(command_sock_add):
    if os.path.exists(command_sock_add):
        os.remove(command_sock_add)
    
    server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server_socket.bind(command_sock_add)
    server_socket.listen()

    print("Command server listening...")
    while True:
        try:
            response = None
            conn, _ = server_socket.accept()
            data = conn.recv(1024).decode()
            if not data == "count":
                print("data", data)
            if data.startswith("fetch"):
                if data == "fetch all":
                    print("Fetching all")
                    with lock:
                        response = json.dumps(data_store, indent=4)
                elif len(data.split()) == 3:
                    _, d_type, user_id = data.split()
                    print(f"Fetching {d_type} for {user_id}")
                    with lock:
                        try:
                            response = json.dumps(data_store[user_id][d_type], indent=4)
                        except KeyError:
                            response = json.dumps({"message": "No data found for the specified key"}, indent=4)
                elif data == "fetch":
                    with lock:
                        response = json.dumps({"keys": ' '.join(list(data_store.keys()))}, indent=4)
                else:
                    response = json.dumps({"message": f"Invalid command {data}"}, indent=4)
            elif data == "count":
                with lock:
                    response = json.dumps({"total_users": len(data_store)}, indent=4)
            elif data.startswith("stop"):
                try:
                    conn_store[data.split()[2]].sendall(data.encode())
                    response = json.dumps({"message": "command sent"}, indent=4)
                except KeyError:
                    response = json.dumps({"message": "No connection found for the specified key"}, indent=4)
            elif data.startswith("start"):
                try:
                    conn_store[data.split()[2]].sendall(data.encode())
                    response = json.dumps({"message": "command sent"}, indent=4)
                except KeyError:
                    response = json.dumps({"message": "No connection found for the specified key"}, indent=4)
            conn.send(response.encode())
            conn.close()
        except OSError as e:
            if e.errno == 24:  # Too many open files
                print("Too many open files in command server. Adjusting ulimit or reducing connections.")
            else:
                print(e)

def command_client(command: str, command_sock_add):
    client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client_socket.connect(command_sock_add)
    client_socket.send(command.encode())
    more = False
    chunk_data = b""
    while True:
        data = client_socket.recv(4096)
        if not data:
            break
        try:
            if more:
                user_data = json.loads((chunk_data + data).decode())
            else:
                user_data = json.loads(data.decode())
            client_socket.close()
            return user_data
        except json.JSONDecodeError:
            more = True
            chunk_data += data
            continue

def start_host(command: str="start", host=HOST, port:int=PORT, command_sock_add=COMMAND_SOCK_ADD):
    try:
        [print(f"Starting the server on port {port}...") if command == "start" else None]
        cmd: list=command.split(' ')
        try:
            if cmd[0] == "start":
                server_thread = threading.Thread(target=start_server, args=(host, port))
                server_thread.daemon = True
                server_thread.start()

                command_thread = threading.Thread(target=command_server, args=(command_sock_add,))
                command_thread.daemon = True
                command_thread.start()

                # Keep the main thread alive
                command_thread.join()
            elif cmd[0] == "fetch":
                print(command_client(' '.join(cmd), command_sock_add))
            elif cmd[0] == "-q":
                print(command_client("count", command_sock_add))
            elif cmd[0] == "send":
                print(command_client(f" ".join(cmd[1:]), command_sock_add))
            else:
                print("Invalid command")
        except IndexError:
            print("Invalid command")
    except KeyboardInterrupt:
        print("Exiting...")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--command', type=str, default="start", help='start, fetch, send, -q')
    parser.add_argument('--host', type=str, default=HOST, help='host')
    parser.add_argument('--port', type=int, default=PORT, help='port')
    parser.add_argument('--command_sock_add', type=str, default=COMMAND_SOCK_ADD, help='command_sock_add')
    args = parser.parse_args()
    start_host(args.command, args.host, args.port, args.command_sock_add)
    start_host(' '.join(sys.argv[1:]))

