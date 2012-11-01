"""An extension to Python Markdown that uses smartypants to provide
typographically nicer ("curly") quotes, proper ("em" and "en") dashes, etc.
"""

from markdown.postprocessors import Postprocessor
from markdown.extensions import Extension
import spants
from spants import smartyPants   # local version of smartypants
from namedentities import named_entities


# Monkeypatch the base smartypants module to add the style tag to the list
# of tags not delved into. This fix has been suggested to the smartypants
# author and package maintainer. But until they update it, there's monkey
# patching.
import re

spants.tags_to_skip_regex = re.compile(r"<(/)?(pre|code|kbd|script|style|math)[^>]*>", re.I)

class SmartypantsPost(Postprocessor):
    
    def run(self, text):
        return named_entities(smartyPants(text))

class SmartypantsExt(Extension):
    
    def extendMarkdown(self, md, md_globals):
        md.postprocessors.add('smartypants', SmartypantsPost(md), '_end')

def makeExtension(configs=None):
    return SmartypantsExt(configs=configs)
