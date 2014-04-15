import json
import os

import sublime

from . import log
from .Common import Singleton


__file__ = os.path.normpath(os.path.abspath(__file__))
__path__ = os.path.dirname(__file__)


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
    def __init__(self):
        SettingEventSource.__init__(self)

    @staticmethod
    def _read_default_settings():
        default_settings_filename = os.path.join(
            __path__, '../', 'default_settings.json')
        default_settings_filename = os.path.normpath(default_settings_filename)
        with open(default_settings_filename) as f:
            settings_obj = json.load(f)
        return settings_obj

    def _fix_setting_type(self):
        type_conversion_map = {
            'ignored_renderers': set,
        }
        for attr, typ in type_conversion_map.items():
            v = getattr(self, attr)
            setattr(self, attr, typ(v))

    def load_setting(self):
        PLUGIN_NAME = 'OmniMarkupPreviewer'
        settings = sublime.load_settings(PLUGIN_NAME + '.sublime-settings')
        settings.clear_on_change(PLUGIN_NAME)
        settings.add_on_change(PLUGIN_NAME, self.sublime_settings_on_change)

        self._sublime_settings = settings

        # Merge new settings into the default settings
        default_settings = self._read_default_settings()
        for k, v in default_settings.items():
            if isinstance(v, dict):
                v.update(settings.get(k, {}))
            else:
                v = settings.get(k, v)
            setattr(self, k, v)

        self._fix_setting_type()

    def get_setting(self, k, default=None):
        return getattr(self, k, default)

    def init(self):
        self.clear_subscribers()
        self.load_setting()

    def sublime_settings_on_change(self):
        log.info('Reloading settings...')
        self.notify('changing', setting=self)
        self.load_setting()
        self.notify('changed', setting=self)
