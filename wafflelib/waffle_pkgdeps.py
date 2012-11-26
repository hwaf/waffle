# -*- python -*-
# pkgdeps.py
# a few waf functions to deal with package dependencies

# imports ---------------------------------------------------------------------
import os
import os.path
import os.path as osp

# waf imports
import waflib.Build
import waflib.Configure
import waflib.Context
import waflib.Errors
import waflib.Logs as msg
import waflib.Scripting
import waflib.Utils

# waffle imports

### API for project queries
@waflib.Configure.conf
def waffle_project_names(self):
    return self.env['WAFFLE_PROJNAMES']

@waflib.Configure.conf
def waffle_add_project(self, projname):
    self.env.append_unique('WAFFLE_PROJNAMES', projname)

@waflib.Configure.conf
def waffle_project(self):
    '''return the name of the current project'''
    return self.env['WAFFLE_PROJNAME']

@waflib.Configure.conf
def waffle_set_project_path(self, projname, projpath):
    if not projname in self.waffle_project_names():
        raise KeyError('no such project [%s] (values=%s)'%
                       (projname,self.waffle_project_names()))
    self.env['WAFFLE_PROJPATH_%s' % projname] = projpath

@waflib.Configure.conf
def waffle_get_project_path(self, projname=None):
    if projname is None:
        projname = self.waffle_project()
        pass
    if not projname in self.waffle_project_names():
        raise KeyError('no such project [%s] (values=%s)'%
                       (projname,self.waffle_project_names()))
    return self.env['WAFFLE_PROJPATH_%s'%projname]
    
@waflib.Configure.conf
def waffle_project_deps(self, projname=None):
    '''return the list of projects projname depends on'''
    if projname is None:
        projname = self.waffle_project()
        pass
    if not projname in self.waffle_project_names():
        raise KeyError('no such project [%s] (values=%s)'%
                       (projname,self.waffle_project_names()))
    return self.env['WAFFLE_PROJDEPS_%s'%projname]

### API for package queries
@waflib.Configure.conf
def waffle_pkg_deps(self, pkgname, projname=None):
    return self.env['WAFFLE_PKGDEPS_%s'%pkgname]

@waflib.Configure.conf
def waffle_pkgs(self, projname=None):
    '''return the list of package full-names for the current project'''
    return self.env['WAFFLE_PKGNAMES']

@waflib.Configure.conf
def waffle_add_pkg(self, pkgname, projname=None):
    self.env.append_unique('WAFFLE_PKGNAMES', pkgname)
    return

@waflib.Configure.conf
def waffle_has_pkg(self, pkgname, projname=None):
    return pkgname in self.waffle_pkgs(projname)

@waflib.Configure.conf
def waffle_pkg_dirs(self, projname=None):
    '''return the path to the packages from the current project'''
    return self.env['WAFFLE_PKGDIRS']

### ---------------------------------------------------------------------------
@waflib.Configure.conf
def build_pkg_deps(ctx, pkgdir=None):
    """process all packages and build the dependency graph"""

    if pkgdir is None: pkgdir = ctx.options.cmtpkgs
    if pkgdir is None: pkgdir = ctx.env.CMTPKGS
    if osp.abspath(pkgdir):
        pkgdir = osp.realpath(pkgdir)
        pkgdir = ctx.root.find_dir(pkgdir)
    else:
        pkgdir = = ctx.path.find_dir(pkgdir)
        pass
    ctx.pkgdir = pkgdir 
    ctx.msg("pkg-dir", pkgdir.abspath())
    pkgs = ctx.find_subpackages(pkgdir.name)
    ctx.msg("local packages", str(len(pkgs)))
    for pkg in pkgs:
        msg.info(" %s" % pkg.path_from(pkgdir))
        pkgname = pkg.path_from(pkgdir)
        ctx.waffle_add_pkg(pkgname)
        ctx.env['WAFFLE_PKGDEPS_%s' % pkgname] = []

    ctx.recurse([pkg.abspath() for pkg in pkgs], name='pkg_deps')

    pkglist = []
    def process_pkg(pkg, parent=None):
        deps = ctx.waffle_pkg_deps(pkg)
        for ppkg in deps:
            if ppkg in pkglist:
                continue
            process_pkg(ppkg, pkg)
        if not (pkg in pkglist):
            if not ctx.waffle_has_pkg(pkg):
                ctx.fatal('package [%s] depends on *UNKNOWN* package [%s]' %
                          (parent, pkg,))
            pkglist.append(pkg)
    for pkg in ctx.waffle_pkgs():
        process_pkg(pkg)
        pass
    
    ctx.env['WAFFLE_PKGNAMES'] = pkglist[:]
    ctx.env['WAFFLE_PKGDIRS'] = []
    topdir = os.path.dirname(waflib.Context.g_module.root_path)
    topdir = ctx.root.find_dir(topdir)
    for pkgname in pkglist:
        #print "--",pkgname,pkgdir.abspath()
        pkg = ctx.pkgdir.find_node(pkgname)
        pkgname = pkg.path_from(topdir)
        ctx.env.append_unique('WAFFLE_PKGDIRS', pkgname)
    return

### ---------------------------------------------------------------------------
#class PkgList(waflib.Context.Context):
class PkgList(waflib.Configure.ConfigurationContext):
    '''gives the list of packages in the current project'''

    cmd = 'pkglist'
    #fun = 'build'

    def execute(self):
        ctx = self
        pkgdir = ctx.path.find_dir(ctx.options.cmtpkgs)
        assert pkgdir, "no such directory: [%s]" % ctx.options.cmtpkgs
        msg.info("pkg-dir: %s" % pkgdir.abspath())
        pkgs = ctx.find_subpackages(pkgdir.name)
        for pkg in pkgs:
            msg.info(" %s" % pkg.path_from(pkgdir))
            pass

        self.pkgs = pkgs
        self.pkgdir = pkgdir
        return
    
### ---------------------------------------------------------------------------
class PkgMgr(waflib.Configure.ConfigurationContext):
    '''finds and creates the list of packages in the current project'''

    cmd = 'pkgmgr'

    
    def execute(self):
        return self.build_pkg_deps()

@waflib.Configure.conf
def use_pkg(ctx,
            pkgname, version=None,
            public=None, private=None,
            runtime=None):
    pkg = ctx.path.path_from(ctx.root.find_dir(ctx.pkgdir.abspath()))
    ## print "--------"
    ## print "ctx:",ctx
    ## print "pkg:",pkg
    ## print "dep:",pkgname
    ## print "path:",ctx.path.abspath()
    ctx.env.append_unique('WAFFLE_PKGNAMES', pkg)
    ctx.env.append_unique('WAFFLE_PKGDEPS_%s' % pkg, pkgname)
    return


### ---------------------------------------------------------------------------
import waflib.Build
class ShowPkgUses(waflib.Build.BuildContext):
    '''shows the list of packages a given package depends on'''

    cmd = 'show-pkg-uses'

    def execute_build(self):
        if not waflib.Options.commands:
            self.fatal('%s expects at least one package name. got: %s' %
                       (self.cmd, waflib.Options.commands))
            
        while waflib.Options.commands:
            pkgname = waflib.Options.commands.pop(0)
            #print "pkgname:",pkgname
            self.show_pkg_uses(pkgname)
        return

    def get_pkg_uses(self, pkgname):
        pkgnames = self.waffle_pkgs()
        if not self.waffle_has_pkg(pkgname):
            self.fatal('package [%s] not in package list:\npkgs: %s' %
                       (pkgname,pkgnames))
        pkgdeps = self.waffle_pkg_deps(pkgname)
        return sorted(pkgdeps)

    def do_display_pkg_uses(self, pkgname, depth=0, maxdepth=2):
        pkgdeps = self.get_pkg_uses(pkgname)
        msg.info('%s%s' % ('  '*depth, pkgname))
        depth += 1
        if depth < maxdepth:
            for pkgdep in pkgdeps:
                self.do_display_pkg_uses(pkgdep, depth)
            
    def show_pkg_uses(self, pkgname):
        pkgdeps = self.get_pkg_uses(pkgname)
        msg.info('package dependency list for [%s] (#pkgs=%s)' %
                 (pkgname, len(pkgdeps)))
        self.do_display_pkg_uses(pkgname)
        return
    
### ---------------------------------------------------------------------------
import waflib.Build
class ShowProjects(waflib.Build.BuildContext):
    '''shows the tree of projects for the current project'''

    cmd = 'show-projects'

    def execute_build(self):
        self.show_projects(projname=self.waffle_project())
        return

    def get_project_uses(self, projname):
        projnames = self.env['WAFFLE_PROJNAMES']
        if not projname in projnames:
            self.fatal('project [%s] not in project list:\nprojects: %s' %
                       (projname, projnames))
            pass
        projdeps = self.env['WAFFLE_PROJDEPS_%s' % projname]
        return projdeps

    def do_display_project_uses(self, projname, depth=0):
        projdeps = self.get_project_uses(projname)
        msg.info('%s%s' % ('  '*depth, projname))
        for projdep in projdeps:
            self.do_display_project_uses(projdep, depth+1)
            pass
        return
    
    def show_projects(self, projname):
        projdeps = self.get_project_uses(projname)
        msg.info('project dependency list for [%s] (#projs=%s)' %
                 (projname, len(projdeps)))
        self.do_display_project_uses(projname)
        return
    
