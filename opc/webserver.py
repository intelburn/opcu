#!/usr/bin/python3
from flask import Flask, render_template, request
import os
import socket
import yaml
import logging
def getColours(filename):
#    logger.info('Reading configuration from %s' % filename)
    stream = open(filename, 'r')
    y = yaml.load(stream)
    return y['scenes'].keys()

com = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
com.connect("/tmp/cal_lights")

app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])
def dropdown():
#    colours = ['water', 'sunset', 'test']
    colours = getColours('/home/opc/opc.yml')
    if request.method == 'POST' :
        colour1 = request.form.getlist('colour1')
        print(colour1)
        com.sendall(colour1[0].encode())
    return render_template('basic.html', colours=colours)

if __name__ == "__main__":
    app.run(host='0.0.0.0')
