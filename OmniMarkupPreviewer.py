"""
Copyright (c) 2012 Timon Wong

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

import webbrowser
import threading
import time
import sublime
import sublime_plugin
from functools import partial
from OmniMarkupLib import log
from OmniMarkupLib.Server import Server
from OmniMarkupLib.RendererManager import RendererManager
from OmniMarkupLib.Common import RenderedMarkupCache


class Setting(object):
    def __init__(self):
        self.server_port = 51004
        self.refresh_on_modified = True
        self.refresh_on_modified_delay = 500
        self.refresh_on_saved = True
        self.refresh_on_loaded = True


g_setting = Setting()
g_server = None


class OmniMarkupPreviewCommand(sublime_plugin.TextCommand):
    def run(self, edit, immediate=True):
        RendererManager.queue_view(self.view, immediate=True)
        # Open browser
        try:
            global g_setting
            webbrowser.open('http://localhost:%d/view/%d' % (g_setting.server_port, self.view.buffer_id()))
        except:
            log.exception("Error on opening web browser")

    def is_enabled(self):
        return RendererManager.has_renderer_enabled_in_view(self.view)


class OmniMarkupCleanCacheCommand(sublime_plugin.ApplicationCommand):
    def run(self, remove_all=False):
        storage = RenderedMarkupCache.instance()
        if remove_all:
            storage.clean()
            return
        keep_ids_list = []
        for window in sublime.windows():
            for view in window.views():
                keep_ids_list.append(view.buffer_id())
        storage.clean(keep_ids=set(keep_ids_list))


def settings_changed():
    log.info('Reload settings...')
    reload_settings()


def reload_settings():
    global g_setting
    settings = sublime.load_settings(__name__ + '.sublime-settings')
    settings.clear_on_change(__name__)
    settings.add_on_change(__name__, settings_changed)

    old_server_port = g_setting.server_port
    g_setting.server_port = settings.get("server_port", 51004)
    g_setting.refresh_on_modified = settings.get("refresh_on_modified", True)
    g_setting.refresh_on_modified_delay = settings.get("refresh_on_modified_delay", 500)
    g_setting.refresh_on_saved = settings.get("refresh_on_saved", True)
    g_setting.refresh_on_loaded = settings.get("refresh_on_loaded", True)
    # Show status on server port change
    if g_setting.server_port != old_server_port:
        sublime.status_message(__name__ + ' requires restart due to server port change')


reload_settings()
RendererManager.load_renderers()
g_server = Server(g_setting.server_port)


class DelayedViewsWorker(threading.Thread):
    WAIT_TIMEOUT = 0.05

    class Entry(object):
        def __init__(self, view, filename, timeout):
            self.view = view
            self.filename = filename
            self.timeout = timeout

    def __init__(self):
        threading.Thread.__init__(self)
        self.mutex = threading.Lock()
        self.cond = threading.Condition(self.mutex)
        self.stopping = False
        self.last_signaled = time.time()
        self.delayed_views = {}

    def queue(self, view, preemptive=True, timeout=0.5):
        if not RendererManager.has_renderer_enabled_in_view(view):
            return

        view_id = view.id()
        now = time.time()

        with self.mutex:
            if view_id in self.delayed_views:
                if now - self.last_signaled <= 0.01:  # Too fast, cancel this operation
                    return

        if preemptive:
            # Cancel pending actions
            with self.mutex:
                if view_id in self.delayed_views:
                    del self.delayed_views[view_id]
            RendererManager.queue_view(view, only_exists=True)
            self.last_signaled = now
        else:
            with self.mutex:
                filename = view.file_name()
                if view_id not in self.delayed_views:
                    self.delayed_views[view_id] = self.Entry(view, filename, timeout)
                else:
                    entry = self.delayed_views[view_id]
                    entry.view = view
                    entry.filename = filename
                    entry.timeout = timeout

    def __queue_checked(self, view, filename):
        view_id = view.id()
        valid_view = False
        for window in sublime.windows():
            if valid_view:
                break
            for v in window.views():
                if v.id() == view_id:  # Got view
                    valid_view = view
                    break

        if not valid_view or view.is_loading() or view.file_name() != filename:
            return
        if RendererManager.has_renderer_enabled_in_view(view):
            RendererManager.queue_view(view, only_exists=True)
            self.last_signaled = time.time()

    def run(self):
        while not self.stopping:
            with self.cond:
                self.cond.wait(self.WAIT_TIMEOUT)
                if len(self.delayed_views) == 0:
                    continue
                for view_id in self.delayed_views.keys():
                    o = self.delayed_views[view_id]
                    o.timeout -= self.WAIT_TIMEOUT
                    if o.timeout <= 0:
                        del self.delayed_views[view_id]
                        sublime.set_timeout(partial(self.__queue_checked, o.view, o.filename), 0)

    def stop(self):
        self.stopping = True
        self.join()


class PluginEventListener(sublime_plugin.EventListener):
    def __init__(self):
        self.mutex = threading.Lock()
        self.delayed_views_worker = DelayedViewsWorker()
        self.delayed_views_worker.start()

    def __del__(self):
        self.delayed_views_worker.stop()

    def on_load(self, view):
        if view.is_scratch() or not g_setting.refresh_on_loaded:
            return
        self.delayed_views_worker.queue(view, preemptive=True)

    def on_modified(self, view):
        if view.is_scratch() or not g_setting.refresh_on_modified:
            return
        self.delayed_views_worker.queue(view, preemptive=False,
                                        timeout=float(g_setting.refresh_on_modified_delay) / 1000)

    def on_post_save(self, view):
        if view.is_scratch() or not g_setting.refresh_on_saved:
            return
        self.delayed_views_worker.queue(view, preemptive=True)

    def on_query_context(self, view, key, operator, operand, match_all):
        if key == 'omp_is_enabled':
            return RendererManager.has_renderer_enabled_in_view(view)
        return None


def unload_handler():
    # Cleaning up resources...
    # Stopping server
    global g_server
    log.info('Bottle server shuting down...')
    g_server.stop()
    # Stopping renderer worker
    RendererManager.WORKER.stop()
    # Reloading modules
    import sys
    import types
    for key in sys.modules.keys():
        if key.startswith('OmniMarkupLib'):
            try:
                mod = sys.modules[key]
                if type(mod) is types.ModuleType:
                    reload(mod)
            except:
                pass
