#!/usr/bin/env python3

'''OPC Client that can switch programs on the fly.

Usage:
  multi_opc [options] [<config-file>]
  multi_opc (-h | --help)
  multi_opc --version

Options:
  -d --debug            Log debugging information.
  -h --help             Show this help.
  --version             Show version.

'''

import os
import sys
import signal
import threading
import re
import json
import time
import copy
import logging
from importlib import import_module
from configparser import ConfigParser
from docopt import docopt
import yaml
from watchdog.events import FileSystemEventHandler, LoggingEventHandler
from opc import opc
from opc import color_utils
import subprocess
import socket

DEFAULT_CONFIG_FILENAME = 'opc.yml'
LOGGER_FORMAT = '%(asctime)-15s %(levelname)s %(name)s - %(message)s'
DEFAULT_LOGGER_LEVEL = logging.INFO

logger = None
running = True
config_changed = False


class ServerGroup(object):
    def __init__(self, name, hosts, layout):
        self.name = name
        self.hosts = hosts # {'name': {ip:, port:, start:, end:}}
        self.clients = []  # [(client,start_pixel,end_pixel)...]
        self.layout = layout
        self.source = None
        self.pixels = None      # pixels about to be sent
        self.prev_pixels = None # last pixels sent
        self.same_pixels_sent_count = 0

    def set_source_class(self, clazz, source_args):
        if source_args == None:
            source_args = dict()
        self.source = clazz(self.layout, **source_args)

    def connect(self):
        logger.info('Setting up %s hosts' % self.name)
        for k,v in self.hosts.items():
            gamma = v.get('gamma')
            client = opc.Client(host=v['ip'], port=v['port'], gamma=gamma, verbose=False, udp=v['udp'])
            if client.can_connect():
                logger.info('\tsending to %s:\t(%s:%d)\t[%d-%d] %d' % (k, v['ip'], v['port'], v['start'], v['end'], v['end']-v['start']+1))
                self.clients.append([client, v['start'], v['end']])
            else:
                # can't connect, but keep running in case the server appears later
                logger.warn('\tWARNING: could not connect to %s:%s' % (v['ip'],v['port']))

    def connected(self):
        return self.client != None

    def calculate_pixels(self, t):
        if not self.source or not self.clients:
            return
        self.pixels = self.source.all_pixel_colors(t)

    def send_pixels(self):
        if not self.pixels:
            return
        if self.pixels == self.prev_pixels:
            self.same_pixels_sent_count += 1
        else:
            self.same_pixels_sent_count = 0
        if self.same_pixels_sent_count > 1:
            return

        for client, start_pixel, end_pixel in self.clients:
            if start_pixel == end_pixel == 0:
                # Client gets all pixels
                client.put_pixels(self.pixels, channel=0)
            else:
                # Client gets a subset of pixels
                client.put_pixels(self.pixels[start_pixel:end_pixel+1], channel=0)
        self.prev_pixels = copy.copy(self.pixels)


class MultiClient(threading.Thread):
    def __init__(self, config):
        super().__init__(daemon=True)
        self.__running = True
        self.__config = config
        self.__layouts_dir = config['layouts-directory']
        self.__plugins_dir = config['plugins-directory']
        self.__fps = config['fps']
        self.__plugins = self.__load_plugins()
        self.__server_groups = self.__load_servers()

    def __load_layout(self, layout):
        coordinates = []
        for item in json.load(open(layout)):
            if 'point' in item:
                coordinates.append(tuple(item['point']))
        return coordinates

    def __load_plugins(self):
        logger.info('Loading plugins')
        if not self.__plugins_dir in sys.path:
            sys.path.insert(0, self.__plugins_dir)
        py_re = re.compile('^(?!__).*\.py')
        pluginfiles = filter(py_re.search, os.listdir(self.__plugins_dir))
        form_module = lambda fp: os.path.splitext(fp)[0]
        plugins_map = map(form_module, pluginfiles)
        # import parent module / namespace
        modules = dict() # name:module
        for plugin in plugins_map:
            mod = import_module(plugin)
            modules[plugin] = mod
        return modules

    def __load_servers(self):
        logger.debug('Entering loading servers')
        server_groups = dict()
        server_group_names = self.__config['server-groups'].keys()
        logger.debug('Servers in config: %s' % (', '.join(server_group_names)))
        for server_key in server_group_names:
            server_config = self.__config['server-groups'][server_key]
            if not server_config['enable']:
                continue
            layout_name = server_config['layout']
            layout = self.__load_layout(os.path.join(self.__layouts_dir, layout_name + '.json'))
            group = ServerGroup(server_key, server_config['hosts'], layout)
            server_groups[server_key] = group
        logger.debug('Loaded %d servers' % (len(server_groups)))
        return server_groups

    def set_group_class(self, group_name, clazz, source_args):
        self.__server_groups[group_name].set_source_class(clazz, source_args)

    def get_group_names(self):
        return self.__server_groups.keys()

    def __connect_clients(self):
        for group in self.__server_groups.values():
            group.connect()

    def stop(self):
        self.__running = False

    def run(self):
        self.__connect_clients()
        start_time = time.time()
        while self.__running:
            t = time.time() - start_time
            for group in self.__server_groups.values():
                group.calculate_pixels(t)
            for group in self.__server_groups.values():
                group.send_pixels()
            next_frame = start_time + t + (1.0 / self.__fps)
            sleep_time = next_frame - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                # warn if it was more than a frame?
                if -sleep_time > (1.0 / self.__fps):
                    logger.warn('Too much work.  Can\'t run at request FPS. Over by %d frames ' % (-sleep_time / (1.0 / self.__fps)))

def load_scene(scene, multi_client):
    if not scene:
        logger.warn('Attempted to load an undefined scene')
        return
    for scene_part in scene:
        group_names = scene_part.get('groups')
        source_name = scene_part['source']
        source_args = scene_part.get('args')
        source_class = color_utils.registered_sources[source_name]
        if group_names == None:
            group_names = multi_client.get_group_names()
        for name in group_names:
            multi_client.set_group_class(name, source_class, source_args)


def setup_logging(debug=False):
    if debug:
        level = logging.DEBUG
    else:
        level = DEFAULT_LOGGER_LEVEL
    LOGGER_FORMAT = '%(asctime)-15s %(levelname)s %(name)s - %(message)s'
    formatter = logging.Formatter(LOGGER_FORMAT)
    formatter.converter = time.gmtime # log times in UTC
    root = logging.getLogger()
    root.setLevel(level)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)
    root.debug('Debug logging enabled')
    return root

def shutdown_handler(signum, frame):
    logger.warn('Signal handler called with signal %d' % signum)
    global running
    running = False


def load_config(filename):
    logger.info('Reading configuration from %s' % filename)
    stream = open(filename, 'r')
    y = yaml.load(stream)
    return y

def main():
    global logger, running
    args = docopt(__doc__, version='v0.0.1')
    logger = setup_logging(args['--debug'])
    signal.signal(signal.SIGINT | signal.SIGTERM, shutdown_handler)
    #Get Filename for use later
    yml_filename = os.environ.get('OPC_YML','./opc.yml')
   logger.info('Registered pixel sources: ' + ', '.join(color_utils.registered_sources.keys()))
    logger.info('Creating Socket for Flask')
    # I am using a Unix socket to communicate with the Flask process that is running the web interface.
    try:
        os.unlink("/tmp/cal_lights")
    except OSError:
        if os.path.exists("/tmp/cal_lights"):
            raise
    logger.info("Opening socket...")
    com = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    com.bind("/tmp/cal_lights")
    # Start Listening for communication from the Flask script
    com.listen()
    #Start process for Flask frontend
    #potential issue: use of hardcoded path for the location of the frontend
    frontend = subprocess.Popen(['python3', '/usr/src/opc/opc/webserver.py'])
    #load the YAML config into a dict
    config = load_config(yml_filename)
    #Load the config into the multi_client handler
    multi_client = MultiClient(config)
    #Start the multi_client handler
    multi_client.start()
    #Set initial scenes
    scene='startup'
    #Send initial scene to lights
    load_scene(config['scenes'][scene], multi_client)
    logger.info("Entering loop")
    # Wait for a connection from the frontend
    connection, client_address = com.accept()
    logger.info("Frontend connected")
    #main loop for actually running the lights
    while running:
        #Try to get data from the Flask Frontend
        try:
            #Received data
            data = connection.recv(32)
            #remove the b from the front of the data
            data = data.decode()
            #Log some stuff
            logger.info("Scene Requested: {!r}".format(data))
            logger.info("running= {!r}".format(running))
            #Check if the data sent from Flask is actually differnet from teh current scene
            if data!=scene:
                #Set the scene variable to the data sent from Flask
                scene=str(data)
                #Get Lastest version of the config file
                config = load_config(yml_filename)
                #Try to catch invalid scenes
                try:
                    #Send the scene to the lights
                    load_scene(config['scenes'][scene], multi_client)
                #If a scene is invalid send a warning to the logger, then do nothing
                except KeyError:
                    logger.warn("Invalid Scene")
        #Check for ^+C
        except KeyboardInterrupt:
            logger.warn('Shutting down due to keyboard interrupt.')
            #Send the shutdown scene to the lights
            load_scene(config['scenes']['shutdown'], multi_client)
            #Wait for the lights to load the shutdown scene
            time.sleep(0.5)
            #Close the connection to Flask
            connection.close()
            #Stop both the main loop and the connection loop
            running = False
        #Sleep for inactivity
        finally:
            time.sleep(1)
    logger.debug('Stopping multi client thread')
    #Stop the multi_client handler
    multi_client.stop()
    frontend.terminate()
    logger.warn('Exiting')
    sys.exit(0)

if __name__=='__main__':
    main()
