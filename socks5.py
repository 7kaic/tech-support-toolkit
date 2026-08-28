import socket
import threading

PROXY_USER = "admin"
PROXY_PASS = "admin"

def forward(source, destination):
    try:
        while data := source.recv(4096):
            destination.sendall(data)
    except:
        pass
    finally:
        source.close()
        destination.close() 
        
def send_reply(client, rep_code):
    try:
        client.sendall(b'\x05' + bytes([rep_code]) + b'\x00\x01\x00\x00\x00\x00\x00\x00')
    except Exception:
        pass

def handle_client(client):
    try:
        _, nmethods = client.recv(2)
        methods = client.recv(nmethods)

        if 2 not in methods:
            client.sendall(b'\x05\xFF')
            return client.close()

        client.sendall(b'\x05\x02')

        if client.recv(1)[0] != 1:
            return client.close()

        username = client.recv(client.recv(1)[0]).decode()
        password = client.recv(client.recv(1)[0]).decode()

        if username == PROXY_USER and password == PROXY_PASS:
            client.sendall(b'\x01\x00')
        else:
            client.sendall(b'\x01\x01')
            return client.close()

        _, cmd, _, address_type = client.recv(4)

        if cmd != 1:
            send_reply(client, 7)
            return client.close()
            
        if address_type == 1:   # ipv4
            address = socket.inet_ntoa(client.recv(4))
        elif address_type == 3: # dominio
            address = client.recv(client.recv(1)[0]).decode()
        elif address_type == 4: # ipv6
            address = socket.inet_ntop(socket.AF_INET6, client.recv(16))
        else:
            send_reply(client, 8)
            return client.close()
        
        port = int.from_bytes(client.recv(2), 'big')

        try:
            remote = socket.create_connection((address, port), timeout=10)
        except ConnectionRefusedError:
            send_reply(client, 5)
            return client.close()
        except socket.timeout:
            send_reply(client, 4)
            return client.close()
        except Exception:
            send_reply(client, 1)
            return client.close()

        send_reply(client, 0)

        threading.Thread(target=forward, args=(client, remote), daemon=True).start()
        threading.Thread(target=forward, args=(remote, client), daemon=True).start()

    except Exception:
        client.close()

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('0.0.0.0', 1080))
server.listen()
print("Proxy SOCKS5 online")

while True:
    client_socket, _ = server.accept()
    threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()
