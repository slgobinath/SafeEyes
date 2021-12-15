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

import logging
import socket
import sys
from contextlib import closing
from typing import Optional
from xmlrpc.client import ServerProxy
from xmlrpc.server import SimpleXMLRPCServer

from safeeyes.context import Context
from safeeyes.thread import worker


class RPCClient:
    """
    An RPC client to communicate with the RPC server.
    """

    def __init__(self, port: int):
        self.__port: int = port
        self.proxy = ServerProxy("http://localhost:%d/" % self.__port, allow_none=True)

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

    def enable_safe_eyes(self):
        """
        Enable Safe Eyes.
        """
        self.proxy.enable_safe_eyes()

    def disable_safe_eyes(self):
        """
        Disable Safe Eyes.
        """
        self.proxy.disable_safe_eyes()

    def take_break(self):
        """
        Take a break now.
        """
        self.proxy.take_break()

    def get_status(self):
        """
        Return the status of Safe Eyes
        """
        return self.proxy.get_status()

    def get_user(self):
        """
        Return the get_user of Safe Eyes
        """
        return self.proxy.get_user()

    def quit_safe_eyes(self):
        """
        Quit Safe Eyes.
        """
        self.proxy.quit_safe_eyes()


class RPCServer:
    """
    An asynchronous RPC server.
    """

    def __init__(self, context: Context, config: dict):
        self.__running: bool = True
        self.__context: Context = context
        self.__port: Optional[int] = RPCServer.get_available_port(context.env.user,
                                                                  int(config.get("port", 7200)),
                                                                  int(config.get("max_attempts", 5)))
        self.__server: Optional[SimpleXMLRPCServer] = None
        if self.__port is None:
            logging.debug("RPC Server: Cannot create an RPC server")
        else:
            logging.debug("Init the rpc server to listen on port %d", self.__port)
            self.__server = SimpleXMLRPCServer(("localhost", self.__port), logRequests=False, allow_none=True)
            self.__server.timeout = 1.0
            self.__server.register_function(self.show_settings)
            self.__server.register_function(self.show_about)
            self.__server.register_function(self.enable_safe_eyes)
            self.__server.register_function(self.disable_safe_eyes)
            self.__server.register_function(self.take_break)
            self.__server.register_function(self.get_status)
            self.__server.register_function(self.get_user)
            self.__server.register_function(self.quit_safe_eyes)

    def show_settings(self) -> None:
        self.__context.window_api.show_settings()

    def show_about(self) -> None:
        self.__context.window_api.show_about()

    def enable_safe_eyes(self) -> None:
        self.__context.core_api.start()

    def disable_safe_eyes(self) -> None:
        self.__context.core_api.stop()

    def quit_safe_eyes(self) -> None:
        self.__context.core_api.quit()

    def take_break(self) -> None:
        self.__context.break_api.take_break()

    def get_status(self) -> str:
        return self.__context.core_api.get_status()

    def get_user(self) -> str:
        return self.__context.env.user

    @worker
    def start(self):
        """
        Start the RPC server.
        """
        if self.__port is not None:
            try:
                logging.debug("RPC Server: starting the server listening on port %d", self.__port)
                while self.__server is not None and self.__running:
                    self.__server.handle_request()
                logging.debug("RPC Server: stopped the server successfully")
            finally:
                self.__running = True
                # Make sure the worker thread is terminated
                sys.exit(0)

    def stop(self):
        """
        Stop the server.
        """
        if self.__server is not None and self.__running:
            logging.debug("RPC Server: stopping the server listening on port %d", self.__port)
            self.__running = False
            # Send a dummy request to make sure the worker thread is released from waiting for requests
            try:
                rpc_client = RPCClient(self.__port)
                rpc_client.get_status()
            except BaseException:
                pass
            # Close the server
            self.__server.server_close()

    @staticmethod
    def is_available(port: int) -> bool:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            return sock.connect_ex(("127.0.0.1", port)) != 0

    @staticmethod
    def get_available_port(user: str, port: int, max_attempts: int) -> Optional[int]:
        i = 0
        original_port = port
        while i < max_attempts:
            i += 1
            if RPCServer.is_available(port):
                return port
            else:
                rpc_client = RPCClient(port)
                try:
                    if user == rpc_client.get_user():
                        # Safe Eyes is running under the same user
                        logging.debug("RPC Server: Another instance of Safe Eyes is running under the same user %s",
                                      user)
                        return None
                except ConnectionError:
                    # Port is used by some other process
                    pass
                port += 1
        logging.error(
            "RPC Server: Failed to get a port between %d and %d. Change the port number of the RPC Server plugin.",
            original_port, port)
        return None

    @staticmethod
    def get_safe_eyes_port(user: str, port: int, max_attempts: int) -> Optional[int]:
        i = 0
        while i < max_attempts:
            i += 1
            rpc_client = RPCClient(port)
            try:
                if user == rpc_client.get_user():
                    # Safe Eyes is running under the same user
                    return port
            except ConnectionError:
                # Port is used by some other process
                pass
            port += 1
        return None


server: Optional[RPCServer] = None
client: Optional[RPCClient] = None


def init(ctx: Context, plugin_config: dict) -> None:
    """
    Create the server.
    """
    global server
    global client
    if server:
        server.stop()
    if ctx.env.found_another_safe_eyes:
        # Do not start the RPC server but create the client.
        port = int(plugin_config.get("port", 7200))
        max_attempts = int(plugin_config.get("max_attempts", 5))
        safe_eyes_port = RPCServer.get_safe_eyes_port(ctx.env.user, port, max_attempts)
        if safe_eyes_port:
            logging.debug("RPC Server: Found another Safe Eyes running at %d", safe_eyes_port)
            client = RPCClient(safe_eyes_port)
        else:
            client = None
        server = None
    else:
        server = RPCServer(ctx, plugin_config)
        server.start()
        client = None


def enable() -> None:
    if server:
        server.start()


def disable() -> None:
    if server:
        server.stop()


def on_exit() -> None:
    if server:
        server.stop()


def show_settings() -> None:
    """
    Show the settings dialog.
    """
    if client is None:
        return
    try:
        client.show_settings()
    except ConnectionError:
        logging.error("RPC Server: Failed to establish a connection with the existing RPC server")


def show_about() -> None:
    """
    Show the about dialog.
    """
    if client is None:
        return
    try:
        client.show_about()
    except ConnectionError:
        logging.error("RPC Server: Failed to establish a connection with the existing RPC server")


def enable_safe_eyes() -> None:
    """
    Enable Safe Eyes.
    """
    if client is None:
        return
    try:
        client.enable_safe_eyes()
    except ConnectionError:
        logging.error("RPC Server: Failed to establish a connection with the existing RPC server")


def disable_safe_eyes() -> None:
    """
    Disable Safe Eyes.
    """
    if client is None:
        return
    try:
        client.disable_safe_eyes()
    except ConnectionError:
        logging.error("RPC Server: Failed to establish a connection with the existing RPC server")


def take_break() -> None:
    """
    Take a break now.
    """
    if client is None:
        return
    try:
        client.take_break()
    except ConnectionError:
        logging.error("RPC Server: Failed to establish a connection with the existing RPC server")


def get_status() -> Optional[str]:
    """
    Return the status of Safe Eyes
    """
    if client is None:
        return None
    try:
        return client.get_status()
    except ConnectionError:
        logging.error("RPC Server: Failed to establish a connection with the existing RPC server")
        return None


def quit_safe_eyes() -> None:
    """
    Quit Safe Eyes.
    """
    if client is None:
        return
    try:
        client.quit_safe_eyes()
    except ConnectionError:
        logging.error("RPC Server: Failed to establish a connection with the existing RPC server")
