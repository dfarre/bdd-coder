def indent(text, tabs=1):
    newspace = ' '*4*tabs
    text = text.replace('\n', '\n' + newspace)

    return newspace + text


def make_doc(*lines):
    text = '\n'.join(line.strip() for line in lines)

    return f'"""\n{text}\n"""'


def decorate(target, decorators):
    return '\n'.join([f'@{decorator}' for decorator in decorators] + [target])


def make_class_head(name, *doc_lines, inheritance='', decorators=()):
    doc = '\n' + indent(make_doc(*doc_lines)) if doc_lines else ''

    return '\n\n' + decorate(f'class {name}{inheritance}:{doc}', decorators)


def make_method(name, body='pass', decorators=()):
    return '\n' + indent(decorate(
        f'def {name}(self, *args, **kwargs):\n{indent(body)}', decorators))
