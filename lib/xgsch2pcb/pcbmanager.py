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

# TODO: Is this needed? What version of python do we depend on?
from __future__ import generators

import commands, shutil, re, gobject, os, sys

# i18n
import gettext
t = gettext.translation('xgsch2pcb', fallback=True)
_ = t.ugettext

# xgsch2pcb-specific modules
from stat import *
from subprocess import *
from funcs import *

# Define PCB action return codes
PCB_RC_OK      = 001
PCB_RC_ERROR   = 002

class PCBManager( gobject.GObject ):

    __gsignals__ = { "update-complete" :
                      ( 0,                        # No special flags
                        gobject.TYPE_NONE,        # Return type
                        (gobject.TYPE_BOOLEAN, )  # Pass a bool to signal
                       ) }
    
    def __init__(self, project):
        gobject.GObject.__init__(self)

        self.project = project
       
        # TODO: Need to think about whether these are relative or absolute paths
        self.project_dir = self.project.filename.rsplit('.', 1)[0]
        self.output_name = self.project.output_name

        self.pipes = None
        self.cofunc = None
        
        self.toolpath = find_tool_path( 'pcb' )
        self.gsch2pcbpath = find_tool_path( 'gsch2pcb' )

        if not (self.toolpath and self.gsch2pcbpath):
            exception_txt = ''
            if not self.toolpath:
                exception_txt = exception_txt + \
                    _("\nCouldn't find 'pcb' executable")
            if not self.gsch2pcbpath:
                exception_txt = exception_txt + \
                    _("\nCouldn't find 'gsch2pcb' executable")
            raise Exception, exception_txt



    def __del__(self):
       
        if self.pcb_stdin:
            self.pcb_stdin.close()

        if self.pcb_stdout:
            self.pcb_stdout.close()

        # TODO: Close pipe, kill PCB and call parent class del
        if not self.pipes == None:
            self.pipes == None

        # TODO: Do we need to call our parent's destructor?
        #gobject.GObject.__del__(self)

    def close_layout(self):

        # TODO: Fixme
        self.pcb_write( "Quit()\n" )
        
        # TODO: Block until the pipe dies, or timeout?
        pass

    def open_layout(self):
        
        if self.is_layout_open():
            # TODO: Is there some clever way to bring PCB to front?
            # Possibly send it an action which does a window-manager request?
            return
        
        pcbargs = (self.toolpath, '--listen', self.output_name + ".pcb" )
        self.pipes = Popen(pcbargs, stdin=PIPE, stdout=PIPE)
        self.pcb_stdout = self.pipes.stdout
        self.pcb_stdin = self.pipes.stdin
        
        # TODO: Wait until PCB confirms layout loaded
        
        ## Call fnctl to set non-blocking IO on the input stream
        #child_in = pcbpipe.stdout.fileno()
        #flags = fcntl.fcntl(child_in, fcntl.F_GETFL)
        #fcntl.fcntl(child_in, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        
        # Setup callback for data ready on PCB's stdout pipe
        self.parser = pcb_output_parser( self.pcb_stdout )
        self.parser.connect("return-code", self.parser_return_code_cb)
        self.parser.connect("pipe-died", self.parser_pipe_died_cb)

        assert self.is_layout_open()

    def is_layout_open(self):
       
        if self.pipes == None or self.pipes.poll() != None:
            return False

        # TODO: Check to see if the layout is actually open, not just pipe alive?
        return True

    def update_layout(self, schematics):

        # First check the layout is open
        if not self.is_layout_open():
            self.open_layout()

        if self.cofunc == None:
            self.cofunc = self.cofunction_update( schematics )
        else:
            print _("Already in the middle of an update")
            # TODO: Some further exception?
            return
        
        try:
            self.cofunc.next()
                
        except StopIteration:
            self.cofunc = None
    
        
    def needs_updating(self, schematics):
        
        # In the future, this could save the users currently active layout
        # and then check if it is complete (via gsch2pcb), thus not relying
        # on mtime.
        
        # If the PCB layout file doesn't exist, assume that it needs updating
        if not os.path.exists(self.output_name + ".pcb"):
            if len( schematics ) > 0:
                return True
            else:
                return False
        
        layout_mtime = os.stat(self.output_name + ".pcb")[ST_MTIME]

        schematic_mtime = layout_mtime
        for page in schematics:
            mtime = os.stat(page)[ST_MTIME]
            schematic_mtime = max(mtime, schematic_mtime)

        return (layout_mtime < schematic_mtime)

    def pcb_write( self, string ):
        self.pcb_stdin.write( string )
        print ">pcb<: ", string,

    def cofunction_update( self, schematics ):

        # NOTE TO HACKERS:
        #
        # This function (rightly or wrongly) is implemeted as a python generator.
        # It uses the generator function "yield", to return out of this function
        # whilst allowing re-entry at that point after a suitable signal is handled.
        #
        # After every yield statement, we should check the status-codes from the
        # parser class. This is done by calling self.parser.consume_retcode().
        #
        # For convenience, call "error_occurred()", which returns True if an error
        # condition was met.

        def error_occurred( ):
            retcode = self.parser.consume_retcode()
            error = False
            if retcode == None:
                error = True
                print _("error_occurred: no retcode from pcb parser")
            elif retcode == PCB_RC_ERROR:
                error = True
                print _("error_occurred: Error response, retcode=%s") % retcode
            return error

        def error_restore_backup():
            # Deliberatly leave (self.output_name + ".savedbackup.pcb") incase it is useful
            
            # Move original file backup to layout if it exists
            if os.path.exists(self.output_name + ".backup.pcb"):
                shutil.move(self.output_name + ".backup.pcb", self.output_name + ".pcb")

        def cleanup_files():

            # Move backup back to layout file if it exists
            try:
                shutil.move(self.output_name + ".backup.pcb", self.output_name + ".pcb")
            except:
                pass
            
            # Remove backup before gsch2pcb
            try:
                os.remove(self.output_name + ".savedbackup.pcb")
            except:
                pass
                
            # Clean up gsch2pcb's mess
            try:
                os.remove(self.output_name + ".tmp.gsch2pcb")
            except:
                pass

            try:
                os.remove(self.output_name + ".new.pcb")
            except:
                pass

            try:
                os.remove(self.output_name + ".cmd")
            except:
                pass


        print _("********START UPDATING********")
        
        # Send 'hello' to PCB
        self.pcb_write("Hello()\n")
        
        # Wait to re-enter with a response
        yield None

        if error_occurred():
            # PCB is not responding happily to its "Hello" action
            # TODO: ERROR MESSAGE TO THE USER
            return
            
        # TODO: TELL PCB TO IGNORE USER ACTIONS

        # Move current layout to backup if it exists
        if os.path.exists(self.output_name + ".pcb"):
            shutil.move(self.output_name + ".pcb", self.output_name + ".backup.pcb")
        
        # Save layout
        self.pcb_write("SaveTo(Layout, %s)\n" % (self.output_name + ".pcb"))
        
        # Wait to re-enter with a response
        yield None
        
        if error_occurred():
            error_restore_backup()
            # TODO: TELL PCB TO ALLOW USER ACTIONS
            # TODO: ERROR MESSAGE TO USER
            return

        # Copy saved layout to backup
        shutil.copy(self.output_name + ".pcb", self.output_name + ".savedbackup.pcb")
        
        # Create gsch2pcb project file
        self.project.save( self.output_name + ".tmp.gsch2pcb" )
        
        # Run gsch2pcb
        # TODO: Handle via Popen like other tools?
        gsch2pcb_cmd = self.gsch2pcbpath + " -q " + self.output_name + ".tmp.gsch2pcb"
        gsch2pcb_output = commands.getstatusoutput(gsch2pcb_cmd)
        lines = gsch2pcb_output[1].splitlines()
        for line in lines:
            print "<gsch2pcb>:", line

        # TODO: HANDLE ERROR OUTPUT FROM gsch2pcb!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        
        # Load layout
        self.pcb_write("LoadFrom(Revert, %s)\n" % (self.output_name + ".pcb"))
        
        # Wait to re-enter with a response
        yield None
        
        if error_occurred():
            error_restore_backup()
            # TODO: TELL PCB TO ALLOW USER ACTIONS
            # TODO: ERROR MESSAGE TO USER
            return
        
        # Delete rats
        self.pcb_write("DeleteRats(AllRats)\n")
        
        # Load netlist
        self.pcb_write("LoadFrom(Netlist, %s)\n" % (self.output_name + ".net"))

        # Wait to re-enter with a response
        yield None
        
        if error_occurred():
            # TODO: WARNING TO THE USER?
            pass
        
        # If new elements exist, put them in the paste-buffer
        newparts = self.output_name + ".new.pcb"
        if os.path.exists (newparts):
            self.pcb_write("LoadFrom(LayoutToBuffer, %s)\n" % newparts)
            
            # Wait to re-enter with a response
            yield None
            
            if error_occurred():
                # TODO: WARN USER?
                pass
       
            # Paste the new components near the origin
            self.pcb_write("PasteBuffer(ToLayout,10,10,mil)\n")
            
            # Change back to the "none" (select) tool
            self.pcb_write("Mode(None)\n")
        
        # Run the .cmd file
        self.pcb_write("ExecuteFile(%s)\n" % (self.output_name + ".cmd"))
        
        # Wait to re-enter with a response
        yield None
        
        if error_occurred():
            # TODO: WARN USER?
            pass
            
        # Add the rat-lines
        self.pcb_write("AddRats(AllRats)\n")
        
        # Move original layout backup back in place, delete intermediate files
        cleanup_files()

        print _("********DONE UPDATING********")
            
    
    def parser_return_code_cb( self, parser, retcode ):
     
        # If running, advance the function which is communicating with PCB

        if self.cofunc == None:
            # print _("Ignoring return code out of cofunc execution")
            return
            
        try:
            self.cofunc.next()
                
        except StopIteration:
            self.cofunc = None

    ## TODO: Use this timeout handler somewhere?
    #def pcb_timeout_cb( self ):
    #
    #    if self.cofunc == None:
    #        return True
    #
    #    try:
    #        self.cofunc.next()
    #
    #    except StopIteration:
    #        self.cofunc = None
    #
    #    ## OR, should we just:
    #    #self.parser_return_code_cb( self.parser, 'TIMEOUT' )
    #    ## as this gives a definate indication of re-entry cause


    def parser_pipe_died_cb( self, parser ):
        
        # Close the pipe
        self.pcb_stdin.close()
        self.pcb_stdin = None

        # Close the corresponding pipe outputting to PCB
        self.pcb_stdout.close()
        self.pcb_stdout = None

        # Close any remaining attachment to the process
        # TODO: Check there isn't an equivelant to "Pclose"
        self.pipes = None
            
gobject.type_register( PCBManager )

class pcb_output_parser(gobject.GObject):
    # Register signals which we may emit
    __gsignals__ = { "return-code": ( gobject.SIGNAL_NO_RECURSE,
                                      gobject.TYPE_NONE,
                                      (gobject.TYPE_INT, ) ),
                     "pipe-died": ( gobject.SIGNAL_NO_RECURSE,
                                      gobject.TYPE_NONE,
                                      () ) }
                                    

    def __init__(self, file):
        gobject.GObject.__init__(self)
        
        self.atnewline = True
        self.file = file

        # Hardcode these for now
        self.out_prefix = "<pcb>: "
        self.out_echo = True

        self.last_retcode = None

        # Compile a regular expression to get any numerical 
        # return code from a PCB output string
        self.retcode_re = re.compile( '([0-9]{3,3}) - ' )
        
        self.watch_handle = gobject.io_add_watch(self.file, 
                             gobject.IO_IN | gobject.IO_ERR | gobject.IO_HUP,
                             self.pcb_read_cb )
    
    def __del__(self):
        gobject.source_remove(self.watch_handle);
        gobject.GObject.__del__(self)
    
    def consume_retcode(self):
        retval = self.last_retcode
        self.last_retcode = None
        return retval
        
    def get_last_retcode(self):
        return self.last_retcode
        
    def pcb_read_cb (self, source, condition ):
        
        # Check if the connection has died
        if condition & gobject.IO_HUP:

            # Callback signal to inform the program
            self.emit( "pipe-died" );

            # Return False, so the io_watch will not re-run
            return False
        
        # Attempt reading from the pipe
        try:

            data = self.file.readline ()

        except IOError:

            print >> sys.stderr, _("pcb_read_cb: IOError whilst in readline()")

            # Callback signal to inform the program
            self.emit( "pipe-died" );

            # Return False, so the io_watch will not re-run
            return False
        
        if self.out_echo:
            print self.out_prefix, data,

        # TODO: Decide if we just want to signal directly with the line read from PCB?

        re_match = self.retcode_re.match( data )
        
        if re_match:
            self.last_retcode = int( re_match.group(1) )
            self.emit ( "return-code", self.last_retcode )
        
        return True

gobject.type_register( pcb_output_parser )
 
