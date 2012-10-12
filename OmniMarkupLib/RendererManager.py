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
import os
import os.path
import re
import log
import threading
from collections import namedtuple
from Common import RenderedMarkupCache, RenderedMarkupCacheEntry, generate_timestamp
import LibraryPathManager


__file__ = os.path.normpath(os.path.abspath(__file__))
__path__ = os.path.dirname(__file__)


WorkerQueueItem = namedtuple('WorkerQueueItem',
    ['timestamp', 'fullpath', 'lang', 'text']
)


class MarkupRenderer:
    def is_enabled(self, filename, lang):
        return False

    def render(self, text):
        raise NotImplementedError()


class RendererWorker(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.mutex = threading.Lock()
        self.cond = threading.Condition(self.mutex)
        self.que = {}

    def queue(self, buffer_id, fullpath, lang, text):
        item = WorkerQueueItem(
            timestamp=generate_timestamp(),
            fullpath=fullpath,
            lang=lang,
            text=text
        )
        with self.cond:
            self.que[buffer_id] = item
            self.cond.notify()

    def run(self):
        while True:
            with self.cond:
                self.cond.wait()
                items = self.que.items()
                self.que.clear()
            for buffer_id, item in items:
                try:
                    filename = os.path.basename(item.fullpath)
                    dirname = os.path.dirname(item.fullpath)
                    html_part = RendererManager._render_text(filename, item.lang, item.text)
                    entry = RenderedMarkupCacheEntry(
                        timestamp=generate_timestamp(),
                        filename=filename,
                        dirname=dirname,
                        html_part=html_part
                    )
                    RenderedMarkupCache.instance().set_entry(buffer_id, entry)
                except NotImplementedError:
                    pass
                except:
                    log.exception("")


class RendererManager:
    WORKER = RendererWorker()
    LANG_RE = re.compile(r"^[^\s]+(?=\s+)")
    RENDERER_TYPES = {}

    @classmethod
    def register(cls, renderer_type):
        if renderer_type not in cls.RENDERER_TYPES:
            cls.RENDERER_TYPES[renderer_type] = None

    @classmethod
    def create_or_get_renderer(cls, renderer_type):
        renderer = cls.RENDERER_TYPES[renderer_type]
        if renderer is None:  # then create a new instance
            renderer = renderer_type()
        return renderer

    @classmethod
    def is_renderers_enabled(cls, filename, lang):
        for renderer_type in cls.RENDERER_TYPES.keys():
            renderer = cls.create_or_get_renderer(renderer_type)
            if renderer.is_enabled(filename, lang):
                return True
        return False

    @classmethod
    def get_lang_by_scope_name(cls, scope_name):
        m = cls.LANG_RE.search(scope_name)
        if m is None:
            lang = ""
        else:
            lang = m.group(0).lower()
        return lang

    @classmethod
    def is_renderers_enabled_in_view(cls, view):
        filename = view.file_name()
        lang = cls.get_lang_by_scope_name(view.scope_name(0))
        return cls.is_renderers_enabled(filename, lang)

    @classmethod
    def _render_text(cls, filename, lang, text):
        for renderer_type in cls.RENDERER_TYPES.keys():
            try:
                renderer = cls.create_or_get_renderer(renderer_type)
                if renderer.is_enabled(filename, lang):
                    return renderer.render(text)
            except:
                log.exception('Exception occured while rendering using %s', renderer_type)
        raise NotImplementedError()

    @classmethod
    def queue_current_view(cls, view):
        import sublime
        region = sublime.Region(0, view.size())
        text = view.substr(region)
        lang = cls.get_lang_by_scope_name(view.scope_name(0))
        cls.WORKER.queue(view.buffer_id(), view.file_name(), lang, text)

    @staticmethod
    def load_renderers():
        # Add library path to sys.path
        st2_dir = LibraryPathManager.add_search_path(os.path.dirname(sys.executable))

        # Change the current directory to that of the module. It's not safe to just
        # add the modules directory to sys.path, as that won't accept unicode paths
        # on Windows
        renderers_path = os.path.normpath(os.path.join(__path__, '..', 'renderers'))
        oldpath = os.getcwdu()
        os.chdir(renderers_path)
        try:
            module_list = [f
                for f in os.listdir(renderers_path) if f.endswith(".py")
            ]
            # Load each renderer
            for module_file in module_list:
                module_name = module_file[:-3]
                try:
                    if module_name in sys.modules:
                        del sys.modules[module_name]
                    __import__(module_name, globals(), locals(), [], -1)
                except:
                    log.exception("Failed to load renderer: %s", module_name)

        finally:
            # Restore the current directory
            os.chdir(oldpath)
            # Clean sys path for library loading
            LibraryPathManager.remove_search_path(st2_dir)


RendererManager.WORKER.daemon = True
RendererManager.WORKER.start()
