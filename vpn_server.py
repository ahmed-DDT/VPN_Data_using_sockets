from concurrent.futures import ThreadPoolExecutor
import argparse
import json
import netifaces
import os
import random
import socket
import subprocess
import sys
import threading
import time


def load_config():
    return {
        "host": os.getenv("SERVER_HOST", "0.0.0.0"),
        "port": int(os.getenv("SERVER_PORT", 445)),
        "command_sock_add": os.getenv("COMMAND_SOCK_ADD", "/tmp/server_socket")
    }

data_store = {}
lock = threading.Lock()

def handle_client(conn, addr, SOCKET_TIMEOUT=60):
    unique_id = str(random.randint(1000000000, 9999999999))
    conn.settimeout(SOCKET_TIMEOUT)
    try:
        while True:
            try:
                data = conn.recv(2048)
                if not data:
                    break
                user_data = json.loads(data.decode())
                # print("Data received from client.")
                with lock:
                    data_store[unique_id] = user_data
            except (ConnectionResetError, json.JSONDecodeError, socket.timeout) as exp:
                print(f"Error: {exp}")
                break
    finally:
        with lock:
            if unique_id in data_store:
                del data_store[unique_id]
        conn.close()

def start_server(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen()
        print(f"Server listening on port {port}")
        with ThreadPoolExecutor(max_workers=2000) as executor:
            while True:
                try:
                    conn, addr = s.accept()
                    # print(f"Connection established with {addr}")
                    executor.submit(handle_client, conn, addr)
                except OSError as e:
                    if e.errno == 24:  # Too many open files
                        print("Too many open files. Try adjusting ulimit or reducing connections.")
                    else:
                        raise

def command_server(COMMAND_SOCK_ADD):
    if os.path.exists(COMMAND_SOCK_ADD):
        os.remove(COMMAND_SOCK_ADD)
    
    server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server_socket.bind(COMMAND_SOCK_ADD)
    server_socket.listen()

    print("Command server listening...")
    while True:
        try:
            conn, _ = server_socket.accept()
            data = conn.recv(1024).decode()
            if data.startswith("fetch"):
                _, user_id = data.split()
                with lock:
                    if user_id == "all":
                        response = json.dumps(data_store, indent=4)
                    else:
                        response = json.dumps(data_store.get(user_id, "No data found for the specified key"), indent=4)
                conn.send(response.encode())
            elif data == "count":
                with lock:
                    response = json.dumps({"total_users": len(data_store)}, indent=4)
                conn.send(response.encode())
            conn.close()
        except OSError as e:
            if e.errno == 24:  # Too many open files
                print("Too many open files in command server. Try adjusting ulimit or reducing connections.")
            else:
                raise

def start_socket_server(HOST, PORT, COMMAND_SOCK_ADD="/tmp/server_socket"):
    server_thread = threading.Thread(target=start_server, args=(HOST,PORT))
    server_thread.daemon = True
    server_thread.start()

    command_thread = threading.Thread(target=command_server, args=(COMMAND_SOCK_ADD,))
    command_thread.daemon = True
    command_thread.start()

    # Keep the main thread alive
    return command_thread    


config = load_config()
SERVER = config['host']
PORT = config['port']
COMMAND_SOCK_ADD = config['command_sock_add']

def command_client(command: str, COMMAND_SOCK_ADD="/tmp/server_socket"):
    client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client_socket.connect(COMMAND_SOCK_ADD)
    client_socket.send(command.encode())
    response = client_socket.recv(1048576)
    client_socket.close()
    return response.decode()



def get_output(command):
    try:
        return subprocess.check_output(command, shell=True).decode().strip()
    except subprocess.CalledProcessError as e:
        return "unknown"

def fetch_service_status(service_name):
    return get_output(f"systemctl is-active {service_name}")

def get_ip_addresses():
    addresses = {}
    for interface in netifaces.interfaces():
        iface_details = netifaces.ifaddresses(interface)
        ipv4 = iface_details.get(netifaces.AF_INET, [{'addr': None}])[0]['addr']
        ipv6 = iface_details.get(netifaces.AF_INET6, [{'addr': None}])[0]['addr']
        addresses[interface] = {'IPv4': ipv4, 'IPv6': ipv6}
    return addresses

def fetch_system_info():
    return {
        'key': 'vpn_server_1',
        'status': {
            'apache': fetch_service_status("apache2"),
            'ocserv.service': fetch_service_status("ocserv"),
            'openvpn.service': fetch_service_status("openvpn@server")
        },
        'cpu_usage': float(get_output("top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'") or 0),
        'ram_usage': float(get_output("free | grep Mem | awk '{print $3/$2 * 100.0}'") or 0),
        'server_load': get_output("uptime | awk -F 'load average:' '{print $2}'").strip(),
        'uptime': int(get_output("awk '{print int($1)}' /proc/uptime") or 0),
        'online_users': int(get_output("who | wc -l") or 0),
        'ports': get_output("netstat -tuln | awk '{print $4}' | grep ':' | cut -d: -f2").split(),
        'interfaces': get_ip_addresses()
    }

def get_data(d_type, COMMAND_SOCK_ADD=None):
    try:
        if d_type == 'ip':
            return get_output("curl -s ifconfig.me")
        elif d_type == 'user_data':
            return command_client("fetch all", COMMAND_SOCK_ADD)
        elif d_type == 'server_data':
            return fetch_system_info()
    except Exception:
        return None

def get_socket(server, port):
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((server, port))
            return s
        except Exception as e:
            print(f"Connection failed: {str(e)}, retrying in 5 seconds...")
            time.sleep(5)

def send_data(s, reconnect_event: threading.Event, user_data_event: threading.Event, server_data_event: threading.Event):
    while not reconnect_event.is_set():
        try:
            combined_data = {}
            user_data = get_data('user_data', COMMAND_SOCK_ADD) if user_data_event.is_set() else None
            server_data = get_data('server_data') if server_data_event.is_set() else None
            ip = get_data('ip')
            combined_data = {"user_data": user_data, "server_data": server_data, "ip": ip}
            s.sendall(json.dumps(combined_data).encode())
            print("Sent data to server")
            time.sleep(2)
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            print(f"Connection failed: {str(e)}, attempting to reconnect...")
            reconnect_event.set()
            break

def listen_for_server(s, reconnect_event, user_data_event, server_data_event):
    while not reconnect_event.is_set():
        try:
            response = s.recv(1024)
            if response:
                decoded = response.decode()
                print("Received from server:", decoded)
                if decoded == "close":
                    reconnect_event.set()
                    break
                elif decoded.startswith("stop"):
                    if decoded.startswith("stop user_data"):
                        user_data_event.clear()
                    elif decoded.startswith("stop server_data"):
                        server_data_event.clear()
                elif decoded.startswith("start"):
                    if decoded.startswith("start user_data"):
                        user_data_event.set()
                    elif decoded.startswith("start server_data"):
                        server_data_event.set()
        except Exception as e:
            print(f"Error receiving data: {str(e)}")
            reconnect_event.set()
            break

def watch_socket_file(server, port, COMMAND_SOCK_ADD):
    user_data_event = threading.Event()
    server_data_event = threading.Event()
    while True:
        try:
            print("Connected to server")
            reconnect_event = threading.Event()

            s = get_socket(server, port)
            send_thread = threading.Thread(target=send_data, args=(s, reconnect_event, user_data_event, server_data_event))
            send_thread.daemon = True
            send_thread.start()

            listen_thread = threading.Thread(target=listen_for_server, args=(s, reconnect_event, user_data_event, server_data_event))
            listen_thread.daemon = True
            listen_thread.start()

            send_thread.join()
            listen_thread.join()
            if reconnect_event.is_set():
                print("Re-establishing connection...")
        except Exception as e:
            print(f"Connection failed: {str(e)}, retrying in 5 seconds...")
            time.sleep(5)    



config = load_config()
HOST = config['host']
PORT = config['port']
COMMAND_SOCK_ADD = config['command_sock_add']
SERVER = '127.0.0.1'

SOCKET_TIMEOUT = 60
terminate_event = threading.Event()

def start_vpn(command:str="start", server_ip=SERVER, server_port=PORT+1, hosting_port=PORT, command_sock_add=COMMAND_SOCK_ADD):
    try:
        print("Starting the server...")
        cmd = command.split()
        try:
            if cmd[0] == "start":
                command_thread = start_socket_server(HOST, hosting_port, command_sock_add)
                def watch_socket_with_retries(server_ip, server_port, command_sock_add):
                    while not terminate_event.is_set():
                        try:
                            watch_socket_file(server_ip, server_port, command_sock_add)
                        except Exception as e:
                            print(f"Error encountered: {e}. Retrying in 5 seconds...")
                            time.sleep(5)

                watch_thread = threading.Thread(target=watch_socket_with_retries, args=(server_ip, server_port, command_sock_add))
                watch_thread.daemon = True
                watch_thread.start()

                command_thread.join()
            elif cmd[0] == "fetch":
                print(command_client(f"fetch {cmd[1]}"))
            elif cmd[0] == "count":
                print(command_client("count"))
            else:
                print("Invalid command")
        except IndexError:
            print("Invalid command")
    except KeyboardInterrupt:
        print("Exiting...")
        terminate_event.set()
        sys.exit(0)

def main():

    parser = argparse.ArgumentParser(description="Start the VPN server with configurable parameters.")
    parser.add_argument('--command', default='start', help='Command to execute, default is "start".')
    parser.add_argument('--server_ip', default=SERVER, help='IP address of the server, default is 127.0.0.1.')
    parser.add_argument('--server_port', type=int, default=PORT+1, help='Port number for the server, default is 445.')
    parser.add_argument('--hosting_port', type=int, default=PORT, help='Hosting port number, default is 445.')
    parser.add_argument('--command_sock_add', default=COMMAND_SOCK_ADD, help='Command socket address, default is "/tmp/server_socket".')

    args = parser.parse_args()

    print(f"Host {HOST}:{args.hosting_port}, Server {args.server_ip}:{args.server_port}")
    start_vpn(args.command, args.server_ip, args.server_port, args.hosting_port, args.command_sock_add)

if __name__ == "__main__":
    main()
# start_vpn(command='start', server_ip='191.10.8.1', server_port=446, hosting_port=445)

