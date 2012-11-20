# -*- python -*-
# a few waf functions to help building gaudi and athena
# a possible CMT replacement
# -- general utils for waffle
#

### imports -------------------------------------------------------------------
# stdlib imports ---
import sys
import platform

# waf imports ---
import waflib.Build
import waflib.Logs
import waflib.Logs as msg
import waflib.Utils

# waffle imports
import waflib.extras.waffle_subprocess as subprocess


def exec_command(self, cmd, **kw):
    """this overrides the 'waf -v' debug output to be in a nice
    unix like format instead of a python list.
    Thanks to ita on #waf for this
    """
    kw['shell'] = isinstance(cmd, str)
    _cmd = cmd    
    if isinstance(cmd, (list,tuple)):
        _cmd = ' '.join(cmd)
    msg.debug('runner: %s' % _cmd)
    msg.debug('runner_env: kw=%s' % kw)
    try:
        if self.logger:
            self.logger.info(cmd)
            kw['stdout'] = kw['stderr'] = subprocess.PIPE
            p = subprocess.Popen(cmd, **kw)
            (out, err) = p.communicate()
            if out:
                self.logger.debug('out: %s' % out.decode(sys.stdout.encoding or 'iso8859-1'))
            if err:
                self.logger.error('err: %s' % err.decode(sys.stdout.encoding or 'iso8859-1'))
            return p.returncode
        else:
            p = subprocess.Popen(cmd, **kw)
            return p.wait()
    except OSError:
        return -1
waflib.Build.BuildContext.exec_command = exec_command


### ---------------------------------------------------------------------------
def _is_dbg(ctx):
    return '-dbg' in ctx.env.CMTCFG
def _is_opt(ctx):
    return '-opt' in ctx.env.CMTCFG
def _is_64b(ctx):
    return 'x86_64' in ctx.env.CMTCFG
def _is_32b(ctx):
    return not _is_64b(ctx)#'i686' in ctx.env.CMTCFG

def _is_host_64b(ctx):
    #system, node, release, version, machine, processor = platform.uname()
    #return machine == 'x86_64'
    return '64bit' in platform.architecture()

def _is_host_32b(ctx):
    return not _is_host_64b(ctx)

def _is_linux(ctx):
    return 'linux' in sys.platform

def _is_darwin(ctx):
    return 'darwin' in sys.platform

def _is_windows(ctx):
    return waflib.Utils.is_win32
    #return 'win' in sys.platform

def _dso_ext(ctx):
    if _is_linux(ctx):
        return '.so'
    elif _is_darwin(ctx):
        #return '.dylib'
        return '.so'
    elif _is_windows(ctx):
        return '.dll'
    else:
        raise RuntimeError('unhandled platform [%s]' % sys.platform)
    
### ---------------------------------------------------------------------------
def _get_env_for_subproc(self, os_env_keys=None):
    ctx = self
    if not hasattr(ctx, "_get_env_for_subproc"):
        ctx = ctx.generator.bld
    return ctx._get_env_for_subproc(os_env_keys)

### ---------------------------------------------------------------------------
def copy_uselib_defs(ctx, dst, src):
    for n in ('LIB', 'LIBPATH',
              'STLIB', 'STLIBPATH',
              'LINKFLAGS', 'RPATH',
              'CFLAGS', 'CXXFLAGS',
              'DFLAGS',
              'INCLUDES',
              'CXXDEPS', 'CCDEPS', 'LINKDEPS',
              'DEFINES',
              'FRAMEWORK', 'FRAMEWORKPATH',
              'ARCH'):
        ctx.env['%s_%s' % (n,dst)] = ctx.env['%s_%s' % (n,src)]
    ctx.env.append_unique('DEFINES', 'HAVE_%s=1' % dst.upper())
    return

### ---------------------------------------------------------------------------
def define_uselib(ctx, name, libpath, libname, incpath, incname):
    """
    define_uselib creates the proper uselib variables based on the ``name``
    with the correct library-path ``libpath``, library name ``libname``,
    include-path ``incpath`` and header file ``incname``
    """
    n = name
    if libpath:
        libpath = waflib.Utils.to_list(libpath)
        ctx.env['LIBPATH_%s'%n] = libpath
        pass

    if libname:
        libname = waflib.Utils.to_list(libname)
        ctx.env['LIB_%s'%n] = libname
        pass
    
    if incpath:
        incpath = waflib.Utils.to_list(incpath)
        ctx.env['INCLUDES_%s'%n] = incpath
        pass

    ctx.env.append_unique('DEFINES', 'HAVE_%s=1' % name.upper())
    return

## EOF ##
