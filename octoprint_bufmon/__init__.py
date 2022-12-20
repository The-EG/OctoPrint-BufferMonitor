# coding=utf-8
from __future__ import absolute_import

import re
import datetime
import octoprint.plugin

ADV_OK_PAT = re.compile(r"^ok\s+(N(?P<line>\d+)\s+)?P(?P<planner>\d+)\s+B(?P<block>\d+).*$")

class BufmonPlugin(
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.EventHandlerPlugin,
    octoprint.plugin.TemplatePlugin
):
    def __init__(self):
        self._in_print = False
        self._last_planner = None
        self._min_planner = None
        self._max_planner = None
        self._mean_planner = None
        self._ttl_planner = 0
        self._cnt_planner = 0
        self._last_block = None
        self._min_block = None
        self._max_block = None
        self._mean_block = None
        self._ttl_block = 0
        self._cnt_block = 0

        self._last_msg = None

    ##~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return {
            # put your plugin's default settings here
        }

    ##~~ AssetPlugin mixin

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return {
            "js": ["js/bufmon.js"],
            "css": ["css/bufmon.css"]
        }

    ##~~ GCode Recieve hook
    def parse_ok(self, comm, line, *args, **kwargs):
        if not self._in_print or not (len(line) >= 3 and line[:3] == 'ok '): return line

        m = ADV_OK_PAT.match(line)
        if m is None: return line

        p = int(m.group('planner'))
        b = int(m.group('block'))

        self._last_planner = p
        self._last_block = b

        if self._min_planner is None or self._min_planner > p: self._min_planner = p
        if self._max_planner is None or self._max_planner < p: self._max_planner = p
        self._ttl_planner += p
        self._cnt_planner += 1
        self._mean_planner = self._ttl_planner / self._cnt_planner
        
        if self._min_block is None or self._min_block > b: self._min_block = b
        if self._max_block is None or self._max_block < b: self._max_block = b
        self._ttl_block += b
        self._cnt_block += 1
        self._mean_block = self._ttl_block / self._cnt_block

        if self._last_msg is None or (datetime.datetime.now() - self._last_msg).total_seconds() > 1.0:
            self._last_msg = datetime.datetime.now()
            self._logger.debug('min_block {0}, max_block {1}, mean_block {2}, min_planner {3}, max_planner {4}, mean_planner {5}'.format(
                self._min_block, self._max_block, self._mean_block, self._min_planner, self._max_planner, self._mean_planner
            ))
            self.send_data_event()

        return line

    def send_data_event(self):
        event = octoprint.events.Events.PLUGIN_BUFMON_BUFFER_DATA
        self._event_bus.fire(event, payload={
            'last_planner': self._last_planner,
            'last_block': self._last_block,
            'min_planner': self._min_planner,
            'max_planner': self._max_planner,
            'mean_planner': self._mean_planner,
            'min_block': self._min_block,
            'max_block': self._max_block,
            'mean_block': self._mean_block
        })

    def on_event(self, event, payload):
        if event=='PrintStarted':
            self._logger.debug("Print started")
            self._in_print = True
            self._min_planner = None
            self._max_planner = None
            self._mean_planner = None
            self._ttl_planner = 0
            self._cnt_planner = 0
            self._min_block = None
            self._max_block = None
            self._mean_block = None
            self._ttl_block = 0
            self._cnt_block = 0
        elif event in ('PrintDone', 'PrintCancelled'):
            self._logger.debug("Print ended")
            self._in_print = False
        
    def register_custom_events(self, *args, **kwargs):
        return ['buffer_data']

    ##~~ Softwareupdate hook

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
        # for details.
        return {
            "bufmon": {
                "displayName": "Buffer Monitor",
                "displayVersion": self._plugin_version,

                # version check: github repository
                "type": "github_release",
                "user": "The-EG",
                "repo": "OctoPrint-BufferMonitor",
                "current": self._plugin_version,

                # update method: pip
                "pip": "https://github.com/The-EG/OctoPrint-BufferMonitor/archive/{target_version}.zip",

                "stable_branch": {
                    "name": "Stable",
                    "branch": "main",
                    "comitish": ["main"]
                },

                "prerelease_brnaches": [
                    {
                        "name": "Release Candidate",
                        "branch": "rc",
                        "comitish": ["rc", "main"]
                    }
                ]
            }
        }


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Buffer Monitor"


# Set the Python version your plugin is compatible with below. Recommended is Python 3 only for all new plugins.
# OctoPrint 1.4.0 - 1.7.x run under both Python 3 and the end-of-life Python 2.
# OctoPrint 1.8.0 onwards only supports Python 3.
__plugin_pythoncompat__ = ">=3,<4"  # Only Python 3

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = BufmonPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.comm.protocol.gcode.received": __plugin_implementation__.parse_ok,
        "octoprint.events.register_custom_events": __plugin_implementation__.register_custom_events
    }
