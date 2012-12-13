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

waflib.Build.BuildContext.waffle_do_post_build = waffle_do_post_build

