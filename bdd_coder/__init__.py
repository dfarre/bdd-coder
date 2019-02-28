"""Common utils and constants"""

import re

LOGS_DIR_NAME = '.bdd-run-logs'
SUCCESS_MSG = '▌ All scenarios ran successfully! ✅'


def get_step_sentence(step_text):
    return step_text.strip().split(maxsplit=1)[1].strip()


def sentence_to_name(text):
    return re.sub(r'[\'`]|"[\w\-\.]+"', '', text).lower().replace(' ', '_')


def strip_lines(lines):
    return list(filter(None, map(str.strip, lines)))


def get_step_specs(lines, aliases=None):
    sentences = list(map(get_step_sentence, strip_lines(lines)))
    input_lists = map(lambda s: re.findall(r'"([\w\-\.]+)"', s), sentences)
    output_name_lists = map(lambda s: re.findall(r'`([\w\-\.]+)`', s), sentences)
    aliases = aliases or {}
    method_names = map(lambda n: aliases.get(n, n), map(sentence_to_name, sentences))

    return list(map(list, zip(method_names, input_lists, output_name_lists)))


class BaseRepr:
    def __str__(self):
        raise NotImplementedError

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self}>'
