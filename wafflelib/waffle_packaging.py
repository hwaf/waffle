# -*- python -*-
# packaging.py
# a few waf functions to help packaging binaries and sources

# imports ---------------------------------------------------------------------
import os
import os.path
import shutil

# waf imports
import waflib.Build
import waflib.Errors
import waflib.Logs as msg
import waflib.Scripting
import waflib.Utils

# waffle imports
import waflib.extras.waffle
import waflib.extras.waffle_utils

### ---------------------------------------------------------------------------
class SDist(waflib.Scripting.Dist):
    '''creates an archive containing the project source code'''
    
    cmd = 'sdist'
    algo = 'tar.gz'

    def execute(self):
        '''runs hg|git archive to create an archive containing the project
        source code '''
        archive_name = self.get_arch_name()
        msg.info('creating archive [%s]...' % archive_name)
        ret = -1
        if self._is_hg_project():
            ret = waflib.Utils.subprocess.Popen([
                'hg', 'archive', '--subrepos',
                archive_name,
                ]).wait()
        elif self._is_git_project():
            p = waflib.Utils.subprocess.Popen(
                ['git', 'name-rev', '--name-only', 'HEAD'],
                stdout=waflib.Utils.subprocess.PIPE)
            o = p.communicate()
            if p.returncode:
                msg.fatal('could not determine git branch name:\n%s\n%s' %
                          o[0],o[1])
            git_object = o[0].strip()
            ret = waflib.Utils.subprocess.Popen([
                'git', 'archive', '-o', archive_name,
                git_object,
                ]).wait()
            pass
        else:
            msg.fatal('source files of project must be tracked by git or hg')
            pass
        if ret:
            raise waflib.Errors.WafError('sdist failed with code %s' % ret)
        msg.info('creating archive [%s]... [done]' % archive_name)
        return

    def _is_hg_project(self):
        dot_hg = self.path.find_dir(".hg")
        #print ".hg:",dot_hg
        return not (dot_hg is None)

    def _is_git_project(self):
        dot_git = self.path.find_dir(".git")
        #print ".git:",dot_git
        return not (dot_git is None)
        

    ## def get_base_name(self):
    ##     """
    ##     Return the default name of the main directory in the archive, which is set to *appname-version*.
    ##     Set the attribute *base_name* to change the default value::

    ##     def dist(ctx):
    ##         ctx.base_name = 'files'

    ##     :rtype: string
    ##     """
    ##     try:
    ##         self.base_name
    ##     except:
    ##         appname = getattr(Context.g_module, Context.APPNAME, 'noname')
    ##         version = getattr(Context.g_module, Context.VERSION, '1.0')
    ##         self.base_name = appname + '-' + version
    ##     return self.base_name
    
    pass # class SDist

### ---------------------------------------------------------------------------
class BDist(waffle.InstallContext):
    '''creates an archive containing the project binaries'''

    cmd = 'bdist'

    def init_dirs(self, *k, **kw):
        super(BDist, self).init_dirs(*k, **kw)
        self.tmp = self.bldnode.make_node('bdist_tmp_dir')
        try:
            shutil.rmtree(self.tmp.abspath())
        except:
            pass
        if os.path.exists(self.tmp.abspath()):
            self.fatal('Could not remove the temporary directory %r' % self.tmp)
        self.tmp.mkdir()
        self.options.destdir = self.tmp.abspath()

    def execute(self, *k, **kw):
        back = self.options.destdir
        try:
            super(BDist, self).execute(*k, **kw)
        finally:
            self.options.destdir = back

        files = self.tmp.ant_glob('**')

        # we could mess with multiple inheritance but this is probably unnecessary
        from waflib import Scripting
        ctx = Scripting.Dist()
        project_name = self.env.PROJNAME
        variant = self.env.CMTCFG
        version = self.env.VERSION
        ctx.arch_name = '%s-%s-%s.tar.gz' % (project_name,
                                             variant,
                                             version)
        ctx.algo = 'tar.gz'
        ctx.files = files
        ctx.tar_prefix = ''
        ctx.base_path = self.tmp
        ctx.archive()

        shutil.rmtree(self.tmp.abspath())
        return
    pass # class BDist

