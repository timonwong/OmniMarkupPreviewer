"""
Copyright (c) 2013 Timon Wong

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import sublime
import sublime_plugin

import codecs
import os
import locale
import subprocess
import sys
import tempfile
import threading
import time
import types
from functools import partial


PY3K = sys.version_info >= (3, 0, 0)

if PY3K:
    from imp import reload

# Reloading modules
for key in sys.modules.keys():
    if key.find('OmniMarkupLib') >= 0:
        try:
            mod = sys.modules[key]
            if isinstance(mod, types.ModuleType):
                reload(mod)
        except:
            pass

if PY3K:
    from .OmniMarkupLib import log, Server
    from .OmniMarkupLib.Setting import Setting
    from .OmniMarkupLib.RendererManager import RenderedMarkupCache, RendererManager
    from .OmniMarkupLib.Common import Singleton
    from .OmniMarkupLib import desktop
else:
    exec('import OmniMarkupLib.LinuxModuleChecker')
    from OmniMarkupLib import log, Server
    from OmniMarkupLib.Setting import Setting
    from OmniMarkupLib.RendererManager import RenderedMarkupCache, RendererManager
    from OmniMarkupLib.Common import Singleton
    from OmniMarkupLib import desktop


def launching_web_browser_for_url(url, success_msg_default=None, success_msg_user=None):
    try:
        setting = Setting.instance()
        if setting.browser_command:
            browser_command = [os.path.expandvars(arg).format(url=url)
                               for arg in setting.browser_command]

            if os.name == 'nt':
                # unicode arguments broken under windows
                encoding = locale.getpreferredencoding()
                browser_command = [arg.encode(encoding) for arg in browser_command]

            subprocess.Popen(browser_command)
            if success_msg_user:
                sublime.status_message(success_msg_user)
        else:
            # Default web browser
            desktop.open(url)
            if success_msg_default:
                sublime.status_message(success_msg_default)
    except:
        if setting.browser_command:
            log.exception('Error while launching user defined web browser')
        else:
            log.exception('Error while launching default web browser')


class OmniMarkupPreviewCommand(sublime_plugin.TextCommand):
    def run(self, edit, immediate=True):
        # Whether RendererManager is finished loading?
        if not RendererManager.ensure_started():
            sublime.status_message('OmniMarkupPreviewer have not yet started')
            return

        buffer_id = self.view.buffer_id()
        # Opened in a tab already?
        opened = False
        for view in self.view.window().views():
            if view.buffer_id() == buffer_id:
                opened = True
                break
        if not opened:
            RendererManager.enqueue_view(self.view, immediate=True)

        host = Setting.instance().server_host
        port = Setting.instance().server_port
        if host == '0.0.0.0':
            host = '127.0.0.1'
        url = 'http://%s:%d/view/%d' % (host, port, buffer_id)
        # Open with the default browser
        log.info('Launching web browser for %s', url)
        launching_web_browser_for_url(
            url,
            success_msg_default='Preview launched in default web browser',
            success_msg_user='Preview launched in user defined web browser')

    def is_enabled(self):
        return RendererManager.any_available_renderer_for_view(self.view)


class OmniMarkupCleanCacheCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        storage = RenderedMarkupCache.instance()
        storage.clean()


class OmniMarkupExportCommand(sublime_plugin.TextCommand):
    def copy_to_clipboard(self, html_content):
        sublime.set_clipboard(html_content)
        sublime.status_message('Exported result copied to clipboard')

    def write_to_file(self, html_content, setting):
        target_folder = setting.export_options.get('target_folder', '.')

        if target_folder is not None:
            fullpath = self.view.file_name() or ''
            timestamp_format = setting.export_options.get('timestamp_format', '_%y%m%d%H%M%S')
            timestr = time.strftime(timestamp_format, time.localtime())

            if (not os.path.exists(fullpath) and target_folder == '.') or \
                    not os.path.isdir(target_folder):
                target_folder = None
            elif target_folder == '.':
                fn_base, _ = os.path.splitext(fullpath)
                html_fn = '%s%s.html' % (fn_base, timestr)
            elif not os.path.exists(fullpath):
                html_fn = os.path.join(target_folder, 'Untitled%s.html' % timestr)
            else:
                fn_base = os.path.basename(fullpath)
                html_fn = os.path.join(target_folder, '%s%s.html' % (fn_base, timestr))

        # No target folder, create file in temporary directory
        if target_folder is None:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as f:
                html_fn = f.name

        with codecs.open(html_fn, 'w', encoding='utf-8') as html_file:
            html_file.write(html_content)
            log.info('Successfully exported to: %s', html_fn)

        return html_fn

    def run(self, edit, clipboard_only=False):
        view = self.view
        try:
            html_content = RendererManager.render_view_as_html(view)

            if clipboard_only:
                self.copy_to_clipboard(html_content)
                return

            setting = Setting.instance()
            html_fn = self.write_to_file(html_content, setting)

            # Copy contents to clipboard
            if setting.export_options.get('copy_to_clipboard', False):
                self.copy_to_clipboard(html_content)

            # Open output file if necessary
            if setting.export_options.get('open_after_exporting', False):
                log.info('Launching web browser for %s', html_fn)
                launching_web_browser_for_url(html_fn)

        except NotImplementedError:
            pass
        except:
            sublime.error_message('Error while exporting, please check your console for more information.')
            log.exception('Error while exporting')

    def is_enabled(self):
        return RendererManager.any_available_renderer_for_view(self.view)


class ThrottleQueue(threading.Thread):
    WAIT_TIMEOUT = 0.02

    class Entry(object):
        def __init__(self, view, timeout):
            self.view = view
            self.filename = view.file_name()
            self.timeout = timeout

        def __cmp__(self, other):
            return self.id == other.id

        def __hash__(self):
            return hash(self.id)

    def __init__(self):
        threading.Thread.__init__(self)
        self.mutex = threading.Lock()
        self.cond = threading.Condition(self.mutex)
        self.stopping = False
        self.last_signaled = time.time()
        self.view_entry_mapping = {}

    def put(self, view, preemptive=True, timeout=0.5):
        if not RendererManager.any_available_renderer_for_view(view):
            return

        view_id = view.id()
        now = time.time()

        with self.mutex:
            if view_id in self.view_entry_mapping:
                # Too fast, cancel this operation
                if now - self.last_signaled <= 0.01:
                    return

        if preemptive:
            # Cancel pending actions
            with self.cond:
                if view_id in self.view_entry_mapping:
                    del self.view_entry_mapping[view_id]
                    self.cond.notify()
            RendererManager.enqueue_view(view, only_exists=True)
            self.last_signaled = now
        else:
            with self.cond:
                filename = view.file_name()
                if view_id not in self.view_entry_mapping:
                    self.view_entry_mapping[view_id] = self.Entry(view, timeout)
                else:
                    entry = self.view_entry_mapping[view_id]
                    entry.view = view
                    entry.filename = filename
                    entry.timeout = timeout
                self.cond.notify()

    def enqueue_view_to_renderer_manager(self, view, filename):
        if view.is_loading() or view.file_name() != filename:
            return
        if RendererManager.any_available_renderer_for_view(view):
            RendererManager.enqueue_view(view, only_exists=True)
            self.last_signaled = time.time()

    def run(self):
        prev_time = time.time()
        while True:
            with self.cond:
                if self.stopping:
                    break
                self.cond.wait(self.WAIT_TIMEOUT)
                if self.stopping:
                        break
                if len(self.view_entry_mapping) > 0:
                    now = time.time()
                    diff_time = now - prev_time
                    prev_time = time.time()
                    for view_id in list(self.view_entry_mapping.keys()):
                        o = self.view_entry_mapping[view_id]
                        o.timeout -= max(diff_time, self.WAIT_TIMEOUT)
                        if o.timeout <= 0:
                            del self.view_entry_mapping[view_id]
                            sublime.set_timeout(partial(self.enqueue_view_to_renderer_manager,
                                                        o.view, o.filename), 0)
                else:
                    # No more items, sleep
                    self.cond.wait()

    def stop(self):
        with self.cond:
            self.stopping = True
            self.cond.notify()
        self.join()


class PluginEventListener(sublime_plugin.EventListener):
    def __init__(self):
        self.throttle = ThrottleQueue()
        self.throttle.start()

    def __del__(self):
        self.throttle.stop()

    def on_query_context(self, view, key, operator, operand, match_all):
        # `omp_is_enabled` for backwards compatibility
        if key == 'omnimarkup_is_enabled' or key == 'omp_is_enabled':
            return RendererManager.any_available_renderer_for_view(view)
        return None

    def _on_close(self, view):
        storage = RenderedMarkupCache.instance()
        entry = storage.get_entry(view.buffer_id())
        if entry is not None:
            entry.disconnected = True

    def _on_modified(self, view):
        # Prevent rare complaintion about slow callback
        def callback():
            setting = Setting.instance()
            if not setting.refresh_on_modified:
                return
            timeout = setting.refresh_on_modified_delay / 1000.0
            self.throttle.put(view, preemptive=False, timeout=timeout)
        if PY3K:
            callback()
        else:
            sublime.set_timeout(callback, 0)

    def _on_post_save(self, view):
        if not Setting.instance().refresh_on_saved:
            return
        self.throttle.put(view, preemptive=True)

    if PY3K:
        on_close_async = _on_close
        on_modified_async = _on_modified
        on_post_save_async = _on_post_save
    else:
        on_close = _on_close
        on_modified = _on_modified
        on_post_save = _on_post_save

g_server = None


@Singleton
class PluginManager(object):
    def __init__(self):
        setting = Setting.instance()
        self.on_setting_changing(setting)

    def on_setting_changing(self, setting):
        self.old_server_host = setting.server_host
        self.old_server_port = setting.server_port
        self.old_ajax_polling_interval = setting.ajax_polling_interval
        self.old_html_template_name = setting.html_template_name

    def on_setting_changed(self, setting):
        if (setting.ajax_polling_interval != self.old_ajax_polling_interval or
                setting.html_template_name != self.old_html_template_name):
            sublime.status_message('OmniMarkupPreviewer requires a browser reload to apply changes')

        need_server_restart = (setting.server_host != self.old_server_host or
                               setting.server_port != self.old_server_port)
        if need_server_restart:
            self.restart_server()

    def subscribe_setting_events(self):
        Setting.instance().subscribe('changing', self.on_setting_changing)
        Setting.instance().subscribe('changed', self.on_setting_changed)

    def restart_server(self):
        global g_server
        if g_server is not None:
            self.stop_server()
        setting = Setting.instance()
        g_server = Server.Server(host=setting.server_host, port=setting.server_port)

    def stop_server(self):
        global g_server
        if g_server is not None:
            g_server.stop()
            g_server = None


def unload_handler():
    log.info('Unloading plugin...')
    # Cleaning up resources...
    PluginManager.instance().stop_server()
    # Stopping renderer worker
    RendererManager.stop()


def plugin_loaded():
    Server.init()
    # Setting must be the first to initialize.
    Setting.instance().init()
    PluginManager.instance().subscribe_setting_events()
    RendererManager.start()
    PluginManager.instance().restart_server()

if not PY3K:
    plugin_loaded()
