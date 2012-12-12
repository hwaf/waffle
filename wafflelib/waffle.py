# waffle.py
# a few waf functions to help building gaudi and athena
# a possible CMT replacement

# imports ---------------------------------------------------------------------
import optparse
import os
import os.path
import os.path as osp
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

    ctx.load('hep-waftools-base', tooldir='hep-waftools')

    
    pkgs = find_suboptions(WAFFLE_PKGDIR)
    ctx.recurse(pkgs, mandatory=False)
    return

@conf
def configure(ctx):
    msg.debug('configure...')
    import os
    import os.path

    ctx.load('hep-waftools-base',   tooldir='hep-waftools')
    ctx.load('hep-waftools-system', tooldir='hep-waftools')
    
    g_module = waflib.Context.g_module

    # taken from hepwaf: PREFIX
    # taken from hepwaf: HEPWAF_PROJECT_NAME
    # taken from hepwaf: CMTCFG
    # taken from hepwaf: CMTPKGS
    # taken from hepwaf: INSTALL_AREA
    
    ctx.env.VERSION = g_module.VERSION

    ctx.load('hwaf', tooldir='hep-waftools')
    ctx.hepwaf_configure()

    #print ctx.env.CPPFLAGS
    if waflib.Options.options.usrcfg:
        # store the configuration...
        ctx.env.store(WAFFLE_CFG)
        pass

    #ctx.setenv(ctx.env.CMTCFG, env=ctx.env)
    return

@conf
def build(ctx):
    #ctx.add_pre_fun(pre) 
    #ctx.add_post_fun(waffle_do_post_build)

    ctx.load('hwaf', tooldir='hep-waftools')
    ctx.hepwaf_build()
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
    return self.hepwaf_find_subpackages(directory)

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
waflib.Build.BuildContext.build_app = build_app

waflib.Build.BuildContext.build_pymodule = build_pymodule
waflib.Build.BuildContext.install_joboptions = install_joboptions
waflib.Build.BuildContext.install_headers = install_headers
waflib.Build.BuildContext.install_scripts = install_scripts

waflib.Build.BuildContext.waffle_do_post_build = waffle_do_post_build

