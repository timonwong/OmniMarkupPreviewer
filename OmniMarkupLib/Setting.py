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
        self.html_template_name = 'github'
        self.ajax_polling_interval = 500
        self.ignored_renderers = set()

    def reload(self):  # Reload settings
        name = 'OmniMarkupPreviewer'
        settings = sublime.load_settings(name + '.sublime-settings')
        settings.clear_on_change(name)
        settings.add_on_change(name, self._on_settings_changed)

        old_html_template_name = self.html_template_name
        old_ajax_polling_interval = self.ajax_polling_interval
        old_server_port = self.server_port

        self.server_port = settings.get("server_port", 51004)
        self.refresh_on_modified = settings.get("refresh_on_modified", True)
        self.refresh_on_modified_delay = settings.get("refresh_on_modified_delay", 500)
        self.refresh_on_saved = settings.get("refresh_on_saved", True)
        self.refresh_on_loaded = settings.get("refresh_on_loaded", True)
        self.html_template_name = settings.get("html_template_name", 'github')
        self.ajax_polling_interval = settings.get("ajax_polling_interval", 500)
        self.ignored_renderers = set(settings.get("ignored_renderers", []))

        if (self.ajax_polling_interval != old_ajax_polling_interval or
        self.html_template_name != old_html_template_name):
            sublime.status_message(name + ' requires browser reload to apply changes')
        else:
            # Show status on server port change
            if (self.server_port != old_server_port):
                sublime.status_message(name + ' requires restart to take effect')

    def _on_settings_changed(self):
        log.info('Reload settings...')
        self.reload()
