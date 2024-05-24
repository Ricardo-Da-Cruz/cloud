import json
import socket
import threading
import time

import a
import gcp_commands


def start_top_server(host, count, port=5000):
    server_scores = a.get_previous_server_scores()
    new_server_scores = {}

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server_address = (host, port)
    print(f'Starting TCP server on {host} port {port}')
    sock.bind(server_address)

    sock.listen(1)

    for i in range(count):
        print('Waiting for a connection')
        connection, client_address = sock.accept()
        try:
            print(f'Connection from {client_address}')

            while True:
                data = connection.recv(16)
                print(f'Received: {data.decode()}')
                if data:
                    jdata = json.loads(data)

                    for key in server_scores.keys:
                        new_server_scores[key] += jdata[key]

                    connection.sendall("received".encode())
                else:
                    print('No more data from', client_address)
                    break

        finally:
            connection.close()


if __name__ == "__main__":
    host = '0.0.0.0'

    gcp_commands.get_vm_ips()
    ips_to_connect = ['192.168.1.10', '192.168.1.20', '192.168.1.30']

    server_thread = threading.Thread(target=start_top_server, args=(host, len(ips_to_connect)))
    server_thread.start()

    # Give the server a moment to start
    time.sleep(2)

    send_requests_to_ips(ips_to_connect, "send_server_scores_in_region")
