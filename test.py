import random
import socket
import sys

port = int(sys.argv[2])
print("port:",port)

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('', port))

print("The server is ready to receive")

while True:
    rand = random.randint(0, 10)
    message, address = server_socket.recvfrom(1024)
    message = message.upper()
    if rand >= 4:
        server_socket.sendto(message, address)