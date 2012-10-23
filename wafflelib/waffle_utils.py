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
from waflib.Utils import subprocess

def exec_command(self, cmd, **kw):
    """this overrides the 'waf -v' debug output to be in a nice
    unix like format instead of a python list.
    Thanks to ita on #waf for this
    """
    subprocess = waflib.Utils.subprocess
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
def _get_env_for_subproc(self):
    import os
    #env = dict(os.environ)
    #waf_env = dict(self.env)
    #for k,v in waf_env.items():
    env = dict(self.env)
    for k,v in env.items():
        v = self.env[k]
        #print("-- %s %s %r" % (k, type(k), v))
        if isinstance(v, (list,tuple)):
            v = list(v)
            for i,_ in enumerate(v):
                if hasattr(v[i], 'abspath'):
                    v[i] = v[i].abspath()
                else:
                    v[i] = str(v[i])
                    pass
                pass
            # handle xyzPATH variables (LD_LIBRARY_PATH, PYTHONPATH,...)
            if k.lower().endswith('path'):
                #print (">>> %s: %r" % (k,v))
                env[k] = os.pathsep.join(v)
            else:
                env[k] = ' '.join(v)
        else:
            env[k] = str(v)
    bld_area = self.env['BUILD_INSTALL_AREA']

    env['LD_LIBRARY_PATH'] = os.pathsep.join(
        [os.path.join(bld_area,'lib')]
        +waflib.Utils.to_list(self.env['LD_LIBRARY_PATH'])
        +[os.environ.get('LD_LIBRARY_PATH','')])

    env['PATH'] = os.pathsep.join(
        [os.path.join(bld_area,'bin')]
        +waflib.Utils.to_list(self.env['PATH'])
        +[os.environ.get('PATH','')])

    if _is_darwin(self):
        env['DYLD_LIBRARY_PATH'] = os.pathsep.join(
            [os.path.join(bld_area,'lib')]
            +waflib.Utils.to_list(self.env['DYLD_LIBRARY_PATH'])
            +[os.environ.get('DYLD_LIBRARY_PATH','')])
        pass
    
    for k in ('CPPFLAGS',
              'CFLAGS',
              'CCFLAGS',
              'CXXFLAGS',
              'FCFLAGS',

              'LINKFLAGS',
              'SHLINKFLAGS',

              'AR',
              'ARFLAGS',

              'CC',
              'CXX',

              ):
        v = self.env.get_flat(k)
        env[k] = str(v)
        pass

    env['SHLINKFLAGS'] += ' '+self.env.get_flat('LINKFLAGS_cshlib')
    env['SHEXT'] = _dso_ext(self)[1:]
    return env


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

## EOF ##
