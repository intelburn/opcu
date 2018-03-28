import os
import socket
import sys

try:
    os.unlink("/tmp/flask4")
except OSError:
    if os.path.exists("/tmp/flask4"):
        raise

print("Opening socket...")
com = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
com.bind("/tmp/flask4")

com.listen(1)
while True:
    # Wait for a connection
    connection, client_address = com.accept()
    try:
        # Receive the data in small chunks and retransmit it
        while True:
            data = connection.recv(16)
            print('received {!r}'.format(data))
            if data:
                print('sending data back to the client')
            else:
                break
    finally:
        # Clean up the connection
        connection.close()
