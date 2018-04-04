#This is a script that translates the UDP version of OpenPixelControll to the offical TCP Version.
#This is intended for use with the simulator provided with the official repo of OpenPixelControl.
#Run this on the same machine that is running the simulator. This does not take any argument and will run in the foreground. Start the simulator, the run this script
import socket
outside = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
inside = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
outside.bind(("0.0.0.0", 7890))
inside.connect(("127.0.0.1",7890))
while True:
    data, addr = outside.recvfrom(65000)
    print("received {1} bytes of data from {0}".format(addr, len(data)))
    inside.send(data)
