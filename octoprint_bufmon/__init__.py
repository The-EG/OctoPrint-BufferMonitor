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
        self._planner_hist = {}
        self._input_hist = {}
        self._print_name = None

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

        if p not in self._planner_hist:
            self._logger.warning(f"Planner buffer size incorrect? {p} not in _planner_hist")
            self._planner_hist[p] = 0
        if b not in self._input_hist:
            self._logger.warning(f"Input buffer size incorrect? {b} not in _input_hist")
            self._input_hist[b] = 0

        self._planner_hist[p] += 1
        self._input_hist[b] += 1

        if self._last_msg is None or (datetime.datetime.now() - self._last_msg).total_seconds() > 1.0:
            self._last_msg = datetime.datetime.now()
            self.send_data_event()

        return line

    def send_data_event(self):
        event = octoprint.events.Events.PLUGIN_BUFMON_BUFFER_DATA
        data = {
            'planner_hist': self._planner_hist,
            'input_hist': self._input_hist,
            'print_name': self._print_name
        }
        self._logger.debug(f"Sending buffer data: {data}")
        self._event_bus.fire(event, payload=data)

    def on_event(self, event, payload):
        if event=='PrintStarted':
            self._logger.debug("Print started")
            self._print_name = payload['name']
            self._in_print = True
            self._planner_hist = { p:0 for p in range(self._planner_size) }
            self._input_hist = { i:0 for i in range(self._input_size) }
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
