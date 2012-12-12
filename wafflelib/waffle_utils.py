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


## EOF ##
