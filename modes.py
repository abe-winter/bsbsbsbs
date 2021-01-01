"modes.py -- mode-switching logic"

import collections

Link = collections.namedtuple('Link', 'latch state')

class ModeState:
    def __init__(self):
        assert self.graph
        self.stack = [self.initial_state]

    def state(self):
        return self.stack[-1]

    def tick(self):
        "if link was a shift instead of a latch, return to base"
        if len(self.stack) > 1:
            self.stack.pop()

    def command(self, codepoint):
        link = self.graph[codepoint]
        if link.latch:
            self.stack[-1] = link.state
        else:
            self.stack.append(link.state)

class MainState(ModeState):
    graph = {
        900: Link(True, 'text'),
        901: Link(True, 'byte'),
        902: Link(True, 'num'),
        913: Link(False, 'byte'), # todo: illegal from num mode
        924: Link(True, 'byte'), # something special about 924 but I haven't read the manual
    }
    initial_state = 'text'

class TextState(ModeState):
    graph = {
        # note: don't really need a table, there's a pattern
        # todo: some transitions are illegal
        'll': Link(True, 'lower'),
        'ps': Link(False, 'punc'),
        'ml': Link(True, 'mixed'),
        'as': Link(False, 'alpha'),
        'al': Link(True, 'alpha'),
        'pl': Link(True, 'punc'),
    }
    initial_state = 'alpha'
