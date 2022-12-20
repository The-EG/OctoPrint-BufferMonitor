/*
 * View model for OctoPrint-BufferMonitor
 *
 * Author: Taylor Talkington
 * License: AGPLv3
 */
$(function() {
    function BufmonViewModel(parameters) {
        var self = this;

        // assign the injected parameters, e.g.:
        // self.loginStateViewModel = parameters[0];
        // self.settingsViewModel = parameters[1];

        self.lastPlanner = ko.observable(undefined);
        self.meanPlanner = ko.observable(undefined);
        self.lastBlock = ko.observable(undefined);
        self.meanBlock = ko.observable(undefined);

        self.onEventplugin_bufmon_buffer_data = function(payload) {
            self.meanPlanner(payload.mean_planner.toFixed(1));
            self.lastPlanner(payload.last_planner.toFixed(0));
            self.meanBlock(payload.mean_block.toFixed(1));
            self.lastBlock(payload.last_block.toFixed(0));
        }
    }

    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push({
        construct: BufmonViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: [ /* "loginStateViewModel", "settingsViewModel" */ ],
        // Elements to bind to, e.g. #settings_plugin_bufmon, #tab_plugin_bufmon, ...
        elements: [ "#navbar_plugin_bufmon" ]
    });
});
