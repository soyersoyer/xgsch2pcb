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
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import commands
import os

def find_tool_path (tool):

    which = commands.getstatusoutput("which %s" % tool)
    if which[0]:
        return None
    
    return which[1]
    
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

