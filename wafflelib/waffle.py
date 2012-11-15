# waffle.py
# a few waf functions to help building gaudi and athena
# a possible CMT replacement

# imports ---------------------------------------------------------------------
import optparse
import os
import os.path
import shutil

# waf imports
import waflib.Configure
import waflib.Context
import waflib.Errors
import waflib.Logs
import waflib.Options
import waflib.Task
import waflib.Tools.ccroot
import waflib.Utils
from waflib.Configure import conf
from waflib.TaskGen import feature, before_method, after_method, extension

import waflib.Logs as msg

# waffle imports
#import waflib.extras.waffle_packaging as waffle_packaging
import waflib.extras.waffle_utils as waffle_utils
import waflib.extras.waffle_subprocess as subprocess

# constants -------------------------------------------------------------------
WAFFLE_CFG = '.local.waffle.cfg'
WAFFLE_PKGDIR = 'pkg'
WAFFLE_CMTCFG = 'default' # 'x86_64-linux-gcc-opt'
WAFFLE_PROJECT_INFO = 'project.info'

REGEN_WSCRIPTS = 0
'''switch to regenerate the wscripts from the CMT requirements files'''

# functions -------------------------------------------------------------------
def options(ctx):

    g_module = waflib.Context.g_module

    gr = optparse.OptionGroup(ctx.parser, 'waffle project options')
    ctx.add_option_group(gr)

    gr.add_option(
        '--usrcfg',
        action='store',
        default=None,
        help='path to a waffle configuration file to override values',
        )

    gr.add_option(
        '--prefix',
        action='store',
        default=g_module.PREFIX,
        help="path where to install project",
        )

    global WAFFLE_PKGDIR
    gr.add_option(
        '--cmtpkgs',
        action='store',
        default=WAFFLE_PKGDIR,
        help='path to cmt pkgs to be waffled (default=%s)' % WAFFLE_PKGDIR,
        )

    gr.add_option(
        '--projects',
        action='store',
        default=None,
        help='colon-separated list of paths to projects this project depends on'
        )
    
    import os
    global WAFFLE_CMTCFG
    WAFFLE_CMTCFG = os.getenv('CMTCONFIG', WAFFLE_CMTCFG)
    gr.add_option(
        '--cmtcfg',
        action='store',
        default=WAFFLE_CMTCFG,
        help='the arch-os-compiler-type quadruplet. default=%s' % WAFFLE_CMTCFG,
        )

    gr.add_option(
        '--regenwscripts',
        action='store',
        default=REGEN_WSCRIPTS,
        help='regenerate wscript files from cmt/requirements',
        )

    ctx.load('c_config')
    ctx.load('compiler_c')
    ctx.load('compiler_cxx')
    #ctx.load('compiler_fc')
    ctx.load('python')
    #ctx.load('java')

    ctx.load('waffle_external_packages')

    ctx.load('boost')
    ## local tools
    #ctx.load('rootmap', tooldir='waffle/wafflelib')
    #ctx.load('atlaspolicy', tooldir='waffle/wafflelib')
    ctx.load('waffle_basepolicy')
    ctx.load('waffle_packaging')
    ctx.load('waffle_pkgdeps')

    
    pkgs = find_suboptions(WAFFLE_PKGDIR)
    ctx.recurse(pkgs, mandatory=False)
    return

@conf
def configure(ctx):
    msg.debug('configure...')
    import os
    import os.path

    g_module = waflib.Context.g_module
    
    ctx.env.PREFIX =         os.path.realpath(ctx.options.prefix)
    ctx.env.INSTALL_AREA =   ctx.env.PREFIX
    ctx.env.CMTPKGS =        ctx.options.cmtpkgs
    ctx.env.CMTCFG  =        ctx.options.cmtcfg
    ctx.env.VERSION =        g_module.VERSION
    ctx.env.WAFFLE_PROJNAME= g_module.APPNAME

    # first, setup the correct variant: WAFFLE_CMTCFG
    ctx.configure_cmtcfg()

    # now setup the project
    ctx.configure_project()
    
    #print ctx.env.CPPFLAGS
    if waflib.Options.options.usrcfg:
        # store the configuration...
        ctx.env.store(WAFFLE_CFG)
        pass

    #ctx.setenv(ctx.env.CMTCFG, env=ctx.env)
    return

@conf
def configure_cmtcfg(ctx):
    g_module = waflib.Context.g_module
    g_module.WAFFLE_CMTCFG = ctx.env.CMTCFG
    if ctx.env.CMTCFG in ('default', 'Darwin', 'Linux', 'Windows'):
        msg.debug('detecting default CMTCFG...')
        mana_arch = 'x86_64'
        mana_os = 'linux'
        mana_comp = 'gcc'
        mana_build_type = 'opt'
        if waffle_utils._is_darwin(ctx):
            mana_os = 'darwin'
        elif waffle_utils._is_linux(ctx):
            mana_os = 'linux'
        else:
            mana_os = 'win'
            pass

        if waffle_utils._is_host_32b(ctx):
            mana_arch = 'i686'
        elif waffle_utils._is_host_64b(ctx):
            mana_arch = 'x86_64'
        else:
            mana_arch = 'x86_64'
            pass
        WAFFLE_CMTCFG = '-'.join([mana_arch, mana_os,
                                  mana_comp, mana_build_type])
        ctx.env.CMTCFG = WAFFLE_CMTCFG
        pass
    
    ctx.env.WAFFLE_CMTCFG = ctx.env.CMTCFG
    o = ctx.env.WAFFLE_CMTCFG.split('-')
    assert len(o) == 4, \
        "Invalid CMTCFG (%s). Expected ARCH-OS-COMP-OPT. ex: x86_64-linux-gcc-opt" % ctx.env.CMTCFG
    
    if o[1].startswith('mac'):
        o[1] = 'darwin'
    if o[1].startswith('slc'):
        o[1] = 'linux'

    if o[2].startswith('gcc'):
        o[2] = 'gcc'

    ctx.env.MANA_QUADRUPLET = o
    
    ctx.env.MANA_ARCH, \
    ctx.env.MANA_OS, \
    ctx.env.MANA_COMPILER, \
    ctx.env.MANA_BUILD_TYPE = ctx.env.MANA_QUADRUPLET

    msg.info('='*80)
    ctx.msg('project',    ctx.env.WAFFLE_PROJNAME)
    ctx.msg('prefix',     ctx.env.PREFIX)
    ctx.msg('pkg dir',    ctx.env.CMTPKGS)
    ctx.msg('variant',    ctx.env.CMTCFG)
    ctx.msg('arch',       ctx.env.MANA_ARCH)
    ctx.msg('OS',         ctx.env.MANA_OS)
    ctx.msg('compiler',   ctx.env.MANA_COMPILER)
    ctx.msg('build-type', ctx.env.MANA_BUILD_TYPE)
    msg.info('='*80)
    
    ctx.load('c_config')
    ctx.load('compiler_cc')
    ctx.load('compiler_cxx')
    #ctx.load('compiler_fc')
    #ctx.load('python')
    #ctx.load('java')

    ctx.load('waffle_external_packages')

    #ctx.load('boost')

    ctx.load('waffle_basepolicy')
    ctx.load('waffle_packaging')
    ctx.load('waffle_pkgdeps')

    return

@conf
def configure_project(ctx):
    #ctx.options.prefix  = os.path.realpath(ctx.options.prefix)
    # need to keep cmtpkgs relative to 'top'
    #ctx.options.cmtpkgs = os.path.realpath(ctx.options.cmtpkgs)

    import os
    import os.path
    
    g_module = waflib.Context.g_module

    ctx.env.CMTPKGS = ctx.path.find_dir(ctx.env.CMTPKGS).abspath()
    install_area = ctx.env.INSTALL_AREA
    ctx.env.INSTALL_AREA = install_area
    ctx.env.INSTALL_AREA_INCDIR = os.path.join(install_area,'include')
    ctx.env.INSTALL_AREA_BINDIR = os.path.join(install_area,'bin')
    ctx.env.INSTALL_AREA_LIBDIR = os.path.join(install_area,'lib')

    binstall_area = ctx.path.make_node(g_module.out)\
                                 .make_node('.install_area').abspath()
    ctx.env.BUILD_INSTALL_AREA = binstall_area
    ctx.env.BUILD_INSTALL_AREA_INCDIR = os.path.join(binstall_area,'include')
    ctx.env.BUILD_INSTALL_AREA_BINDIR = os.path.join(binstall_area,'bin')
    ctx.env.BUILD_INSTALL_AREA_LIBDIR = os.path.join(binstall_area,'lib')

    ctx.msg('install-area',       ctx.env.INSTALL_AREA)
    ctx.msg('build-install-area', ctx.env.BUILD_INSTALL_AREA)
    ctx.env.WAFFLE_ROOT = os.getcwd()
    ctx.msg('project root', ctx.env.WAFFLE_ROOT)
    
    g_module.REGEN_WSCRIPTS = bool(ctx.options.regenwscripts)
    ctx.msg('regen-wscripts', str(g_module.REGEN_WSCRIPTS))

    ## init project tree structure
    ctx.configure_projects_tree()
    ctx.msg('project deps', ctx.waffle_project_deps())
    
    if waflib.Options.options.usrcfg:
        # try to retrieve an already configured project
        try:
            fname = waflib.Options.options.usrcfg
            msg.info('loading configuration from [%s]' % fname)
            ctx.env.load(fname)
            msg.info('loading configuration from [%s] [done]' % fname)
        except (IOError,):
            pass
        pass

    # FIXME: we should find a better way to configure this...
    #        at least something more automagic and less hardcodish
    ctx.configure_policy()
   

    pkgs = ctx.find_subpackages(ctx.options.cmtpkgs)
    cmtpkg_root = ctx.path.find_dir(ctx.options.cmtpkgs).abspath()

    if ctx.cmd != 'clean':
        for pkg in pkgs:
            #msg.info("-- %s --" % pkg.name)
            pkg_node = pkg
            wscript_node = pkg_node.find_resource("wscript")
            if (not ctx.options.regenwscripts) or (wscript_node and
                not ('automatically generated by gen-wscript'
                     in wscript_node.read())):
                msg.debug ("... skipping [%s]... (package has already a wscript file)" % (pkg.srcpath(),))
            else:
                import os
                msg.debug ("... generating wscript for [%s]..." %
                           (pkg_node.srcpath(),))
                wafflelib_dir = os.path.dirname(waffle_utils.__file__)
                _cmd = [
                    os.path.join(wafflelib_dir, 'gen-wscript.py'),
                    pkg_node.srcpath(),
                    cmtpkg_root,
                    os.getcwd(),
                    ]
                #print "++++>", _cmd
                subprocess.Popen(_cmd).wait()
                pass
            #ctx.recurse(pkg.abspath())
    #ctx.recurse(ctx.options.cmtpkgs)

    # configure packages
    ctx.configure_pkgs()
    return

@conf
def configure_projects_tree(ctx, projname=None, projpath=None):
    if projname is None:
        projname = ctx.waffle_project()
        pass
    if projpath is None:
        projpath = ctx.env.WAFFLE_ROOT
        pass

    all_good = True
    #print ">"*40,"--project-tree--",projname
    ctx.waffle_add_project(projname)
    ctx.waffle_set_project_path(projname, projpath)
    
    projdeps = ctx.options.projects
    if projdeps is None:
        projdeps = []
    elif isinstance(projdeps, str):
        projdeps = projdeps.split(':')
    else:
        self.fatal('cant handle option --projects')
        pass
    projpaths = projdeps[:]
    #print ":: projpaths:",projpaths
    projdeps = []
    env = waflib.ConfigSet.ConfigSet()
    for projpath in projpaths:
        if not projpath:
            continue
        proj_dir = ctx.root.find_dir(projpath)
        if not proj_dir:
            continue
        try:
            proj_infos = proj_dir.ant_glob('**/%s' % WAFFLE_PROJECT_INFO)
        except:
            all_good = False
            continue
        if not proj_infos or len(proj_infos) != 1:
            msg.error("invalid project infos at [%s]" % proj_dir.abspath())
            all_good = False
            continue
        proj_node = proj_infos[0]
        #print proj_node.abspath()
        
        denv = waflib.ConfigSet.ConfigSet()
        denv.load(proj_node.abspath())
        ppname = denv['WAFFLE_PROJNAME']
        projdeps += [ppname]
        ctx.waffle_add_project(ppname)
        ctx.waffle_set_project_path(ppname, projpath)

        # import uses from this project into our own
        from waflib.Tools.ccroot import USELIB_VARS
        vv = set([])
        for kk in USELIB_VARS.keys():
            vv |= USELIB_VARS[kk]
        vv = tuple([ii+"_" for ii in vv])
        for k in denv.keys():
            if k in ('INSTALL_AREA_INCDIR', 'INCPATHS'):
                env.prepend_value('INCPATHS', denv[k])
                continue
            if k in ('INSTALL_AREA_LIBDIR', 'LIBPATH'):
                env.prepend_value('LIBPATH', denv[k])
                continue
            if k in ('INSTALL_AREA_BINDIR', 'PATH'):
                env.prepend_value('PATH', denv[k])
                continue
                
            if k in ('ARCH_ST', 'DEFINES_ST',
                     'FRAMEWORKPATH_ST', 'FRAMEWORK_ST',
                     'LIBPATH_ST', 'LIB_ST',
                     'RPATH_ST', 
                     'STLIBPATH_ST', 'STLIB_ST',
                     'BUILD_INSTALL_AREA',
                     'PREFIX',
                     'LIBDIR',
                     'BINDIR',
                     'VERSION',
                     'CMTPKGS',
                     ):
                continue
            if k.startswith('WAFFLE_') or k.endswith('_PATTERN'):
                continue
            # print "-- import [%s] from [%s] %r" % (k, ppname, denv[k])
            v = denv[k]
            if isinstance(v, list):
                #env.prepend_unique(k, v)
                env.prepend_value(k, v)
            else:
                #ctx.fatal('invalid type (%s) for [%s]' % (type(v),k))
                env[k] = v
        pass # loop over proj-paths
    if not all_good:
        ctx.fatal("error(s) while configuring project dependency tree")
        pass
    # FIXME: windows(tm) handling !!
    if 'LIBPATH' in env.keys():
        env.prepend_value('LD_LIBRARY_PATH', env['LIBPATH'])
        if waffle_utils._is_darwin(ctx):
            env.prepend_value('DYLD_LIBRARY_PATH', env['LIBPATH'])
        
    if waffle_utils._is_darwin(ctx):
        # special handling of ['bar', '-arch', 'foo', 'baz']
        #-> regroup as ['bar', ('-arch','foo'), 'baz'] so the ctx.append_unique
        # will work correctly
        def _regroup(lst):
            if not '-arch' in lst:
                return lst
            v = []
            idx = 0
            while idx < len(lst):
                o = lst[idx]
                if o == '-arch':
                    o = (lst[idx], lst[idx+1])
                    idx += 1
                    pass
                v.append(o)
                idx += 1
            return v
        def _flatten(lst):
            o = []
            for i in lst:
                if isinstance(i, (list,tuple)): o.extend(i)
                else:                           o.append(i)
            return o
    else:
        def _regroup(v): return v
        def _flatten(v): return v
        pass

    
    # merge all
    for k in env.keys():
        v = env[k]
        if isinstance(v, list):
            ctx.env[k] = _regroup(ctx.env[k])
            ctx.env.append_unique(k, _regroup(v))
            ctx.env[k] = _flatten(ctx.env[k])
        else:
            #ctx.fatal('invalid type (%s) for [%s]' % (type(v), k))
            #ctx.env wins...
            if not k in ctx.env.keys():
                ctx.env[k] = v
            pass
        pass
    #ctx.waffle_project_deps(projname)[:] = projdeps
    ctx.env['WAFFLE_PROJDEPS_%s' % projname] = projdeps
    if ctx.env.PATH:
        ctx.env.PATH = os.pathsep.join(ctx.env.PATH)
    return

@conf
def configure_pkgs(ctx):

    ctx.build_pkg_deps(pkgdir=ctx.options.cmtpkgs)
    ctx.recurse(ctx.waffle_pkg_dirs())
    
    return

@conf
def build(ctx):
    #ctx.add_pre_fun(pre) 
    #ctx.add_post_fun(waffle_do_post_build)

    pkgs = ctx.find_subpackages(ctx.options.cmtpkgs)
    for pkg in pkgs:
        ctx.recurse(pkg.srcpath())
        pass
    
    ctx.waffle_do_post_build()    
    return

@conf
def error_handler(fct, exc):
    msg.debug ("-- handling error [%r]" % (exc,))
    msg.debug ("--   fct: %r" % (fct,))
    return waflib.Configure.BREAK

@conf
def test_complib(ctx):
    msg.debug ("-- test building component-libraries...")

def find_subpackages(self, directory='.'):
    srcs = []
    root_node = self.path.find_dir(directory)
    dirs = root_node.ant_glob('**/*', src=False, dir=True)#.split()
    for d in dirs:
        #msg.debug ("##> %s (type: %s)" % (d.abspath(), type(d)))
        node = d # self.path.find_dir(d.abspath())
        if node and (node.ant_glob('wscript') or
                     node.ant_glob('cmt/requirements')):
            #msg.debug ("##> %s" % d.srcpath())
            srcs.append(d)
    #return ' '.join(srcs)
    return srcs

def find_suboptions(directory='.'):
    pkgs = []
    for root, dirs, files in os.walk(directory):
        if 'wscript' in files:
            pkgs.append(root)
            continue
        if os.path.basename(root) == 'cmt' and 'requirements' in files:
            pkgs.append(os.path.dirname(root))
            continue
    return pkgs

### ---------------------------------------------------------------------------
@feature('*')
@after_method('process_source') #@before_method('process_rule')
def massage_c_and_cxx_linkflags(self):
    for n in ('cshlib', 'cstlib', 'cprogram',):
        c = waflib.Task.classes[n]
        c.run_str='${LINK_CC} ${CCLNK_SRC_F}${SRC} ${CCLNK_TGT_F}${TGT[0].abspath()} ${LINKFLAGS} ${RPATH_ST:RPATH} ${FRAMEWORKPATH_ST:FRAMEWORKPATH} ${FRAMEWORK_ST:FRAMEWORK} ${ARCH_ST:ARCH} ${STLIB_MARKER} ${STLIBPATH_ST:STLIBPATH} ${STLIB_ST:STLIB} ${SHLIB_MARKER} ${LIBPATH_ST:LIBPATH} ${LIB_ST:LIB}'
    for n in ('cxxshlib', 'cxxstlib', 'cxxprogram',):
        cxx = waflib.Task.classes[n]
        cxx.run_str='${LINK_CXX} ${CXXLNK_SRC_F}${SRC} ${CXXLNK_TGT_F}${TGT[0].abspath()} ${LINKFLAGS} ${RPATH_ST:RPATH} ${FRAMEWORKPATH_ST:FRAMEWORKPATH} ${FRAMEWORK_ST:FRAMEWORK} ${ARCH_ST:ARCH} ${STLIB_MARKER} ${STLIBPATH_ST:STLIBPATH} ${STLIB_ST:STLIB} ${SHLIB_MARKER} ${LIBPATH_ST:LIBPATH} ${LIB_ST:LIB}'
    return

### ---------------------------------------------------------------------------
@feature('cxx', 'c')
@after_method('apply_incpaths')
def insert_blddir(self):
    self.env.prepend_value('INCPATHS', self.env.BUILD_INSTALL_AREA_INCDIR)
    self.env.prepend_value('INCPATHS', self.env.INSTALL_AREA_INCDIR)
    self.env.prepend_value('INCPATHS', '.')

    self.env.prepend_value('LIBPATH', self.env.BUILD_INSTALL_AREA_LIBDIR)
    return

class symlink_tsk(waflib.Task.Task):
    """
    A task to install symlinks of binaries and libraries under the *build*
    install-area (to not require shaggy RPATH)
    this is needed for genconf and gencliddb.
    """
    color   = 'PINK'
    reentrant = True
    
    def run(self):
        import os
        try:
            os.remove(self.outputs[0].abspath())
        except OSError:
            pass
        return os.symlink(self.inputs[0].abspath(),
                          self.outputs[0].abspath())


@feature('symlink_tsk')
@after_method('apply_link')
def add_install_copy(self):
    link_cls_name = self.link_task.__class__.__name__
    # FIXME: is there an API for this ?
    if link_cls_name.endswith('lib'):
        outdir = self.bld.path.make_node('.install_area').make_node('lib')
    else:
        outdir = self.bld.path.make_node('.install_area').make_node('bin')
    link_outputs = waflib.Utils.to_list(self.link_task.outputs)
    for out in link_outputs:
        if isinstance(out, str):
            n = out
        else:
            n = out.name
        out_sym = outdir.find_or_declare(n)
        #print("===> ", self.target, link_cls_name, out_sym.abspath())
        tsk = self.create_task('symlink_tsk',
                               out,
                               out_sym)
        self.source += tsk.outputs

# def symlink_tgt(cls):
#     old = cls.run
#     def wrap(self):
#         return old(self)
#     setattr(cls, 'run', wrap)
# symlink_tgt(some_cls)

def _get_pkg_name(self):
    # FIXME: should this be more explicit ?
    pkg_name = self.path.name
    return pkg_name

def _get_pkg_version_defines(self):
    pkg_name = _get_pkg_name(self)
    pkg_vers = "%s-XX-XX-XX" % pkg_name
    pkg_defines = ['PACKAGE_VERSION="%s"' % pkg_vers,
                   'PACKAGE_VERSION_UQ=%s'% pkg_vers]
    cmt_dir_node = self.path.get_src().find_dir('cmt')
    if not cmt_dir_node:
        return pkg_defines
    version_cmt = cmt_dir_node.find_resource('version.cmt')
    if not version_cmt:
        return pkg_defines
    pkg_vers = version_cmt.read().strip()
    pkg_defines = ['PACKAGE_VERSION="%s"' % pkg_vers,
                   'PACKAGE_VERSION_UQ=%s'% pkg_vers]
    #msg.debug("*** %s %r" % (pkg_name, pkg_vers))
    return pkg_defines

### ---------------------------------------------------------------------------
def build_app(self, name, source, **kw):
    kw = dict(kw)

    # FIXME: hack !!! cppunit doesn't propagate correctly...
    do_test = kw.get('do_test', False)
    if do_test:
        return

    kw['features'] = waflib.Utils.to_list(
        kw.get('features', 'cxx cxxprogram')) + [
        'symlink_tsk',
        ]
    
    kw['use'] = waflib.Utils.to_list(kw.get('use', []))

    pkg_node = self.path.get_src()
    src_node = self.path.find_dir('src')

    srcs = self.path.ant_glob(source)
    if (not srcs) and src_node:
        # hack to mimick CMT's default (to take sources from src)
        srcs = src_node.ant_glob(source)
        pass
    if not srcs:
        self.fatal("could not infer sources from %r" % source)
        pass

    linkflags = kw.get('linkflags', [])
    linkflags = self.env.SHLINKFLAGS + linkflags
    kw['linkflags'] = linkflags

    defines = kw.get('defines', [])
    defines = [d[len('-D'):] for d in self.env.CPPFLAGS] + defines
    kw['defines'] = defines + _get_pkg_version_defines(self)
    
    # extract package name
    PACKAGE_NAME = _get_pkg_name(self)

    exe = self.new_task_gen(
        name=name,
        source=srcs,
        target=name+'.exe',
        install_path='${INSTALL_AREA}/bin',
        libpath = self.env.LD_LIBRARY_PATH + [self.path.get_bld().abspath()],
        #libpath = self.env.LD_LIBRARY_PATH,
        **kw)
        
    return exe

### ---------------------------------------------------------------------------
def build_complib(self, name, source, **kw):

    kw = dict(kw)
    do_genmap = kw.get('do_genmap', True)
    do_genconf= kw.get('do_genconf', True)
    do_cliddb = kw.get('do_cliddb', True)
    
    #msg.info('=========== %s ============' % name)
    #msg.info("::: %s" % self.path.abspath())
    src_node = self.path.find_dir('src')
    bld_node = src_node.get_bld()

    srcs = self.path.ant_glob(source)
    if (not srcs) and src_node:
        # hack to mimick CMT's default (to take sources from src)
        srcs = src_node.ant_glob(source)
        pass
    if not srcs:
        self.fatal("could not infer sources from %r" % source)
        pass
    
    linkflags = kw.get('linkflags', [])
    linkflags = self.env.SHLINKFLAGS + linkflags
    kw['linkflags'] = linkflags

    defines = kw.get('defines', [])
    defines = [d[len('-D'):] for d in self.env.CPPFLAGS] + defines
    kw['defines'] = defines + _get_pkg_version_defines(self)

    kw['depends_on'] = waflib.Utils.to_list(kw.get('use', [])) + \
                       waflib.Utils.to_list(kw.get('depends_on', []))
    #print("---> depends: %s" % kw['depends_on'])
    
    # extract package name
    PACKAGE_NAME = _get_pkg_name(self)

    # schedule the requested features
    features = ['cxx', 'cxxshlib',]
    features.append('symlink_tsk')
    if do_genmap:
        features.append('gen_map')
    if do_genconf:
        features.append('gen_conf')
        #features.append('py')
    if do_cliddb:
        features.append('gen_cliddb')
        
    lib = self.new_task_gen(
        #features='cxx cxxshlib symlink_tsk',
        features=features,
        name='complib-%s' % name,
        source=srcs,
        target=name,
        install_path='${INSTALL_AREA}/lib',
        libpath = self.env.LD_LIBRARY_PATH + [self.path.get_bld().abspath()],
        reentrant=True,
        **kw)
    lib_name = "lib%s.so" % (lib.target,) # FIXME !!
    lib.env['GENCONF_LIBNAME'] = lib.target
    lib.env['PACKAGE_NAME'] = PACKAGE_NAME
    lib.env['GENCLIDDB_LIB_NAME'] = lib.target
    lib.env['GENCLIDDB'] = self.env['GENCLIDDB']
    
    return lib

### ---------------------------------------------------------------------------
def build_linklib(self, name, source, **kw):

    #msg.info('=========== %s ============' % name)
    # extract package name
    PACKAGE_NAME = _get_pkg_name(self)

    kw = dict(kw)
    linkflags = kw.get('linkflags', [])
    linkflags = self.env.SHLINKFLAGS + linkflags
    kw['linkflags'] = linkflags
    
    src_node = self.path.find_dir('src')

    srcs = self.path.ant_glob(source)
    if (not srcs) and src_node:
        # hack to mimick CMT's default (to take sources from src)
        srcs = src_node.ant_glob(source)
        pass
    if not srcs:
        self.fatal("could not infer sources from %r" % source)
        pass
    includes = kw.get('includes', [])
    includes.insert(0, self.path.abspath())
    #includes.insert(1, self.path.abspath()+'/'+PACKAGE_NAME)
    kw['includes'] = includes + [src_node]

    export_incs = None
    kw['export_includes'] = waflib.Utils.to_list(
        kw.get('export_includes', [])
        )[:]
    if not kw['export_includes']:
        inc_node = self.path.find_dir(PACKAGE_NAME)
        if inc_node:
            export_incs = '.'
            kw['export_includes'].append(export_incs)
        inc_node = self.path.find_dir('inc/%s' % PACKAGE_NAME)
        if inc_node:
            export_incs = 'inc'
            kw['export_includes'].append(export_incs)
            #self.fatal('%s: export_includes - inc' % name)
        else:
            #self.fatal('%s: could not find [inc/%s] !!' % (name,PACKAGE_NAME))
            pass
    else:
        export_incs = kw['export_includes']
        #msg.info('%s: exports: %r' % (name, kw['export_includes']))
        pass

    kw['includes'].extend(kw['export_includes'])
    
    kw['use'] = waflib.Utils.to_list(kw.get('use', [])) + ['dl']
    
    defines = kw.get('defines', [])
    _defines = []
    for d in self.env.CPPFLAGS:
        if d.startswith('-D'):
            _defines.append(d[len('-D'):])
        else:
            _defines.append(d)
    defines = _defines + defines
    kw['defines'] = defines + _get_pkg_version_defines(self)

    #msg.info ("==> build_linklib(%s, '%s', %r)..." % (name, source, kw))
    o = self.new_task_gen(
        features        = 'cxx cxxshlib symlink_tsk',
        name            = name,
        source          = srcs,
        target          = name,
        install_path    = '${INSTALL_AREA}/lib',
        #export_includes = ['.', './'+PACKAGE_NAME],
        #export_includes = export_,
        libpath = self.env.LD_LIBRARY_PATH + [self.path.get_bld().abspath()],
        #libpath         = self.env.LD_LIBRARY_PATH,
        **kw
        )
    # for use-exports
    # FIXME: also propagate uses ?
    self.env['LIB_%s' % name] = [name]
    self.env.append_unique('LIBPATH_%s'%name, self.path.get_bld().abspath())
    #msg.info('--> libpath[%s]: %s' % (name, self.env['LIBPATH_%s'%name]))
    #msg.info('--> incpath[%s]: %s' % (name, export_incs))

    if export_incs:
        export_incs = waflib.Utils.to_list(export_incs)[0]
        if export_incs == '.':
            self.install_headers()
        elif export_incs == 'inc':
            incdir = self.path.find_dir('inc')
            hdrdir = 'inc/%s' % PACKAGE_NAME
            self.install_headers(hdrdir, cwd=incdir)
        else:
            pass

    #o.post()
    return o

### ---------------------------------------------------------------------------
def build_reflex_dict(self, name, source, selection_file, **kw):

    # extract package name
    PACKAGE_NAME = _get_pkg_name(self)

    source = waflib.Utils.to_list(source)[0]
    src_node = self.path.find_resource(source)
    if not src_node:
        # maybe in 'src' ?
        src_node = self.path.find_dir('src').find_resource(source)
        if src_node:
            source = os.path.join('src',source)
            
    kw = dict(kw)

    linkflags = [] # kw.get('linkflags', [])
    linkflags = self.env.SHLINKFLAGS + linkflags
    kw['linkflags'] = linkflags
    
    kw['includes'] = kw.get('includes',[])
    ## src_node = self.path.find_dir('src')
    ## if src_node:
    ##     kw['includes'].append(src_node.abspath())
    
    defines = kw.get('defines', [])
    _defines = []
    for d in self.env.CPPFLAGS:
        if d.startswith('-D'):
            _defines.append(d[len('-D'):])
        else:
            _defines.append(d)
    defines = _defines + defines
    kw['defines'] = defines + _get_pkg_version_defines(self) + ['__REFLEX__',]
    if waffle_utils._is_dbg(self):
        print(":"*80)
        # only add NDEBUG in dbg mode as it should already be added
        # by basepolicy.
        kw['defines'].append('NDEBUG')
        pass
        
    #libs = kw.get('libs', [])
    #kw['libs'] = libs + ['Reflex']
    
    uses = kw.get('use', [])
    kw['use'] = uses + ['Reflex']

    def _maybe_tgen(*names):
        for name in names:
            try:
                return self.get_tgen_by_name(name), name
            except:
                pass
        return None, None
    dep_inc_dirs = []
    def _get_deps(obj):
        uses = getattr(obj, 'use', [])
        ld = obj.path.get_bld().abspath()
        dep_inc_dirs.extend(getattr(obj,'includes',[]))
        for u in uses:
            tgt,n = _maybe_tgen(u, 'complib-%s' % u, 'genreflex-%s' % u)
            if tgt:
                _get_deps(tgt)
    for u in kw['use']:
        tgt,n = _maybe_tgen(u)
        if tgt:
            _get_deps(tgt)
    kw['includes'] = dep_inc_dirs + kw['includes']
    target = kw['target'] = kw.get('target', name+'Dict')
    del kw['target']
    defines= kw['defines']
    del kw['defines']
    o = self.new_task_gen(
        features='gen_reflex cxx cxxshlib symlink_tsk',
        name='genreflex-%s' % name,
        source=source,
        target=target,
        reentrant=False,
        #libpath = self.env.LD_LIBRARY_PATH,
        libpath = self.env.LD_LIBRARY_PATH + [self.path.get_bld().abspath()],
        defines=defines,
        **kw
        )
    o.env.GENREFLEX = self.env['GENREFLEX']
    o.env.GCCXML_USER_FLAGS = ['-D__GNUC_MINOR__=2',]
    o.env.GCCXML_FLAGS = [
        #'--quiet',
        '--debug',
        '--gccxmlopt=--gccxml-cxxflags', '--fail_on_warnings',
        #'--gccxmlopt=--gccxml-cxxflags', '-D__STRICT_ANSI__',
        waflib.Utils.subst_vars('--gccxmlpath=${GCCXML_BINDIR}', o.env),        
        ]
    lib_name = "lib%s" % (o.target,) # FIXME !!
    o.env.GENREFLEX_DSOMAP = '--rootmap=%s.dsomap' % lib_name
    o.env.GENREFLEX_DSOMAPLIB = '--rootmap-lib=%s.so' % lib_name
    
    if waffle_utils._is_32b(self):
        o.env.GCCXML_FLAGS.append('--gccxmlopt=-m32')
    else:
        o.env.GCCXML_FLAGS.append('--gccxmlopt=-m64')
        pass
    
    o.env.GENREFLEX_SELECTION = self.path.find_resource(selection_file).abspath()
    o.env.GENREFLEX_DICTNAME = name
    return o

### ---------------------------------------------------------------------------
def gen_rootcint_dict(self, name, source, target,
                      **kw):
    kw = dict(kw)

    _src = []
    for s in waflib.Utils.to_list(source):
        s = self.path.ant_glob(s)
        _src.extend(s)
    source = _src
    del _src
    
    includes = kw.get('includes', [])
    tgtdir = self.bldnode.find_or_declare(target).parent.abspath()
    kw['includes'] = [
        self.path.abspath(),
        self.bldnode.abspath(),
        tgtdir,
        ] + includes
    self.env.append_unique('INCPATHS', tgtdir)
    
    defines = kw.get('defines', [])
    defines.insert(0, 'R__ACCESS_IN_SYMBOL=1')
    kw['defines'] = defines
    
    env = self.env
    incpaths = [env.CPPPATH_ST % x for x in kw['includes']]
    o = self.new_task_gen(
        rule='${ROOTCINT} -f ${TGT} -c ${ROOTCINTINCPATHS} ${SRC}',
        name='rootcint-dict-%s' % name,
        source=source,
        target=target,
        reentrant=True,
        **kw
        )
    o.env['ROOTCINTINCPATHS'] = incpaths
    return o

### ---------------------------------------------------------------------------
def build_pymodule(self, source, **kw):
    
    # extract package name
    PACKAGE_NAME = _get_pkg_name(self)

    install_path_root = kw.get('install_path_root',
                               '${INSTALL_AREA}/python/%s' % PACKAGE_NAME)
    
    #source = waflib.Utils.to_list(source)
    pydir = self.path.find_dir('python')
    if not pydir:
        msg.info(
            'no such directory: [%s]' %
            os.path.join(self.path.abspath(), 'python')
            )
        msg.info('cannot execute [build_pymodule]')
        return
    pyfiles = pydir.ant_glob(
        '**/*',
        dir=False,
        relative_trick=True,
        )
    if 1:
        _fixup_pymodule_install(
            self,
            name = 'py-%s' % PACKAGE_NAME,
            source = pyfiles,
            install_path_root = install_path_root
            )
    else:
        self(
            features     = 'py',
            name         = 'py-%s' % PACKAGE_NAME,
            source       = pyfiles,
            install_path = '${INSTALL_AREA}/python/%s' % PACKAGE_NAME,
            )
    return

def _fixup_pymodule_install(self, name, source, install_path_root):
    # temporary hack for issue 901
    # http://code.google.com/p/waf/issues/detail?id=901
    source = waflib.Utils.to_list(source)
    pydir = self.path.get_src().find_dir('python')
    if not pydir:
        return
    dirs = {}
    for f in source:
        fname = f.path_from(pydir)
        dname = os.path.dirname(fname)
        try:
            dirs[dname].append(f)
        except KeyError:
            dirs[dname] = [f]
    for d in dirs:
        if (not d) or d == '.':
            n = name
            i = install_path_root
        else:
            n = '%s-%s' % (name, d)
            i = os.path.join(install_path_root, d)
            
        self(
            features     = 'py',
            name         = n,
            source       = dirs[d],
            install_path = i,
            )
    return

### -----------------------------------------------------------------------------
def install_joboptions(self, source, **kw):
    
    # extract package name
    PACKAGE_NAME = _get_pkg_name(self)

    jobo_dir = self.path.find_dir('share')
    jobos = jobo_dir.ant_glob('**/*', dir=False)
    
    self.install_files(
        '${INSTALL_AREA}/jobOptions/%s' % PACKAGE_NAME,
        jobos,
        cwd=jobo_dir,
        relative_trick=True
        )
    return

### -----------------------------------------------------------------------------
def install_headers(self, incdir=None, relative_trick=True, cwd=None):
    
    # extract package name
    PACKAGE_NAME = _get_pkg_name(self)
    inc_node = None
    if not incdir:
        inc_node = self.path.find_dir(PACKAGE_NAME)
        if not inc_node:
            return
    else:
        if isinstance(incdir, str):
            inc_node = self.path.find_dir(incdir)
        else:
            inc_node = incdir
            pass
        pass
    
    if isinstance(cwd, str):
        cwd = self.path.find_dir(cwd)
        
    if not inc_node:
        self.fatal('no such directory [%s] (pkg=%s)' % (incdir, PACKAGE_NAME))
        pass
    
    includes = inc_node.ant_glob('**/*', dir=False)
    self.install_files(
        '${INSTALL_AREA}/include', includes, 
        relative_trick=relative_trick,
        cwd=cwd,
        postpone=False,
        )

    incpath = waflib.Utils.subst_vars('${INSTALL_AREA}/include',self.env)
    #msg.info("--> [%s] %s" %(PACKAGE_NAME,incpath))
    self.env.append_unique('INCLUDES_%s' % PACKAGE_NAME,
                           [incpath,inc_node.parent.abspath()])
    #inc_node.parent.abspath())
    return
    
### -----------------------------------------------------------------------------
def install_scripts(self, source, **kw):
    
    # extract package name
    PACKAGE_NAME = _get_pkg_name(self)

    source = waflib.Utils.to_list(source)
    _srcs = []
    for f in source:
        _srcs.extend(self.path.ant_glob(f, dir=False))
    source = _srcs[:]
    del _srcs
    
    self.install_files(
        '${INSTALL_AREA}/bin',
        source, 
        #relative_trick=True,
        chmod=waflib.Utils.O755,
        )
    return

### -----------------------------------------------------------------------------
if 0:
    # it would be nice to automatically build *as a variant* everything,
    # based on CMTCFG...
    # bonus point: cross-compile all variants...
    #FIXME: infinite recursion on ctx.env.CMTCFG !!
    def waffle_variant(ctx):
        return ctx.env.CMTCFG

    import waflib.Build
    for cls in (waflib.Build.BuildContext,
                waflib.Build.CleanContext,
                waflib.Build.StepContext,
                waflib.Build.InstallContext): 
        cls.variant = property(waffle_variant) 

### -----------------------------------------------------------------------------
import sys
import waflib.Build
class InstallContext(waflib.Build.InstallContext):
    def __init__(self, **kw):
        super(InstallContext, self).__init__(**kw)
        return

    def execute_build(self):
        self.logger = msg
        lvl = msg.log.level
        if lvl < msg.logging.ERROR:
            msg.log.setLevel(msg.logging.ERROR)
            pass
        try:
            ret = super(InstallContext, self).execute_build()
        finally:
            msg.log.setLevel(lvl)
        return ret
    pass # class InstallContext

### -----------------------------------------------------------------------------
import sys
import waflib.Build
class UninstallContext(waflib.Build.UninstallContext):
    def __init__(self, **kw):
        super(UninstallContext, self).__init__(**kw)
        return

    def execute_build(self):
        self.logger = msg
        lvl = msg.log.level
        if lvl < msg.logging.ERROR:
            msg.log.setLevel(msg.logging.ERROR)
        try:
            ret = super(UninstallContext, self).execute_build()
        finally:
            msg.log.setLevel(lvl)
        return ret
    pass # class UninstallContext

### ---------------------------------------------------------------------------
import waflib.Build
import waflib.Scripting
import waflib.Utils

class RunCmdContext(waflib.Build.BuildContext):
    """run a command within the correct runtime environment"""
    cmd = 'run'

    def execute_build(self):
        self.logger = msg

        lvl = msg.log.level
        if lvl < msg.logging.ERROR:
            msg.log.setLevel(msg.logging.ERROR)
            pass
        try:
            ret = super(RunCmdContext, self).execute_build()
        finally:
            msg.log.setLevel(lvl)

        #msg.info("args: %s" % waflib.Options.commands)
        if not waflib.Options.commands:
            self.fatal('%s expects at least one package name. got: %s' %
                       (self.cmd, waflib.Options.commands))

        args = []
        while waflib.Options.commands:
            arg = waflib.Options.commands.pop(0)
            #msg.info("arg: %r" % arg)
            args.append(arg)
            pass
        
        #msg.info("args: %s" % args)
        ret = run_cmd_with_runtime_env(self, args)
        return ret

def _get_runtime_env(ctx):
    """return an environment suitably modified to run locally built programs
    """
    import os
    cwd = os.getcwd()
    root = os.path.realpath(ctx.options.prefix)
    root = os.path.realpath(ctx.env.INSTALL_AREA)
    bindir = os.path.join(root, 'bin')
    libdir = os.path.join(root, 'lib')
    pydir  = os.path.join(root, 'python')

    env = dict(os.environ)

    def _env_prepend(k, *args):
        v = env.get(k, '').split(os.pathsep)
        env[k] = os.pathsep.join(args)
        if v:
            env[k] = os.pathsep.join([env[k]]+v)
            pass
        return
    
    for k in ctx.env.keys():
        v = ctx.env[k]
        # reject invalid values (for an environment)
        if isinstance(v, (list,tuple)):
            continue
        # special case of PATH
        if k == 'PATH': 
            _env_prepend(k, v)
            continue
        
        env[k] = str(v)
        pass

    ## handle the shell flavours...
    if waffle_utils._is_linux(ctx):
        ppid = os.getppid()
        shell = os.path.realpath('/proc/%d/exe' % ppid)
    elif waffle_utils._is_darwin(ctx):
        ppid = os.getppid()
        shell = os.popen('ps -p %d -o %s | tail -1' % (ppid, "command")).read()
        shell = shell.strip()
        if shell.startswith('-'):
            shell = shell[1:]
    elif waffle_utils._is_windows(ctx):
        ## FIXME: ???
        shell = None
    else:
        shell = None
        pass

    # catch-all
    if not shell or "(deleted)" in shell:
        # fallback on the *login* shell
        shell = os.environ.get("SHELL", "/bin/sh")
        pass

    env['SHELL'] = shell
    
        
    # joboptions support
    _env_prepend('JOBOPTSEARCHPATH',
                 '.',
                 os.path.join(root, 'jobOptions'))

    # clid and misc. support
    _env_prepend('DATAPATH',
                 '.',
                 os.path.join(root, 'share'))
    
    # FIXME: this should probably be done elsewhere (and better)
    #env['ROOTSYS'] = os.getenv('ROOTSYS', ctx.env.ROOTSYS)

    # path
    _env_prepend('PATH', bindir)

    # lib
    _env_prepend('LD_LIBRARY_PATH', libdir, *ctx.env.LIBPATH)

    # dy-ld-library
    if waffle_utils._is_darwin(ctx):
        _env_prepend('DYLD_LIBRARY_PATH', libdir, *ctx.env.LIBPATH)
    else:
        env['DYLD_LIBRARY_PATH'] = ''
        pass

    # pythonpath
    if ctx.env.ROOTSYS:
        _env_prepend('PYTHONPATH', os.path.join(ctx.env.ROOTSYS,'lib'))
        pass
    _env_prepend('PYTHONPATH', pydir)

    ## for k in ('PATH',
    ##           'LD_LIBRARY_PATH',
    ##           'PYTHONPATH',
    ##           ):
    ##     msg.info('env[%s]: %r' % (k,env[k]))

    for k in env:
        v = env[k]
        if not isinstance(v, str):
            msg.warning('env[%s]=%r (%s)' % (k,v,type(v)))
            del env[k]
            
    return env

def run_cmd_with_runtime_env(ctx, cmds):
    # make sure we build first"
    # waflib.Scripting.run_command('install')
    
    import os
    import tempfile
    import textwrap

    #env = ctx.env
    cwd = os.getcwd()
    root = os.path.realpath(ctx.options.prefix)
    # FIXME: we should use the *local* install-area to be
    #        able to test the runtime w/o requiring an actual install!!
    root = os.path.realpath(ctx.env['INSTALL_AREA'])
    bindir = os.path.join(root, 'bin')
    libdir = os.path.join(root, 'lib')
    pydir  = os.path.join(root, 'python')

    # get the runtime...
    env = _get_runtime_env(ctx)

    for k in env:
        v = env[k]
        if not isinstance(v, str):
            ctx.fatal('env[%s]=%r (%s)' % (k,v,type(v)))
            pass
        pass

    shell_cmd = cmds[:]
    import pipes # FIXME: use shlex.quote when available ?
    from string import Template as str_template
    cmds=' '.join(pipes.quote(str_template(s).safe_substitute(env)) for s in cmds)

    retval = subprocess.Popen(
        cmds,
        env=env,
        cwd=os.getcwd(),
        shell=True,
        ).wait()

    if retval:
        signame = None
        if retval < 0: # signal?
            import signal
            for name, val in vars(signal).iteritems():
                if len(name) > 3 and name[:3] == 'SIG' and name[3] != '_':
                    if val == -retval:
                        signame = name
                        break
        if signame:
            raise waflib.Errors.WafError(
                "Command '%s' terminated with signal %s." % (cmds, signame))
        else:
            raise waflib.Errors.WafError(
                "Command '%s' exited with code %i" % (cmds, retval))
        pass
    return retval

### ---------------------------------------------------------------------------
import waflib.Build
import waflib.Scripting
import waflib.Utils

class IShellContext(waflib.Build.BuildContext):
    """run an interactive shell with an environment suitably modified to run locally built programs"""
    cmd = 'shell'
    #fun = 'shell'

    def execute_build(self):
        self.logger = msg
        lvl = msg.log.level
        if lvl < msg.logging.ERROR:
            msg.log.setLevel(msg.logging.ERROR)
            pass
        try:
            ret = super(IShellContext, self).execute_build()
        finally:
            msg.log.setLevel(lvl)
        ret = ishell(self)
        return ret
    
def ishell(ctx):
    # make sure we build first"
    # waflib.Scripting.run_command('install')
    
    import os
    import tempfile
    import textwrap

    #env = ctx.env
    cwd = os.getcwd()
    root = os.path.realpath(ctx.options.prefix)
    root = os.path.realpath(ctx.env['INSTALL_AREA'])
    bindir = os.path.join(root, 'bin')
    libdir = os.path.join(root, 'lib')
    pydir  = os.path.join(root, 'python')

    # get the runtime...
    env = _get_runtime_env(ctx)


    ## handle the shell flavours...
    if waffle_utils._is_linux(ctx):
        ppid = os.getppid()
        shell = os.path.realpath('/proc/%d/exe' % ppid)
    elif waffle_utils._is_darwin(ctx):
        ppid = os.getppid()
        shell = os.popen('ps -p %d -o %s | tail -1' % (ppid, "command")).read()
        shell = shell.strip()
        if shell.startswith('-'):
            shell = shell[1:]
    elif waffle_utils._is_windows(ctx):
        ## FIXME: ???
        shell = None
    else:
        shell = None
        pass

    # catch-all
    if not shell or "(deleted)" in shell:
        # fallback on the *login* shell
        shell = os.environ.get("SHELL", "/bin/sh")

    tmpdir = tempfile.mkdtemp(prefix='waffle-env-')
    dotrc = None
    dotrc_fname = None
    shell_cmd = [shell,]
    msg.info("---> shell: %s" % shell)

    if 'zsh' in os.path.basename(shell):
        env['ZDOTDIR'] = tmpdir
        dotrc_fname = os.path.join(tmpdir, '.zshrc')
        shell_cmd.append('-i')

    elif 'bash' in os.path.basename(shell):
        dotrc_fname = os.path.join(tmpdir, '.bashrc')
        shell_cmd += [
            '--init-file',
            dotrc_fname,
            '-i',
            ]
    elif 'csh' in os.path.basename(shell):
        msg.info('sorry, c-shells not handled at the moment: fallback to bash')
        dotrc_fname = os.path.join(tmpdir, '.bashrc')
        shell_cmd += [
            '--init-file',
            dotrc_fname,
            '-i',
            ]
    else:
        # default to dash...
        dotrc_fname = os.path.join(tmpdir, '.bashrc')
        shell_cmd += [
            #'--init-file',
            #dotrc_fname,
            '-i',
            ]
        env['ENV'] = dotrc_fname
        pass

    # FIXME: this should probably be done elsewhere (and better)
    #env['ROOTSYS'] = os.getenv('ROOTSYS', ctx.env.ROOTSYS)
    if ctx.env['BUNDLED_ROOT']:
        rootsys_setup = textwrap.dedent('''
        pushd ${ROOTSYS}
        echo ":: sourcing \${ROOTSYS}/bin/thisroot.sh..."
        source ./bin/thisroot.sh
        popd
        ''')

    else:
        rootsys_setup = ''
        pass
    ###


    dotrc = open(dotrc_fname, 'w')
    dotrc.write(textwrap.dedent(
        '''
        ## automatically generated by waffle-shell
        echo ":::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::"
        echo ":: launching a sub-shell with the correct mana environment..."
        echo ":: sourcing ${HOME}/%(dotrc_fname)s..."
        source ${HOME}/%(dotrc_fname)s
        echo ":: sourcing ${HOME}/%(dotrc_fname)s... [done]"

        # adjust env. variables
        export PATH=%(waffle_path)s
        export LD_LIBRARY_PATH=%(waffle_ld_library_path)s
        export DYLD_LIBRARY_PATH=%(waffle_dyld_library_path)s

        # for ROOT
        ROOTSYS=%(rootsys)s
        %(rootsys_setup)s

        # setup PYTHONPATH *after* ROOT so "we" win
        export PYTHONPATH=%(waffle_pythonpath)s

        # env. variables for athena
        JOBOPTSEARCHPATH=%(waffle_joboptsearchpath)s
        DATAPATH=.:%(waffle_datapath)s

        # customize PS1 so we know we are in a waffle subshell
        export PS1="[waf] ${PS1}"

        echo ":: mana environment... [setup]"
        echo ":: hit ^D or exit to go back to the parent shell"
        echo ":::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::"
        ''' % {
            'dotrc_fname' : os.path.basename(dotrc_fname),
            'waffle_path': env['PATH'],
            'waffle_ld_library_path': env['LD_LIBRARY_PATH'],
            'waffle_dyld_library_path': env['DYLD_LIBRARY_PATH'],
            'waffle_pythonpath': env['PYTHONPATH'],
            'waffle_joboptsearchpath': env['JOBOPTSEARCHPATH'],
            'waffle_datapath': env['DATAPATH'],
            'rootsys':  env['ROOTSYS'],
            'rootsys_setup': rootsys_setup,
            }
        ))
    dotrc.flush()
    dotrc.close()

    for k in env:
        v = env[k]
        if not isinstance(v, str):
            ctx.fatal('env[%s]=%r (%s)' % (k,v,type(v)))
            

    retval = subprocess.Popen(
        shell_cmd,
        env=env,
        cwd=os.getcwd()
        ).wait()

    try:
        import shutil
        shutil.rmtree(tmpdir)
    except Exception:
        msg.verbose('could not remove directory [%s]' % tmpdir)
        pass

    if retval:
        signame = None
        if retval < 0: # signal?
            import signal
            for name, val in vars(signal).iteritems():
                if len(name) > 3 and name[:3] == 'SIG' and name[3] != '_':
                    if val == -retval:
                        signame = name
                        break
        if signame:
            raise waflib.Errors.WafError(
                "Command %s terminated with signal %s." % (shell_cmd, signame))
        else:
            raise waflib.Errors.WafError(
                "Command %s exited with code %i" % (shell_cmd, retval))
    return retval



### -----------------------------------------------------------------------------
def waffle_do_post_build(self):
    """
    schedule the post-build actions
    """
    ctx = self
    #msg.info("post-build")
    #bld_area = self.env['BUILD_INSTALL_AREA']
    #msg.info(":: bld-area: %s" % bld_area)
    node = ctx.bldnode.make_node(WAFFLE_PROJECT_INFO)
    ctx.env.stash()
    env = ctx.env
    # irrelevant
    del env.WAFFLE_ROOT
    #
    env.store(node.abspath())
    node.sig = waflib.Utils.h_file(node.abspath())

    #msg.info('project infos: %s' % node.abspath())

    ctx.install_files(
        '${INSTALL_AREA}',
        [node],
        #cwd=jobo_dir,
        #relative_trick=True
        )
    ctx.env.revert()
    return

### ---------------------------------------------------------------------------
import waflib.Context
waflib.Context.Context.find_subpackages = find_subpackages

import waflib.Options
waflib.Options.OptionsContext.find_subpackages = find_subpackages

import waflib.Configure
waflib.Configure.ConfigurationContext.find_subpackages = find_subpackages
waflib.Configure.ConfigurationContext.waffle_utils = waffle_utils

import waflib.Build
waflib.Build.BuildContext.find_subpackages = find_subpackages
waflib.Build.BuildContext.waffle_utils = waffle_utils
waflib.Build.BuildContext.build_complib = build_complib
waflib.Build.BuildContext.build_linklib = build_linklib
waflib.Build.BuildContext.build_reflex_dict = build_reflex_dict
waflib.Build.BuildContext.build_app = build_app

waflib.Build.BuildContext.build_pymodule = build_pymodule
waflib.Build.BuildContext.install_joboptions = install_joboptions
waflib.Build.BuildContext.install_headers = install_headers
waflib.Build.BuildContext.install_scripts = install_scripts

waflib.Build.BuildContext.waffle_do_post_build = waffle_do_post_build

