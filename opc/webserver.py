#!/usr/bin/python3
from flask import Flask, render_template, request
import os
import socket
import yaml
import logging
#The method for getting the list of scenes from the config file
def getScenes(filename):
    #Get config file as stream of data
    stream = open(filename, 'r')
    #Control Scenes are scenes used for the back end operation of the lights but should not be visible on the web page
    control_scenes = ['startup', 'shutdown', 'test']
    #Convert stream from file into python dict
    raw = yaml.load(stream)
    #Set up empty dict for scenes to end up
    scenes=[" "]
    #loop through the keys from the screnes as described in YAML data
    for canidate in raw['scenes'].keys():
        #Check to insure scene is not a control scene
        if canidate not in control_scenes:
            #add scen to dict of scenes
            scenes.append(canidate)
    #return scenes dict
    return scenes

#Declare socket for communicating with multi_opc
com = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
#connect to socket from multi_opc
com.connect("/tmp/cal_lights")

#define the web app for Flask to server
app = Flask(__name__)

#Define the path and HTTP methods from the brower for Flask
@app.route('/', methods=['POST', 'GET'])
#The method Flask uses to serve the page
def select_scenes():
    #Get the scenes for use with the dropdown menu from the config file
    scenes = getScenes('/home/opc/opc.yml')
    #Check for the POST HTTP method
    if request.method == 'POST' :
        #Get scene that was submitted by the user
        requested_scene = request.form.getlist('requested_scene')
        #Debug print of the requested scene
        print(requested_scene)
        #Send the requested scene to multi_opc
        com.sendall(requested_scene[0].encode())
    #Render the page
    return render_template('basic.html', scenes=scenes)

#Check to see if this is being called by another script or interpreter
if __name__ == "__main__":
    #Run Flask on the wildcard IP address
    app.run(host='0.0.0.0')
