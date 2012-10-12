from OmniMarkupLib.RendererManager import *
import markdown2


@RendererManager.register
class MarkdownRenderer(MarkupRenderer):
    def is_enabled(self, filename, syntax):
        return syntax == "text.html.markdown"

    def render(self, text):
        return markdown2.markdown(
            text,
            extras=[
                'footnotes', 'toc', 'fenced-code-blocks', 'cuddled-lists',
                'code-friendly'
            ]
        )
