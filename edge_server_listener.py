import socket

import a


def get_response():
    ips = a.get_ips_from_nginx()

    coords = []

    for ip in ips:
        coords.append(a.ip_to_geolocation(ip))

    print(coords)

    a.assign_server_scores(coords,)


def start_tcp_server(host, port):
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket to the address and port
    server_address = (host, port)
    print(f'Starting TCP server on {host} port {port}')
    sock.bind(server_address)

    # Listen for incoming connections
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

                    connection.sendall(get_response().encode())
                else:
                    print('No more data from', client_address)
                    break

        finally:
            connection.close()

if __name__ == "__main__":
    host = '0.0.0.0'  # Listen on all network interfaces
    port = 5000       # The port to listen on

    start_tcp_server(host, port)