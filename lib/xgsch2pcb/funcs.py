# -*-Python-*-

# xgsch2pcb - a GUI for gsch2pcb
# Copyright (C) 2006 University of Cambridge
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import subprocess, os, string, re

def find_tool_path (tool):

    p = subprocess.Popen(["which", tool], stdout=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if p.returncode:
        return None
    
    return stdout.strip()
    
def rel_path(topath, fromdir=""):

    sep = os.path.sep
    pardir = os.path.pardir

    # Expand paths:
    # "" becomes the current dir
    # /foo/../ sections are contracted
    fromdir = os.path.abspath( fromdir )
    topath = os.path.abspath( topath )

    if fromdir == topath:
        return ''

    # We need a directory separator at the end for consistency
    if not fromdir.endswith( sep ):
        fromdir = fromdir + sep

    # Compute the common prefix of the paths
    # Note, that this is done on a string basis:
    # /home and /homedir share a common prefix of /home
    prefix = os.path.commonprefix([fromdir, topath])
    
    # If the topath doesn't have fromdir as a common part: 
    if (prefix != fromdir):

        # Go down one directory in the fromdir, and prepend
        # a relative move down one dir in the output string
        fromdir = os.path.abspath( fromdir + pardir )

        # Recurse down
        return pardir + sep + rel_path(fromdir, topath)
    
    # Return the topath without the common prefix
    return topath[len(prefix):]

def shell_parse (line):
    # FIXME: shlex.split could be used instead of this function.
    # Forcing shlex.split to follow POSIX is possible since Python 2.6
    r"""Parse shell command line according to POSIX rules.

    >>> shell_parse('')
    []

    >>> shell_parse(' \t ')
    []

    >>> shell_parse(' \  ')
    [' ']

    >>> shell_parse('abc def')
    ['abc', 'def']

    >>> shell_parse(' abc""d\'\'ef')
    ['abcdef']

    >>> shell_parse(' " \' " ')
    [" ' "]

    >>> shell_parse("'\\'")
    ['\\']

    >>> shell_parse("'")
    Traceback (most recent call last):
        ...
    ValueError: unmatched single quote

    >>> shell_parse('"')
    Traceback (most recent call last):
        ...
    ValueError: unmatched double quote

    >>> shell_parse('\\')
    Traceback (most recent call last):
        ...
    ValueError: unmatched escape character
    """

    parsed = []
    state = 'white'
    collect = ""
    escape = False
    C_SQUOTE = "'"
    C_DQUOTE = '"'
    C_BSLASH = '\\'

    for c in line:
        if escape:
            collect += c
            escape = False
        elif state == 'white':
            if c == C_SQUOTE:
                state = 'squote'
            elif c == C_DQUOTE:
                state = 'dquote'
            elif c == C_BSLASH:
                escape = True
                state = 'text'
            elif c not in string.whitespace:
                state = 'text'
                collect += c
        elif state == 'squote':
            if c == C_SQUOTE:
                state = 'text'
            else:
                collect += c
        elif state == 'dquote':
            if c == C_DQUOTE:
                state = 'text'
            elif c == C_BSLASH:
                escape = True
            else:
                collect += c
        elif state == 'text':
            if c == C_SQUOTE:
                state = 'squote'
            elif c == C_DQUOTE:
                state = 'dquote'
            elif c == C_BSLASH:
                escape = True
            elif c in string.whitespace:
                parsed.append (collect)
                collect = ""
                state = 'white'
            else:
                collect += c

    if escape:
        raise ValueError('unmatched escape character')
    elif state == 'text':
        parsed.append (collect)
    elif state == 'squote':
        raise ValueError('unmatched single quote')
    elif state == 'dquote':
        raise ValueError('unmatched double quote')
    return parsed

def shell_quote (line):
    """Quote string according to POSIX shell rules.

    >>> s = '"'; s == shell_parse(shell_quote(s))[0]
    True

    >>> s = "'"; s == shell_parse(shell_quote(s))[0]
    True

    >>> s = "test abc"; s == shell_parse(shell_quote(s))[0]
    True

    >>> s = ' ab " \\'c'; s == shell_parse(shell_quote(s))[0]
    True

    >>> shell_quote("abc")
    'abc'

    >>> shell_quote(" def ")
    '" def "'
    """

    toquote = '"\'\\'

    if any ([c in line for c in toquote + string.whitespace]):
        escaped = re.sub ("([%s])" % re.escape(toquote), r'\\\1', line)
        return '"%s"' % escaped
    else:
        return line

if __name__ == "__main__":
    import doctest
    doctest.testmod()
