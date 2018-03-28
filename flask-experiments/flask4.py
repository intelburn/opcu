from flask import Flask, render_template, request
import os
import socket

com = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
com.connect("/tmp/flask4")

app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])
def dropdown():
    colours = ['Red', 'Blue', 'Black', 'Orange', '']
    if request.method == 'POST' :
        colour1 = request.form.getlist('colour1')
        print(colour1)
        com.sendall(colour1[0].encode())
        colour2 = request.form.getlist('colour2')
        print(colour2)
        com.sendall(colour2[0].encode())
    return render_template('flask4.html', colours=colours)

if __name__ == "__main__":
    app.run()
