class MarkupRenderer(object):
    @classmethod
    def is_enabled(cls, filename, lang):
        return False

    def render(self, text):
        raise NotImplementedError()


def renderer(renderer_type):
    renderer_type.IS_VALID_RENDERER__ = True
    return renderer_type
