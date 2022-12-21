# coding=utf-8
from __future__ import absolute_import

import re
import datetime
import octoprint.plugin

ADV_OK_PAT = re.compile(r"^ok\s+(N(?P<line>\d+)\s+)?P(?P<planner>\d+)\s+B(?P<input>\d+).*$")

MOVEMENT_CMS = [
    'G0',
    'G1',
    'G2',
    'G3',
    'G5',
    'G6',
    'G10',
    'G11',
    'G80'
]

class BufmonPlugin(
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.EventHandlerPlugin,
    octoprint.plugin.TemplatePlugin
):
    def __init__(self):
        self._planner_size = 0
        self._input_size = 0
        self._detect_sizes = False

        self._in_print = False
        self._last_planner = None
        self._min_planner = None
        self._max_planner = None
        self._mean_planner = None
        self._ttl_planner = 0
        self._cnt_planner = 0
        self._last_input = None
        self._min_input = None
        self._max_input = None
        self._mean_input = None
        self._ttl_input = 0
        self._cnt_input = 0

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

    def on_gcode_sending(self, comm_instance, phase, cmd, cmd_type, gcode, subcode=None, tags=None, *args, **kwargs):
        if cmd=='M115':
            self._logger.info("Detecting buffer sizes...")
            self._detect_sizes = True

    ##~~ GCode Recieve hook
    def parse_ok(self, comm, line, *args, **kwargs):
        if not (len(line) >= 3 and line[:3] == 'ok '): return line
        if not self._detect_sizes and not self._in_print: return line

        m = ADV_OK_PAT.match(line)
        if m is None: return line

        p = int(m.group('planner'))
        b = int(m.group('input'))

        if self._detect_sizes:
            self._planner_size = p + 1
            self._logger.info(f"Detected planner buffer size: {self._planner_size}")
            self._input_size = b + 1
            self._logger.info(f"Detected input buffer size: {self._input_size}")
            self._detect_sizes = False
            return line

        self._last_planner = p
        self._last_input = b

        if self._min_planner is None or self._min_planner > p: self._min_planner = p
        if self._max_planner is None or self._max_planner < p: self._max_planner = p
        self._ttl_planner += p
        self._cnt_planner += 1
        self._mean_planner = self._ttl_planner / self._cnt_planner
        
        if self._min_input is None or self._min_input > b: self._min_input = b
        if self._max_input is None or self._max_input < b: self._max_input = b
        self._ttl_input += b
        self._cnt_input += 1
        self._mean_input = self._ttl_input / self._cnt_input

        if self._last_msg is None or (datetime.datetime.now() - self._last_msg).total_seconds() > 1.0:
            self._last_msg = datetime.datetime.now()
            self._logger.debug('min_input {0}, max_input {1}, mean_input {2}, min_planner {3}, max_planner {4}, mean_planner {5}'.format(
                self._min_input, self._max_input, self._mean_input, self._min_planner, self._max_planner, self._mean_planner
            ))
            self.send_data_event()

        return line

    def send_data_event(self):
        event = octoprint.events.Events.PLUGIN_BUFMON_BUFFER_DATA
        self._event_bus.fire(event, payload={
            'last_planner': self._last_planner,
            'last_input': self._last_input,
            'min_planner': self._min_planner,
            'max_planner': self._max_planner,
            'mean_planner': self._mean_planner,
            'min_input': self._min_input,
            'max_input': self._max_input,
            'mean_input': self._mean_input
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
            self._min_input = None
            self._max_input = None
            self._mean_input = None
            self._ttl_input = 0
            self._cnt_input = 0
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
        "octoprint.comm.protocol.gcode.sending": __plugin_implementation__.on_gcode_sending,
        "octoprint.events.register_custom_events": __plugin_implementation__.register_custom_events
    }
