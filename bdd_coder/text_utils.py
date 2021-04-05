def indent(text, tabs=1):
    newspace = ' '*4*tabs
    text = text.replace('\n', '\n' + newspace)

    return newspace + text


def make_doc(*lines):
    text = '\n'.join(line.strip() for line in lines)

    return f'"""\n{text}\n"""' if text else ''


def decorate(target, decorators):
    return '\n'.join([f'@{decorator}' for decorator in decorators] + [target])


def make_def_content(*doc_lines, body=''):
    return indent('\n'.join(([make_doc(*doc_lines)] if doc_lines else []) +
                            ([body] if body else []) or ['pass']))


def make_class_head(name, bases=(), decorators=()):
    inheritance = f'({", ".join(map(str.strip, bases))})' if bases else ''

    return decorate(f'class {name}{inheritance}', decorators)


def make_class(name, *doc_lines, bases=(), decorators=(), body=''):
    return '\n'.join([f'{make_class_head(name, bases, decorators)}:',
                      make_def_content(*doc_lines, body=body)])


def make_method(name, *doc_lines, args_text='', decorators=(), body=''):
    return '\n'.join([decorate(f'def {name}(self{args_text}):', decorators),
                      make_def_content(*doc_lines, body=body)])


def rstrip(text):
    return '\n'.join(list(map(str.rstrip, text.splitlines()))).lstrip('\n')
