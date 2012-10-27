import sublime
import log
from Common import Singleton


@Singleton
class Setting(object):
    def __init__(self):
        self.server_port = 51004
        self.refresh_on_modified = True
        self.refresh_on_modified_delay = 500
        self.refresh_on_saved = True
        self.refresh_on_loaded = True
        self.ignored_renderers = set()

    def reload(self):  # Reload settings
        name = 'OmniMarkupPreviewer'
        settings = sublime.load_settings(name + '.sublime-settings')
        settings.clear_on_change(name)
        settings.add_on_change(name, self._on_settings_changed)

        old_server_port = self.server_port

        self.server_port = settings.get("server_port", 51004)
        self.refresh_on_modified = settings.get("refresh_on_modified", True)
        self.refresh_on_modified_delay = settings.get("refresh_on_modified_delay", 500)
        self.refresh_on_saved = settings.get("refresh_on_saved", True)
        self.refresh_on_loaded = settings.get("refresh_on_loaded", True)
        self.ignored_renderers = set(settings.get("ignored_renderers", []))

        # Show status on server port change
        if self.server_port != old_server_port:
            sublime.status_message(name + ' requires restart due to server port change')

    def _on_settings_changed(self):
        log.info('Reload settings...')
        self.reload()
