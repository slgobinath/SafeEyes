#!/usr/bin/env python
# Safe Eyes is a utility to remind you to take break frequently
# to protect your eyes from eye strain.

# Copyright (C) 2017  Gobinath

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
RPC server and client implementation.
"""

import logging
from threading import Thread
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.client import ServerProxy


class RPCServer:
    """
    An aynchronous RPC server.
    """
    def __init__(self, port, context):
        self.__running = False
        logging.info('Setting up an RPC server on port %d', port)
        self.__server = SimpleXMLRPCServer(("localhost", port), logRequests=False, allow_none=True)
        self.__server.register_function(context['api']['show_settings'], 'show_settings')
        self.__server.register_function(context['api']['show_about'], 'show_about')
        self.__server.register_function(context['api']['enable_safeeyes'], 'enable_safeeyes')
        self.__server.register_function(context['api']['disable_safeeyes'], 'disable_safeeyes')
        self.__server.register_function(context['api']['take_break'], 'take_break')
        self.__server.register_function(context['api']['status'], 'status')
        self.__server.register_function(context['api']['quit'], 'quit')

    def start(self):
        """
        Start the RPC server.
        """
        if not self.__running:
            self.__running = True
            logging.info('Start the RPC server')
            server_thread = Thread(target=self.__server.serve_forever)
            server_thread.start()

    def stop(self):
        """
        Stop the server.
        """
        if self.__running:
            logging.info('Stop the RPC server')
            self.__running = False
            self.__server.shutdown()


class RPCClient:
    """
    An RPC client to communicate with the RPC server.
    """
    def __init__(self, port):
        self.port = port
        self.proxy = ServerProxy('http://localhost:%d/' % self.port, allow_none=True)

    def show_settings(self):
        """
        Show the settings dialog.
        """
        self.proxy.show_settings()

    def show_about(self):
        """
        Show the about dialog.
        """
        self.proxy.show_about()

    def enable_safeeyes(self):
        """
        Enable Safe Eyes.
        """
        self.proxy.enable_safeeyes()

    def disable_safeeyes(self):
        """
        Disable Safe Eyes.
        """
        self.proxy.disable_safeeyes(None)

    def take_break(self):
        """
        Take a break now.
        """
        self.proxy.take_break()

    def status(self):
        """
        Return the status of Safe Eyes
        """
        return self.proxy.status()

    def quit(self):
        """
        Quit Safe Eyes.
        """
        self.proxy.quit()
