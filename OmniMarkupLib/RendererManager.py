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
import re
import base64
from urlparse import urlparse
import threading
import inspect
import mimetypes
import sublime
from OmniMarkupLib.Setting import Setting
from OmniMarkupLib.Common import RWLock, RenderedMarkupCache, RenderedMarkupCacheEntry
from OmniMarkupLib import LibraryPathManager
from OmniMarkupLib import log


__file__ = os.path.normpath(os.path.abspath(__file__))
__path__ = os.path.dirname(__file__)


LibraryPathManager.push_search_path(os.path.dirname(sys.executable))
LibraryPathManager.push_search_path(os.path.join(__path__, 'libs'))
try:
    from bottle import template
finally:
    LibraryPathManager.pop_search_path()
    LibraryPathManager.pop_search_path()


class WorkerQueueItem(object):
    def __init__(self, timestamp=0, fullpath='untitled', lang='', text=''):
        self.timestamp = timestamp
        self.fullpath = fullpath or 'untitled'
        self.lang = lang
        self.text = text


class RendererWorker(threading.Thread):
    def __init__(self, mutex):
        threading.Thread.__init__(self)
        self.cond = threading.Condition(mutex)
        self.que = {}
        self.stopping = False

    def queue(self, buffer_id, fullpath, lang, text, immediate=False):
        item = WorkerQueueItem(fullpath=fullpath, lang=lang, text=text)
        if immediate:  # Render in the main thread
            self._run_queued_item(buffer_id, item)
        else:
            with self.cond:
                self.que[buffer_id] = item
                self.cond.notify()

    def _run_queued_item(self, buffer_id, item):
        try:
            # Render text and save to cache
            filename = os.path.basename(item.fullpath)
            dirname = os.path.dirname(item.fullpath)
            html_part = RendererManager.render_text(item.fullpath, item.lang, item.text)
            entry = RenderedMarkupCacheEntry(filename=filename, dirname=dirname, html_part=html_part)
            RenderedMarkupCache.instance().set_entry(buffer_id, entry)
        except NotImplementedError:
            pass
        except:
            log.exception("")

    def run(self):
        while True:
            with self.cond:
                self.cond.wait()
                if self.stopping:
                    break
                if len(self.que) == 0:
                    continue
                items = self.que.items()
                self.que.clear()
            for buffer_id, item in items:
                self._run_queued_item(buffer_id, item)

    def stop(self):
        self.stopping = True
        with self.cond:
            self.cond.notify()
        self.join()


class RendererManager(object):
    MUTEX = threading.Lock()
    RW_LOCK = RWLock(MUTEX)

    WORKER = RendererWorker(MUTEX)
    LANG_RE = re.compile(r"^[^\s]+(?=\s+)")
    RENDERERS = []

    @classmethod
    def has_any_valid_renderer(cls, filename, lang):
        # filename may be None, so prevent it
        filename = filename or ""
        with cls.RW_LOCK.readlock:
            for renderer_classname, renderer in cls.RENDERERS:
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
    def has_renderer_enabled_in_view(cls, view):
        filename = view.file_name()
        lang = cls.get_lang_by_scope_name(view.scope_name(0))
        return cls.has_any_valid_renderer(filename, lang)

    @classmethod
    def render_text(cls, fullpath, lang, text, post_process_func=None):
        if post_process_func is None:
            post_process_func = cls.render_text_postprocess
        filename = os.path.basename(fullpath)
        with cls.RW_LOCK.readlock:
            for renderer_classname, renderer in cls.RENDERERS:
                try:
                    if renderer.is_enabled(filename, lang):
                        rendered_text = renderer.render(text, filename=filename)
                        return post_process_func(rendered_text, fullpath)
                except:
                    log.exception('Exception occured while rendering using %s', renderer_classname)
        raise NotImplementedError()

    IMG_TAG_RE = re.compile('(<img [^>]*src=")([^"]+)("[^>]*>)', re.DOTALL | re.IGNORECASE | re.MULTILINE)

    @classmethod
    def render_text_postprocess(cls, rendered_text, filename):
        dirname = os.path.dirname(filename)

        def encode_image_path(m):
            url = m.group(2)
            o = urlparse(url)
            if len(o.scheme) > 0:
                # Is a valid url, returns original text
                return m.group(0)
            # or local file (maybe?)
            local_path = os.path.normpath(os.path.join(dirname, url))
            return m.group(1) + '/local/' + base64.urlsafe_b64encode(local_path.encode('utf-8')) + m.group(3)

        return cls.IMG_TAG_RE.sub(encode_image_path, rendered_text)

    @classmethod
    def render_text_postprocess_exporting(cls, rendered_text, filename):
        # Embedding images
        dirname = os.path.dirname(filename)

        def encode_image_path(m):
            url = m.group(2)
            o = urlparse(url)
            if len(o.scheme) > 0:
                # Is a valid url, returns original text
                return m.group(0)
            # or local file (maybe?)
            local_path = os.path.normpath(os.path.join(dirname, url))
            mime_type, _ = mimetypes.guess_type(os.path.basename(local_path))
            if mime_type is not None:
                data_uri = open(local_path, 'rb').read().encode('base64').replace('\n', '')
                image_tag_src = 'data:%s;base64,%s' % (mime_type, data_uri)
            else:
                image_tag_src = '[Invalid mime type]'
            return m.group(1) + image_tag_src + m.group(3)

        return cls.IMG_TAG_RE.sub(encode_image_path, rendered_text)

    @classmethod
    def render_view_to_string(cls, view):
        fullpath = view.file_name() or ''
        lang = RendererManager.get_lang_by_scope_name(view.scope_name(0))
        text = view.substr(sublime.Region(0, view.size()))
        html_part = RendererManager.render_text(
            fullpath, lang, text,
            post_process_func=cls.render_text_postprocess_exporting
        )
        setting = Setting.instance()
        return template(setting.export_options['template_name'],
                        mathjax_enabled=setting.mathjax_enabled,
                        filename=os.path.basename(fullpath),
                        dirname=os.path.dirname(fullpath),
                        html_part=html_part
        )

    @classmethod
    def queue_view(cls, view, only_exists=False, immediate=False):
        buffer_id = view.buffer_id()
        settings = view.settings()
        if only_exists and not RenderedMarkupCache.instance().exists(buffer_id):
            # If current view is previously rendered, then ignore 'only_exists'
            if not settings.get('omnimarkup_enabled', False):
                return
        settings.set('omnimarkup_enabled', True)
        region = sublime.Region(0, view.size())
        text = view.substr(region)
        lang = cls.get_lang_by_scope_name(view.scope_name(0))
        cls.WORKER.queue(buffer_id, view.file_name(), lang, text, immediate=immediate)

    @classmethod
    def _load_renderer(cls, renderers, module_file, module_name):
        try:
            __import__(module_name)
            mod = sys.modules[module_name] = reload(sys.modules[module_name])
            # Get classes
            classes = inspect.getmembers(mod, inspect.isclass)
            for classname, classtype in classes:
                # Register renderer into manager
                if hasattr(classtype, 'IS_VALID_RENDERER__'):
                    try:
                        log.info('Loaded renderer: OmniMarkupLib.Renderers.%s', classname)
                        # Add both classname and its instance
                        renderers.append((classname, classtype()))
                    except:
                        log.exception('Failed to load renderer: %s', classname)
        except:
            log.exception('Failed to load renderer module: OmniMarkupLib/Renderers/%s', module_file)

    @classmethod
    def load_renderers(cls):
        renderers = []
        # Add library path to sys.path
        LibraryPathManager.push_search_path(os.path.dirname(sys.executable))
        LibraryPathManager.add_search_path_if_not_exists(os.path.join(__path__, './Renderers/libs/'))

        # Change the current directory to that of the module. It's not safe to just
        # add the modules directory to sys.path, as that won't accept unicode paths
        # on Windows
        renderers_path = os.path.join(__path__, 'Renderers/')
        oldpath = os.getcwdu()
        os.chdir(os.path.join(__path__, '..'))
        try:
            module_list = [f
                for f in os.listdir(renderers_path) if f.endswith('Renderer.py')
            ]
            # Load each renderer
            for module_file in module_list:
                module_name = 'OmniMarkupLib.Renderers.' + module_file[:-3]
                cls._load_renderer(renderers, module_file, module_name)

        finally:
            # Restore the current directory
            os.chdir(oldpath)
            LibraryPathManager.pop_search_path()

        with cls.RW_LOCK.writelock:
            cls.RENDERERS = renderers

    OLD_IGNORED_RENDERERS = set()

    @classmethod
    def on_setting_changing(cls, setting):
        cls.OLD_IGNORED_RENDERERS = setting.ignored_renderers.copy()

    @classmethod
    def on_setting_changed(cls, setting):
        # Unload ignored renderers
        if cls.OLD_IGNORED_RENDERERS != setting.ignored_renderers:
            # Reload renderers, of course
            log.info('Reloading renderers...')
            cls.load_renderers()

        with cls.RW_LOCK.readlock:
            for renderer_classname, renderer in cls.RENDERERS:
                key = 'renderer_options-' + renderer_classname
                try:
                    renderer_options = setting._sublime_settings.get(key, {})
                    renderer.load_settings(renderer_options, setting)
                except:
                    log.exception('Error on setting renderer options for %s', renderer_classname)

    @classmethod
    def init(cls):
        setting = Setting.instance()
        setting.subscribe('changing', cls.on_setting_changing)
        setting.subscribe('changed', cls.on_setting_changed)

        cls.on_setting_changing(setting)
        cls.load_renderers()
        cls.on_setting_changed(setting)
