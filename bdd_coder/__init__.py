"""Common utils"""

import re


def get_step_sentence(step_text):
    return step_text.strip().split(maxsplit=1)[1].strip()


def sentence_to_name(text):
    return re.sub(r'[\'`]|".+"', '', text).lower().replace(' ', '_')


def get_step_specs(lines, steps_map=None):
    sentences = list(map(get_step_sentence, filter(None, map(str.strip, lines))))
    input_lists = map(lambda s: re.findall(r'"(.+)"', s), sentences)
    output_name_lists = map(lambda s: re.findall(r'`(\w+)`', s), sentences)
    steps_map = steps_map or {}
    method_names = map(lambda n: steps_map.get(n, n), map(sentence_to_name, sentences))

    return tuple(zip(method_names, input_lists, output_name_lists))
