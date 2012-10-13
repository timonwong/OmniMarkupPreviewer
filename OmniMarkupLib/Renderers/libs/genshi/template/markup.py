# -*- coding: utf-8 -*-
#
# Copyright (C) 2006-2010 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://genshi.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://genshi.edgewall.org/log/.

"""Markup templating engine."""

from itertools import chain

from genshi.core import Attrs, Markup, Namespace, Stream, StreamEventKind
from genshi.core import START, END, START_NS, END_NS, TEXT, PI, COMMENT
from genshi.input import XMLParser
from genshi.template.base import BadDirectiveError, Template, \
                                 TemplateSyntaxError, _apply_directives, \
                                 EXEC, INCLUDE, SUB
from genshi.template.eval import Suite
from genshi.template.interpolation import interpolate
from genshi.template.directives import *
from genshi.template.text import NewTextTemplate

__all__ = ['MarkupTemplate']
__docformat__ = 'restructuredtext en'


class MarkupTemplate(Template):
    """Implementation of the template language for XML-based templates.
    
    >>> tmpl = MarkupTemplate('''<ul xmlns:py="http://genshi.edgewall.org/">
    ...   <li py:for="item in items">${item}</li>
    ... </ul>''')
    >>> print(tmpl.generate(items=[1, 2, 3]))
    <ul>
      <li>1</li><li>2</li><li>3</li>
    </ul>
    """

    DIRECTIVE_NAMESPACE = 'http://genshi.edgewall.org/'
    XINCLUDE_NAMESPACE = 'http://www.w3.org/2001/XInclude'

    directives = [('def', DefDirective),
                  ('match', MatchDirective),
                  ('when', WhenDirective),
                  ('otherwise', OtherwiseDirective),
                  ('for', ForDirective),
                  ('if', IfDirective),
                  ('choose', ChooseDirective),
                  ('with', WithDirective),
                  ('replace', ReplaceDirective),
                  ('content', ContentDirective),
                  ('attrs', AttrsDirective),
                  ('strip', StripDirective)]
    serializer = 'xml'
    _number_conv = Markup

    def __init__(self, source, filepath=None, filename=None, loader=None,
                 encoding=None, lookup='strict', allow_exec=True):
        Template.__init__(self, source, filepath=filepath, filename=filename,
                          loader=loader, encoding=encoding, lookup=lookup,
                          allow_exec=allow_exec)
        self.add_directives(self.DIRECTIVE_NAMESPACE, self)

    def _init_filters(self):
        Template._init_filters(self)
        # Make sure the include filter comes after the match filter
        self.filters.remove(self._include)
        self.filters += [self._match, self._include]

    def _parse(self, source, encoding):
        if not isinstance(source, Stream):
            source = XMLParser(source, filename=self.filename,
                               encoding=encoding)
        stream = []

        for kind, data, pos in source:

            if kind is TEXT:
                for kind, data, pos in interpolate(data, self.filepath, pos[1],
                                                   pos[2], lookup=self.lookup):
                    stream.append((kind, data, pos))

            elif kind is PI and data[0] == 'python':
                if not self.allow_exec:
                    raise TemplateSyntaxError('Python code blocks not allowed',
                                              self.filepath, *pos[1:])
                try:
                    suite = Suite(data[1], self.filepath, pos[1],
                                  lookup=self.lookup)
                except SyntaxError, err:
                    raise TemplateSyntaxError(err, self.filepath,
                                              pos[1] + (err.lineno or 1) - 1,
                                              pos[2] + (err.offset or 0))
                stream.append((EXEC, suite, pos))

            elif kind is COMMENT:
                if not data.lstrip().startswith('!'):
                    stream.append((kind, data, pos))

            else:
                stream.append((kind, data, pos))

        return stream

    def _extract_directives(self, stream, namespace, factory):
        depth = 0
        dirmap = {} # temporary mapping of directives to elements
        new_stream = []
        ns_prefix = {} # namespace prefixes in use

        for kind, data, pos in stream:

            if kind is START:
                tag, attrs = data
                directives = []
                strip = False

                if tag.namespace == namespace:
                    cls = factory.get_directive(tag.localname)
                    if cls is None:
                        raise BadDirectiveError(tag.localname,
                                                self.filepath, pos[1])
                    args = dict([(name.localname, value) for name, value
                                 in attrs if not name.namespace])
                    directives.append((factory.get_directive_index(cls), cls,
                                       args, ns_prefix.copy(), pos))
                    strip = True

                new_attrs = []
                for name, value in attrs:
                    if name.namespace == namespace:
                        cls = factory.get_directive(name.localname)
                        if cls is None:
                            raise BadDirectiveError(name.localname,
                                                    self.filepath, pos[1])
                        if type(value) is list and len(value) == 1:
                            value = value[0][1]
                        directives.append((factory.get_directive_index(cls),
                                           cls, value, ns_prefix.copy(), pos))
                    else:
                        new_attrs.append((name, value))
                new_attrs = Attrs(new_attrs)

                if directives:
                    directives.sort()
                    dirmap[(depth, tag)] = (directives, len(new_stream),
                                            strip)

                new_stream.append((kind, (tag, new_attrs), pos))
                depth += 1

            elif kind is END:
                depth -= 1
                new_stream.append((kind, data, pos))

                # If there have have directive attributes with the
                # corresponding start tag, move the events inbetween into
                # a "subprogram"
                if (depth, data) in dirmap:
                    directives, offset, strip = dirmap.pop((depth, data))
                    substream = new_stream[offset:]
                    if strip:
                        substream = substream[1:-1]
                    new_stream[offset:] = [
                        (SUB, (directives, substream), pos)
                    ]

            elif kind is SUB:
                directives, substream = data
                substream = self._extract_directives(substream, namespace,
                                                     factory)

                if len(substream) == 1 and substream[0][0] is SUB:
                    added_directives, substream = substream[0][1]
                    directives += added_directives

                new_stream.append((kind, (directives, substream), pos))

            elif kind is START_NS:
                # Strip out the namespace declaration for template
                # directives
                prefix, uri = data
                ns_prefix[prefix] = uri
                if uri != namespace:
                    new_stream.append((kind, data, pos))

            elif kind is END_NS:
                uri = ns_prefix.pop(data, None)
                if uri and uri != namespace:
                    new_stream.append((kind, data, pos))

            else:
                new_stream.append((kind, data, pos))

        return new_stream

    def _extract_includes(self, stream):
        streams = [[]] # stacked lists of events of the "compiled" template
        prefixes = {}
        fallbacks = []
        includes = []
        xinclude_ns = Namespace(self.XINCLUDE_NAMESPACE)

        for kind, data, pos in stream:
            stream = streams[-1]

            if kind is START:
                # Record any directive attributes in start tags
                tag, attrs = data
                if tag in xinclude_ns:
                    if tag.localname == 'include':
                        include_href = attrs.get('href')
                        if not include_href:
                            raise TemplateSyntaxError('Include misses required '
                                                      'attribute "href"',
                                                      self.filepath, *pos[1:])
                        includes.append((include_href, attrs.get('parse')))
                        streams.append([])
                    elif tag.localname == 'fallback':
                        streams.append([])
                        fallbacks.append(streams[-1])
                else:
                    stream.append((kind, (tag, attrs), pos))

            elif kind is END:
                if fallbacks and data == xinclude_ns['fallback']:
                    assert streams.pop() is fallbacks[-1]
                elif data == xinclude_ns['include']:
                    fallback = None
                    if len(fallbacks) == len(includes):
                        fallback = fallbacks.pop()
                    streams.pop() # discard anything between the include tags
                                  # and the fallback element
                    stream = streams[-1]
                    href, parse = includes.pop()
                    try:
                        cls = {
                            'xml': MarkupTemplate,
                            'text': NewTextTemplate
                        }.get(parse) or self.__class__
                    except KeyError:
                        raise TemplateSyntaxError('Invalid value for "parse" '
                                                  'attribute of include',
                                                  self.filepath, *pos[1:])
                    stream.append((INCLUDE, (href, cls, fallback), pos))
                else:
                    stream.append((kind, data, pos))

            elif kind is START_NS and data[1] == xinclude_ns:
                # Strip out the XInclude namespace
                prefixes[data[0]] = data[1]

            elif kind is END_NS and data in prefixes:
                prefixes.pop(data)

            else:
                stream.append((kind, data, pos))

        assert len(streams) == 1
        return streams[0]

    def _interpolate_attrs(self, stream):
        for kind, data, pos in stream:

            if kind is START:
                # Record any directive attributes in start tags
                tag, attrs = data
                new_attrs = []
                for name, value in attrs:
                    if value:
                        value = list(interpolate(value, self.filepath, pos[1],
                                                 pos[2], lookup=self.lookup))
                        if len(value) == 1 and value[0][0] is TEXT:
                            value = value[0][1]
                    new_attrs.append((name, value))
                data = tag, Attrs(new_attrs)

            yield kind, data, pos

    def _prepare(self, stream):
        return Template._prepare(self,
            self._extract_includes(self._interpolate_attrs(stream))
        )

    def add_directives(self, namespace, factory):
        """Register a custom `DirectiveFactory` for a given namespace.
        
        :param namespace: the namespace URI
        :type namespace: `basestring`
        :param factory: the directive factory to register
        :type factory: `DirectiveFactory`
        :since: version 0.6
        """
        assert not self._prepared, 'Too late for adding directives, ' \
                                   'template already prepared'
        self._stream = self._extract_directives(self._stream, namespace,
                                                factory)

    def _match(self, stream, ctxt, start=0, end=None, **vars):
        """Internal stream filter that applies any defined match templates
        to the stream.
        """
        match_templates = ctxt._match_templates

        tail = []
        def _strip(stream, append=tail.append):
            depth = 1
            next = stream.next
            while 1:
                event = next()
                if event[0] is START:
                    depth += 1
                elif event[0] is END:
                    depth -= 1
                if depth > 0:
                    yield event
                else:
                    append(event)
                    break

        for event in stream:

            # We (currently) only care about start and end events for matching
            # We might care about namespace events in the future, though
            if not match_templates or (event[0] is not START and
                                       event[0] is not END):
                yield event
                continue

            for idx, (test, path, template, hints, namespaces, directives) \
                    in enumerate(match_templates):
                if idx < start or end is not None and idx >= end:
                    continue

                if test(event, namespaces, ctxt) is True:
                    if 'match_once' in hints:
                        del match_templates[idx]
                        idx -= 1

                    # Let the remaining match templates know about the event so
                    # they get a chance to update their internal state
                    for test in [mt[0] for mt in match_templates[idx + 1:]]:
                        test(event, namespaces, ctxt, updateonly=True)

                    # Consume and store all events until an end event
                    # corresponding to this start event is encountered
                    pre_end = idx + 1
                    if 'match_once' not in hints and 'not_recursive' in hints:
                        pre_end -= 1
                    inner = _strip(stream)
                    if pre_end > 0:
                        inner = self._match(inner, ctxt, start=start,
                                            end=pre_end, **vars)
                    content = self._include(chain([event], inner, tail), ctxt)
                    if 'not_buffered' not in hints:
                        content = list(content)
                    content = Stream(content)

                    # Make the select() function available in the body of the
                    # match template
                    selected = [False]
                    def select(path):
                        selected[0] = True
                        return content.select(path, namespaces, ctxt)
                    vars = dict(select=select)

                    # Recursively process the output
                    template = _apply_directives(template, directives, ctxt,
                                                 vars)
                    for event in self._match(self._flatten(template, ctxt,
                                                           **vars),
                                             ctxt, start=idx + 1, **vars):
                        yield event

                    # If the match template did not actually call select to
                    # consume the matched stream, the original events need to
                    # be consumed here or they'll get appended to the output
                    if not selected[0]:
                        for event in content:
                            pass

                    # Let the remaining match templates know about the last
                    # event in the matched content, so they can update their
                    # internal state accordingly
                    for test in [mt[0] for mt in match_templates[idx + 1:]]:
                        test(tail[0], namespaces, ctxt, updateonly=True)

                    break

            else: # no matches
                yield event
