# waffle_basepolicy.py
# a few waf functions to define compilation defaults

# imports ---------------------------------------------------------------------
# stdlib imports ---
import os
import os.path

# waf imports ---
import waflib.Logs
import waflib.Utils
import waflib.Configure
import waflib.Build
import waflib.Task
import waflib.Tools.ccroot
from waflib.Configure import conf
from waflib.TaskGen import feature, before_method, after_method, extension, after

import waflib.Logs as msg

# waffle imports
import waflib.extras.waffle_utils as waffle_utils
import waflib.extras.waffle_subprocess as subprocess

# functions -------------------------------------------------------------------
@conf
def configure(ctx):
    waflib.Logs.debug('basepolicy detected')
    ctx.load('c_config')
    ctx.load('compiler_cc')
    ctx.load('compiler_cxx')
    #ctx.load('compiler_fc')
    #ctx.load('python')

    #ctx.check_fortran()

    return
    
@conf
def error_handler(fct, exc):
    msg.warn ("-- handling error [%r]" % (exc,))
    msg.warn ("--   fct: %r" % (fct,))
    return waflib.Configure.BREAK


### ---------------------------------------------------------------------------

#class MakefileDumper(waflib.Build.BuildContext):
#    fun = 'dump_makefile'
#    cmd = 'dump-makefile'
#    pass

def dump_makefile(ctx):
    # call the build function as if a real build were performed
    #build(ctx)

    ctx.commands = []
    ctx.targets  = []

    # store the executed command
    old_exec = waflib.Task.TaskBase.exec_command
    def exec_command(self, *k, **kw):
        ret = old_exec(self, *k, **kw)
        self.command_executed = k[0]
        self.path = kw['cwd'] or self.generator.bld.cwd
        return ret
    waflib.Task.TaskBase.exec_command = exec_command

    # perform a fake build, and accumulate the makefile bits
    old_process = waflib.Task.TaskBase.process
    def process(self):
        old_process(self)

        lst = []
        for x in self.outputs:
            lst.append(x.path_from(self.generator.bld.bldnode))
        bld.targets.extend(lst)

        lst.append(':')
        for x in \
                self.inputs + \
                self.dep_nodes + \
                self.generator.bld.node_deps.get(self.uid(), []):
            lst.append(x.path_from(self.generator.bld.bldnode))
        try:
            if isinstance(self.command_executed, list):
                self.command_executed = ' '.join(self.command_executed)
        except Exception:
            msg.error('*** error during makefile generation ***')
        else:
            ctx.commands.append(' '.join(lst))
            ctx.commands.append('\tcd %s && %s' %
                                (self.path, self.command_executed))
        return
    waflib.Task.TaskBase.process = process

    # write the makefile after the build is complete
    def output_makefile(self):
        self.commands.insert(0, "all: %s" % ' '.join(self.targets))
        node = self.bldnode.make_node('Makefile')
        node.write('\n'.join(self.commands))
        msg.warn('Wrote %s' % node.abspath())
    ctx.add_post_fun(output_makefile)

waflib.Build.BuildContext.dump_makefile = dump_makefile
    
