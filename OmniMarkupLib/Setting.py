import sublime

from . import log
from .Common import Singleton


class SettingEventSource(object):
    def __init__(self):
        self._subscribers = {}

    def notify(self, evt_type, *evt_args, **evt_kwargs):
        if evt_type not in self._subscribers:
            return

        for subscriber in self._subscribers[evt_type]:
            try:
                subscriber(*evt_args, **evt_kwargs)
            except:
                log.exception("Error on calling event subscriber for setting: %s", str(subscriber))

    def subscribe(self, evt_type, subscriber):
        if evt_type not in self._subscribers:
            self._subscribers[evt_type] = set()
        self._subscribers[evt_type].add(subscriber)

    def clear_subscribers(self):
        self._subscribers.clear()


@Singleton
class Setting(SettingEventSource):
    DEFAULT_EXPORT_OPTIONS = {
        "target_folder": ".",
        "timestamp_format": "_%y%m%d%H%M%S",
        "copy_to_clipboard": False,
        "open_after_exporting": False
    }

    def __init__(self):
        SettingEventSource.__init__(self)

    def load_setting(self):
        PLUGIN_NAME = 'OmniMarkupPreviewer'
        settings = sublime.load_settings(PLUGIN_NAME + '.sublime-settings')
        settings.clear_on_change(PLUGIN_NAME)
        settings.add_on_change(PLUGIN_NAME, self.sublime_settings_on_change)

        self._sublime_settings = settings
        self.server_host = settings.get("server_host", '127.0.0.1')
        self.server_port = settings.get("server_port", 51004)
        self.refresh_on_modified = settings.get("refresh_on_modified", True)
        self.refresh_on_modified_delay = settings.get("refresh_on_modified_delay", 500)
        self.refresh_on_saved = settings.get("refresh_on_saved", True)
        self.browser_command = settings.get("browser_command", [])
        self.html_template_name = settings.get("html_template_name", 'github')
        self.ajax_polling_interval = settings.get("ajax_polling_interval", 500)
        self.ignored_renderers = set(settings.get("ignored_renderers", []))
        self.mathjax_enabled = settings.get("mathjax_enabled", False)
        self.http_proxy = settings.get("http_proxy", None)
        self.https_proxy = settings.get("https_proxy", None)
        self.export_options = self.DEFAULT_EXPORT_OPTIONS.copy()
        # Merge with the user defined export options
        self.export_options.update(settings.get("export_options", {}))

    def init(self):
        self.clear_subscribers()
        self.load_setting()

    def sublime_settings_on_change(self):
        log.info('Reloading settings...')
        self.notify('changing', setting=self)
        self.load_setting()
        self.notify('changed', setting=self)
