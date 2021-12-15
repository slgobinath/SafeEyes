# Safe Eyes is a utility to remind you to take break frequently
# to protect your eyes from eye strain.

# Copyright (C) 2021  Gobinath

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
from threading import Timer

from safeeyes.context import Context
from safeeyes.plugin_utils.manager import PluginManager
from safeeyes.util.locale import get_text as _


class Arguments:

    def __init__(self, context: Context, plugin_manager: PluginManager, args):
        self.__context: Context = context
        self.__args = args
        self.__plugin_manager: PluginManager = plugin_manager

    def execute_on_local_instance(self) -> None:
        """
        Evaluate the arguments and execute the operations.
        """
        Timer(1.0, lambda: self.__execute_on_local_instance()).start()

    def __execute_on_local_instance(self) -> None:
        if self.__args.about:
            self.__context.window_api.show_about()
        elif self.__args.disable:
            self.__context.core_api.stop()
        elif self.__args.enable:
            self.__context.core_api.start()
        elif self.__args.settings:
            self.__context.window_api.show_settings()
        elif self.__args.take_break:
            self.__context.break_api.take_break()

    def execute_on_remote_instance(self) -> None:
        rpc_plugin = self.__plugin_manager.get_plugin("rpcserver")
        if rpc_plugin:
            if self.__args.about:
                rpc_plugin.execute_if_exists("show_about")
            elif self.__args.disable:
                rpc_plugin.execute_if_exists("disable_safe_eyes")
            elif self.__args.enable:
                rpc_plugin.execute_if_exists("enable_safe_eyes")
            elif self.__args.settings:
                rpc_plugin.execute_if_exists("show_settings")
            elif self.__args.take_break:
                rpc_plugin.execute_if_exists("take_break")
            elif self.__args.status:
                print(rpc_plugin.execute_if_exists("get_status"))
            elif self.__args.quit:
                rpc_plugin.execute_if_exists("quit_safe_eyes")
            else:
                # Default behavior is opening settings
                rpc_plugin.execute_if_exists("show_settings")
        else:
            print(_("RPC Server plugin is disabled. Without this plugin, command line arguments cannot be processed"))
