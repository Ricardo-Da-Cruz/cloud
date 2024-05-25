import json
import socket
from collections import Counter

import server_score_calculator
import gcp_commands
import concurrent.futures


def start_region_server(host, port=5000):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server_address = (host, port)
    print(f'Starting TCP server on {host} port {port}')
    sock.bind(server_address)

    sock.listen(1)

    while True:
        print('Waiting for a connection')
        connection, client_address = sock.accept()
        try:
            print(f'Connection from {client_address}')

            while True:
                data = connection.recv(16)
                print(f'Received: {data.decode()}')
                if data:
                    if data == "scores_in_region":
                        region = gcp_commands.get_gcp_region()

                        ips = gcp_commands.get_vm_ips(region)

                        connection.sendall(
                            json.dumps(get_server_scores_from_servers(ips, "send_server_scores",
                                                                      server_score_calculator.get_server_scores())).encode())

                    if data == "send_server_scores":
                        scores = server_score_calculator.get_server_scores()

                        connection.sendall(json.dumps(scores).encode())
                else:
                    print('No more data from', client_address)
                    break

        finally:
            connection.close()


def get_server_scores_from_servers(ips, message, servers):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = [executor.submit(send_requests_to_ip, ip, message, 5000) for ip in ips]

    for future in concurrent.futures.as_completed(results):
        servers = dict(Counter(servers) + Counter(future.result()))

    return servers


def send_requests_to_ip(ip, message, port=5000):
    try:
        print(f'Connecting to {ip}:{port}')
        with socket.create_connection((ip, port), timeout=10) as sock:
            print(f'Sending to {ip}: {message}')
            sock.sendall(message.encode())
            response = sock.recv(16)
            return json.loads(response.decode())
    except Exception as e:
        print(f'Failed to connect to {ip}: {e}')


if __name__ == "__main__":
    start_region_server("0.0.0.0")
