"""Namedentities workhorse for Python 3."""

from html.entities import codepoint2name, name2codepoint
import re
import codecs

def unescape(text):
    """
    Convert from HTML entities (named or numeric) to Unicode characters.
    """
    
    def fixup(m):
        """
        Given an HTML entity (named or numeric), return its Unicode
        equivalent. Does not, however, unescape &lt; &gt; and &amp; (decimal 60,
        62, and 38). Those are 'special' in that they are often escaped for very
        important, specific reasons (e.g. to describe HTML within HTML). Any
        messing with them is likely to break things badly.
        """
        
        text = m.group(0)
        if text[:2] == "&#":            # numeric entity
            try:
                codepoint = int(text[3:-1], 16) if text[:3] == "&#x" else int(text[2:-1])
                if codepoint != 38 and codepoint != 60 and codepoint != 62:
                    return chr(codepoint)
            except ValueError:
                pass
        else:                           # named entity
            try:
                codepoint = name2codepoint[text[1:-1]]
                if codepoint != 38 and codepoint != 60 and codepoint != 62:
                    return chr(codepoint)
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)
    
    
def named_entities_codec(text):
    """
    Encode codec that converts Unicode characters into named entities (where
    the names are known), or failing that, numerical entities.
    """
    
    if isinstance(text, (UnicodeEncodeError, UnicodeTranslateError)):
        s = []
        for c in text.object[text.start:text.end]:
            if ord(c) in codepoint2name:
                s.append('&{};'.format(codepoint2name[ord(c)]))
            else:
                s.append('&#{};'.format(ord(c)))
        return ''.join(s), text.end
    else:
        raise TypeError("Can't handle {}".format(text.__name__))


codecs.register_error('named_entities', named_entities_codec)
    

def named_entities(text):
    """
    Given a string, convert its numerical HTML entities to named HTML
    entities. Works by converting the entire string to Unicode characters, then
    re-encoding Unicode characters into named entities (where the names are
    known), or failing that, numerical entities.
    """
    
    unescaped_text = unescape(text)
    entities_text = unescaped_text.encode('ascii', 'named_entities')
    return entities_text.decode("ascii", "strict")
    
    
def encode_ampersands(text):
    """
    Encode ampersands into &amp;
    """
    
    text = re.sub('&(?!([a-zA-Z0-9]+|#[0-9]+|#x[0-9a-fA-F]+);)', '&amp;', text)
    return text

