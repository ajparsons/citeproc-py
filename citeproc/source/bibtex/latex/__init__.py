
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from citeproc.py2compat import *


import unicodedata

from collections import namedtuple
from warnings import warn


__all__ = ['parse_latex', 'substitute_ligatures']


def parse_latex(string, macros={}):
    tokens = Tokenizer(string)
    output = ''
    for result in dispatch(tokens, macros):
        output += result
    return substitute_ligatures(output)


Token = namedtuple('Token', ['type', 'value'])


TOGGLE_MATH = 'TOGGLE-MATH'
WHITESPACE = 'WHITESPACE'
CLOSE_SCOPE = 'CLOSE-SCOPE'
OPEN_SCOPE = 'OPEN-SCOPE'
START_MACRO = 'START-MACRO'
CHARACTER = 'CHARACTER'


class Tokenizer(object):
    def __init__(self, string):
        self.string = string
        self._tokens = self.tokenize(string)
        self._next_token = None

    @staticmethod
    def tokenize(input_string):
        for char in input_string:
            if char == '\\':
                yield Token(START_MACRO, char)
            elif char == '{':
                yield Token(OPEN_SCOPE, char)
            elif char == '}':
                yield Token(CLOSE_SCOPE, char)
            elif char in ' \t\n':
                yield Token(WHITESPACE, char)
            elif char == '$':
                yield Token(TOGGLE_MATH, char)
            else:
                yield Token(CHARACTER, char)

    def __iter__(self):
        return self

    def __next__(self):
        if self._next_token:
            token = self._next_token
            self._next_token = None
        else:
            try:
                token = next(self._tokens)
            except StopIteration:
                return
        return token

    next = __next__

    def peek(self):
        if self._next_token is None:
            try:
                self._next_token = next(self._tokens)
            except StopIteration:
                return None
        return self._next_token


def eat_whitespace(tokens):
    next_obj = tokens.peek()
    while next_obj and next_obj.type == WHITESPACE:
        next(tokens)


class ScopeClosing(Exception):
    pass


def dispatch(tokens, macros, level=0):
    while True:
        next_token = tokens.peek()
        if next_token is None:
            if level > 0:
                warn("Unbalanced parenthesis in '{}'".format(tokens.string))
            break
        elif next_token.type == OPEN_SCOPE:
            yield handle_scope(tokens, macros, level)
        elif next_token.type == CLOSE_SCOPE:
            raise ScopeClosing
        elif next_token.type == START_MACRO:
            yield handle_macro(tokens, macros)
        elif next_token.type == TOGGLE_MATH:
            yield handle_math(tokens)
        else:
            assert next_token.type in (CHARACTER, WHITESPACE)
            try:
                yield next(tokens).value
            except StopIteration:
                return



def handle_scope(tokens, macros, level):
    assert next(tokens).type == OPEN_SCOPE
    output = ''
    try:
        for result in dispatch(tokens, macros, level + 1):
            output += result
    except ScopeClosing:
        assert next(tokens).type == CLOSE_SCOPE
    return output


def parse_argument(tokens, macros, level=0):
    eat_whitespace(tokens)
    return next(dispatch(tokens, macros, level))


def handle_macro(tokens, macros):
    assert next(tokens).type == START_MACRO
    name = parse_macro_name(tokens).strip()
    try:
        macro = MACROS[name]
    except KeyError:
        macro = macros[name]
    return macro.parse_arguments_and_expand(tokens, macros)


def parse_macro_name(tokens):
    token = next(tokens)
    assert token.type in (CHARACTER, TOGGLE_MATH, WHITESPACE)
    name = token.value
    if name.isalpha():
        next_obj = tokens.peek()
        while next_obj and next_obj.type == CHARACTER and next_obj.value.isalpha():
            try:
                next_obj = next(tokens)
            except StopIteration:
                next_obj = None
            if next_obj:
                name += next_obj.value
        eat_whitespace(tokens)
    return name


def handle_math(tokens):
    assert next(tokens).type == TOGGLE_MATH
    output = ''
    for token in tokens:
        if token.type == START_MACRO:
            output += token.value
            token = next(tokens)
        elif token.type == TOGGLE_MATH:
            break
        output += token.value
    return '$' + output + '$'


def substitute_ligatures(string):
    for chars, ligature in SUBSTITUTIONS.items():
        string = string.replace(chars, unicodedata.lookup(ligature))
    return string


SUBSTITUTIONS = {"~": 'NO-BREAK SPACE',

                 # ligatures defined in Computer Modern (symbol shortcuts)
                 "--": 'EN DASH',
                 "---": 'EM DASH',
                 "''": 'RIGHT DOUBLE QUOTATION MARK',
                 "``": 'LEFT DOUBLE QUOTATION MARK',
                 "!`": 'INVERTED EXCLAMATION MARK',
                 "?`": 'INVERTED QUESTION MARK',
                 ",,": 'DOUBLE LOW-9 QUOTATION MARK',
                 "<<": 'LEFT-POINTING DOUBLE ANGLE QUOTATION MARK',
                 ">>": 'RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK',
}


from .macro import MACROS
