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

import sys
import types
import webbrowser
import threading
import time
import sublime
import sublime_plugin
from functools import partial

# Reloading modules
for key in sys.modules.keys():
    if key.startswith('OmniMarkupLib'):
        try:
            mod = sys.modules[key]
            if type(mod) is types.ModuleType:
                reload(mod)
        except:
            pass

import OmniMarkupLib.LinuxModuleChecker
OmniMarkupLib.LinuxModuleChecker.check()

from OmniMarkupLib import log
from OmniMarkupLib.Setting import Setting
from OmniMarkupLib.Server import Server
from OmniMarkupLib.RendererManager import RendererManager
from OmniMarkupLib.Common import Singleton, RenderedMarkupCache

try:
    from OmniMarkupLib import OnDemandDownloader
except:
    log.exception("Error on loading OnDemandDownloader")


class OmniMarkupPreviewCommand(sublime_plugin.TextCommand):
    def run(self, edit, immediate=True):
        url = 'http://localhost:%d/view/%d' % \
            (Setting.instance().server_port, self.view.buffer_id())
        # Open with the default browser
        webbrowser.open(url, new=2)

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


class DelayedViewsWorker(threading.Thread):
    WAIT_TIMEOUT = 0.02

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
            with self.cond:
                if view_id in self.delayed_views:
                    del self.delayed_views[view_id]
                    self.cond.notify()
            RendererManager.queue_view(view, only_exists=True)
            self.last_signaled = now
        else:
            with self.cond:
                filename = view.file_name()
                if view_id not in self.delayed_views:
                    self.delayed_views[view_id] = self.Entry(view, filename, timeout)
                else:
                    entry = self.delayed_views[view_id]
                    entry.view = view
                    entry.filename = filename
                    entry.timeout = timeout
                self.cond.notify()

    def queue_to_renderer_manager(self, view, filename):
        view_id = view.id()
        valid_view = False
        for window in sublime.windows():
            if valid_view:
                break
            for v in window.views():
                if v.id() == view_id:  # Got view
                    valid_view = True
                    break

        if not valid_view or view.is_loading() or view.file_name() != filename:
            return
        if RendererManager.has_renderer_enabled_in_view(view):
            RendererManager.queue_view(view, only_exists=True)
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
                if len(self.delayed_views) > 0:
                    now = time.time()
                    diff_time = now - prev_time
                    for view_id in self.delayed_views.keys():
                        o = self.delayed_views[view_id]
                        o.timeout -= min(diff_time, self.WAIT_TIMEOUT)
                        if o.timeout <= 0:
                            del self.delayed_views[view_id]
                            sublime.set_timeout(partial(self.queue_to_renderer_manager,
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
        self.delayed_views_worker = DelayedViewsWorker()
        self.delayed_views_worker.start()

    def __del__(self):
        self.delayed_views_worker.stop()

    def on_load(self, view):
        if view.is_scratch() or not Setting.instance().refresh_on_loaded:
            return
        self.delayed_views_worker.queue(view, preemptive=True)

    def on_modified(self, view):
        if view.is_scratch() or not Setting.instance().refresh_on_modified:
            return
        self.delayed_views_worker.queue(view, preemptive=False,
                                        timeout=float(Setting.instance().refresh_on_modified_delay) / 1000)

    def on_post_save(self, view):
        if view.is_scratch() or not Setting.instance().refresh_on_saved:
            return
        self.delayed_views_worker.queue(view, preemptive=True)

    def on_query_context(self, view, key, operator, operand, match_all):
        # omp_is_enabled is here for backwards compatibility
        if key == 'omnimarkup_is_enabled' or key == 'omp_is_enabled':
            return RendererManager.has_renderer_enabled_in_view(view)
        return None

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
        PLUGIN_NAME = __name__
        if (setting.ajax_polling_interval != self.old_ajax_polling_interval or
            setting.html_template_name != self.old_html_template_name):
            sublime.status_message(PLUGIN_NAME + ' requires browser reload to apply changes')

        need_server_restart = (
            (setting.server_host != self.old_server_host) or
            (setting.server_port != self.old_server_port)
        )
        if need_server_restart:
            self.restart_server()

        self.try_download_mathjax()

    def subscribe_setting_events(self):
        Setting.instance().subscribe('changing', self.on_setting_changing)
        Setting.instance().subscribe('changed', self.on_setting_changed)

    def restart_server(self):
        global g_server
        if g_server is not None:
            self.stop_server()
        setting = Setting.instance()
        g_server = Server(host=setting.server_host, port=setting.server_port)

    def stop_server(self):
        global g_server
        if g_server is not None:
            g_server.stop()
            g_server = None

    def try_download_mathjax(self, setting=None):
        if setting is None:
            setting = Setting.instance()
        if setting.mathjax_enabled:
            OnDemandDownloader.on_demand_download_mathjax()


def unload_handler():
    log.info('Unloading plugin...')
    # Cleaning up resources...
    PluginManager.instance().stop_server()
    # Stopping renderer worker
    RendererManager.WORKER.stop()


# Setting must be the first to initialize.
Setting.instance().init()
PluginManager.instance().subscribe_setting_events()
RendererManager.init()
RendererManager.WORKER.start()
PluginManager.instance().restart_server()
PluginManager.instance().try_download_mathjax()
