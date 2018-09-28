#!/usr/bin/env python3

"""
Implementation of
https://github.com/hak5darren/USB-Rubber-Ducky/wiki/Duckyscript
"""
import os
import binascii
from typing import List

import parsimonious
from parsimonious.exceptions import ParseError, VisitationError

from ducky.hid import get_bytes
from ducky.exceptions import DuckyParseError



DUCKY_GRAMMAR = parsimonious.Grammar("""
# Based on the rules expressed here: https://github.com/hak5darren/USB-Rubber-Ducky/wiki/Duckyscript
# Command names
rem               = "REM"
delay             = "DELAY"
default_delay     = "DEFAULT_DELAY" / "DEFAULTDELAY"
repeat            = "REPEAT"
string            = "STRING" / "STR"

# Modifiers
alt               = "ALT"
ctrl              = "CTRL" / "CONTROL"
shift             = "SHIFT"
windows           = "GUI" / "WINDOWS" / "META" / "CMD" / "COMMAND"
menu              = "MENU" / "APP"

# Arrows
downarrow         = "DOWNARROW" / "DOWN"
leftarrow         = "LEFTARROW" / "LEFT"
rightarrow        = "RIGHTARROW" / "RIGHT"
uparrow           = "UPARROW" / "UP"
arrow             = downarrow / leftarrow / rightarrow / uparrow

# Special keys
break             = "BREAK" / "PAUSE"
capslock          = "CAPSLOCK"
delete            = "DELETE"
end               = "END"
esc               = "ESC" / "ESCAPE"
home              = "HOME"
insert            = "INSERT"
numlock           = "NUMLOCK"
pageup            = "PAGEUP"
pagedown          = "PAGEDOWN"
printscreen       = "PRINTSCREEN"
scrollock         = "SCROLLLOCK"
space             = "SPACE"
tab               = "TAB"
enter             = "ENTER"
fkey              =  "F12" / "F11" / "F10" / "F1" / "F2" / "F3" / "F4" / "F5" / "F6" / "F7" / "F8" / "F9"
special_key       = break / capslock / delete / end / esc / home / insert / numlock / pageup / pagedown / printscreen / scrollock / space / tab / enter / fkey

# Command parameters
string_data        = ~"[\w \!\@\#\$\%\^\&\*\(\)\`\~\+\=\_\-\\"\\'\:\;\<\>\.\,\?\\\\\|\/]+"
char              = ~"[\w]"
anything          = ~".*"
number            = ~"\d+"
#fkey              = ~"F\d{1,2}"
newline           = ~"(\\n|\\r\\n)+"
optional_spaces   =  ~"[\s\\t]*"
delimiter         = " "

# Commands
rem_cmd           = rem delimiter anything
default_delay_cmd = default_delay delimiter number
delay_cmd         = delay delimiter number
string_cmd        = string delimiter string_data
windows_cmd       = windows delimiter windows_cmd_param
windows_cmd_param = special_key /arrow / char
menu_cmd          = menu
shift_cmd         = shift delimiter shift_cmd_param
shift_cmd_param   = delete / home / insert / pageup / pageup / windows / windows / uparrow / downarrow / leftarrow / rightarrow / tab
alt_cmd           = alt delimiter alt_cmd_param
alt_cmd_param     = end / esc / fkey / space / tab / char
control_cmd       = ctrl delimiter control_cmd_param
control_cmd_param = special_key / arrow / break / fkey / esc / char
repeat_cmd        = repeat delimiter number
special_key_cmd   = special_key / arrow
cmd               = rem_cmd / default_delay_cmd / delay_cmd / string_cmd / windows_cmd / menu_cmd / shift_cmd / alt_cmd / control_cmd / repeat_cmd / special_key_cmd

# Entrypoint
line              = newline? cmd newline?
empty_line        = optional_spaces newline?
ducky_script      = line*
""")


class Command(object):

    def __init__(self, cmd: str, payload: bytes, delay: int=0):
        self.cmd = cmd
        self.payload = payload
        self.delay = delay

    def __repr__(self):
        return 'Command(cmd="{}", payload={}, delay={})'.format(
            self.cmd,
            self.payload,
            self.delay)
    
    def serialized_payload(self):
        formatted = None
        if self.payload:
            payload = binascii.hexlify(self.payload).decode('ascii')
            formatted = ''
            for i in range(0, len(payload)):
                if i > 0 and i % 16 == 0:
                    formatted += ' '
                formatted += payload[i]
        return formatted
    
    def serialized(self):
        return {
            'cmd': self.cmd,
            'delay': self.delay,
            'payload': self.serialized_payload(),
        }


def _find_child_by_name(node, name):
    for child in node.children:
        if child.expr_name == name:
            return child.text
    return None


class DuckyNodeVisitor(parsimonious.NodeVisitor):

    def __init__(self, commands: List[Command]):
        self.commands = commands
        self.default_delay = 0
        self.prev = None
    
    def generic_visit(self, node, visited_children):
        pass  # All the unimportant stuff like spaces and params

    def append(self, command):
        self.prev = command
        self.commands.append(command)

    def visit_string_cmd(self, cmd, *args, **kwargs):
        data = _find_child_by_name(cmd, 'string_data')
        byts = b''
        for ch in data:
            byts += get_bytes(ch)
        self.append(Command(cmd.text, byts, self.default_delay))
    
    def visit_default_delay_cmd(self, cmd, *args, **kwargs):
        data = _find_child_by_name(cmd, 'number')
        self.default_delay = int(data)
    
    def visit_delay_cmd(self, cmd, *args, **kwargs):
        data = _find_child_by_name(cmd, 'number')
        delay = int(data)
        self.append(Command(cmd.text, None, delay))
        
    def visit_repeat_cmd(self, cmd, *args, **kwargs):
        data = _find_child_by_name(cmd, 'number')
        times = int(data)
        if self.prev:
            for _ in range(0, times):
                self.commands.append(self.prev)
        self.prev = None
    
    def visit_windows_cmd(self, cmd, *args, **kwargs):
        ch = _find_child_by_name(cmd, 'windows_cmd_param')
        byts = get_bytes(ch, ['META'])
        self.append(Command(cmd.text, byts, self.default_delay))
    
    def visit_menu_cmd(self, cmd, *args, **kwargs):
        self.append(Command(cmd.text, get_bytes('PROPS'), self.default_delay))
        
    def visit_shift_cmd(self, cmd, *args, **kwargs):
        param = _find_child_by_name(cmd, 'shift_cmd_param')
        self.append(Command(cmd.text, get_bytes(param, ['SHIFT']), self.default_delay))
        
    def visit_alt_cmd(self, cmd, *args, **kwargs):
        param = _find_child_by_name(cmd, 'alt_cmd_param')
        self.append(Command(cmd.text, get_bytes(param, ['ALT']), self.default_delay))
    
    def visit_control_cmd(self, cmd, *args, **kwargs):
        param = _find_child_by_name(cmd, 'control_cmd_param')
        self.append(Command(cmd.text, get_bytes(param, ['CTRL']), self.default_delay))

    def visit_special_key_cmd(self, cmd, *args, **kwargs):
        self.append(Command(cmd.text, get_bytes(cmd.text), self.default_delay))


def parse(cmd: str) -> List[Command]:
    tree = None
    try:
        tree = DUCKY_GRAMMAR.get('ducky_script').parse(cmd)
    except ParseError as pe:
        raise DuckyParseError(pe)
    commands = []
    visitor = DuckyNodeVisitor(commands)
    try:
        visitor.visit(tree)  # Kick things off
    except VisitationError as ve:
        raise DuckyParseError(ve)
    return commands
