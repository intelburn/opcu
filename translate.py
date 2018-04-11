#This is a script that translates the UDP version of OpenPixelControll to the offical TCP Version.
#This is intended for use with the simulator provided with the official repo of OpenPixelControl.
#Run this on the same machine that is running the simulator. This does not take any argument and will run in the foreground. Start the simulator, the run this script
import socket
#Declare socket for receiving outside UDP Traffic
outside = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#Declare socket for TCP traffic to the internal simulator
inside = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#Bind to the outside address on 7890/UDP
outside.bind(("0.0.0.0", 7890))
#Connect to the simulator running on localhost port 7890/TCP
inside.connect(("127.0.0.1",7890))
#Loop forever
while True:
    #Receive data from outside
    data, addr = outside.recvfrom(65000)
    #Debug print
    print("received {1} bytes of data from {0}".format(addr, len(data)))
    #Send data to the internal simulator
    inside.send(data)
