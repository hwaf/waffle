# waffle_main.py
# a few waf functions for the main entry-point of waf

# imports ---------------------------------------------------------------------
import os
import os.path
import shutil

# waf imports
import waflib.Build
import waflib.ConfigSet
import waflib.Configure
import waflib.Context
import waflib.Errors
import waflib.Logs
import waflib.Logs as msg
import waflib.Task
import waflib.Utils

# waffle imports
#import waflib.extras.waffle
import waflib.extras.waffle_utils as waffle_utils

### ---------------------------------------------------------------------------
def start(cwd, version, wafdir):
    """
    This is the main entry point, all Waf execution starts here.

    :param cwd: absolute path representing the current directory
    :type cwd: string
    :param version: version number
    :type version: string
    :param wafdir: absolute path representing the directory of the waf library
    :type wafdir: string
    """
    import waflib.extras.compat15
    import waflib.Context
    import waflib.Logs
    import waflib.Scripting

    root_path = os.path.join(cwd, 'wscript')
    wafflelib_dir = os.path.dirname(waffle_utils.__file__)

    import sys
    sys.path += [os.path.dirname(wafflelib_dir)]

    waflib.Scripting.waf_entry_point(cwd, version, wafdir)
    return
