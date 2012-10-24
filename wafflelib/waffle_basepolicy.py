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
import waflib.extras.waffle_utils

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
def configure_policy(ctx):
    # compiler ---
    if waffle_utils._is_darwin(ctx):
        # we really want .so and not .dylib...
        for shlib in ['cshlib', 'cxxshlib']:
            linkflags = ctx.env['LINKFLAGS_%s'%shlib][:]
            ctx.env['LINKFLAGS_%s'%shlib] = [l.replace('-dynamiclib','-shared')
                                             for l in linkflags]
            ctx.env['%s_PATTERN'%shlib]      = 'lib%s.so'

        # and no stinking current_version either
        for flag in ['CXXFLAGS_cxxshlib','CFLAGS_cshlib']:
            _flags = ctx.env[flag][:]
            if '-compatibility_version' in _flags:
                _idx = _flags.index('-compatibility_version')
                # +2 b/c it is of the form: ['-compatibility_version','1',...]
                ctx.env[flag] = _flags[:_idx]+_flags[_idx+2:]
            _flags = ctx.env[flag][:]
            if '-current_version' in _flags:
                _idx = _flags.index('-current_version')
                # +2 b/c it is of the form: ['-current_version','1',...]
                ctx.env[flag] = _flags[:_idx]+_flags[_idx+2:]
        
    # preprocessor ---
    ctx.env.append_unique(
        'CPPFLAGS',
        ['-DDISABLE_ALLOC',
         '-DHAVE_NEW_IOSTREAMS',
         '-DATHENA_VERSION=1',
         '-D_GNU_SOURCE',
         '-DGAUDI_V20_COMPAT',
         '-DATLAS_GAUDI_V21',
         # FIXME: only meaningful for slc6-gcc4x...
         '-D__USE_XOPEN2K8'
         ]
        )
    if waffle_utils._is_opt(ctx):
        ctx.env.append_unique(
            'CPPFLAGS',
            ['-DNDEBUG=1',
             ]
            )
    import sys
    if waffle_utils._is_linux(ctx):
        ctx.env.append_unique('CPPFLAGS', ['-Dlinux'])

    def subst(v):
        return waflib.Utils.subst_vars(v, ctx.env)
    
    # C compiler flags -----------------------------------------------
    if waffle_utils._is_windows(ctx):
        # dummy
        pass
    else:
        ctx.env.append_value(
            'COMMONFLAGS',
            ['-O2', '-fPIC',
             '-pipe', '-ansi', '-Wall', '-W', '-pthread'])

        if waffle_utils._is_dbg(ctx):
            ctx.env.append_value('COMMONFLAGS', ['-g'])

        if waffle_utils._is_32b(ctx):
            ctx.env.append_value('COMMONFLAGS', ['-m32'])
        else:
            ctx.env.append_value('COMMONFLAGS', ['-m64'])

        ctx.env.append_unique('CCFLAGS', subst('${COMMONFLAGS}').split())
        ctx.env.append_unique('CFLAGS', subst('${COMMONFLAGS}').split())

        # C++ compiler flags ---------------------------------------------
        ctx.env.append_unique('CXXFLAGS', subst('${COMMONFLAGS}').split())
        ctx.env.append_unique(
            'CXXFLAGS',
            [#'-std=c++0x',
             '-Wno-deprecated',
             ]
            )

        if waffle_utils._is_darwin(ctx):
            ctx.env.append_unique(
                'CXXFLAGS',
                ['-Wno-non-virtual-dtor',
                 '-Wno-long-long',
                 '-Wwrite-strings',
                 '-Wpointer-arith',
                 '-Woverloaded-virtual',
                 '-ftemplate-depth-512',
                 '-fmessage-length=0',
                 ]
                )
        # Fortran compiler flags -----------------------------------------
        ctx.env.append_unique('FCFLAGS', subst('${COMMONFLAGS}').split())

        # link flags
        if waffle_utils._is_dbg(ctx):
            ctx.env.append_unique('LINKFLAGS', ['-g',])
        if waffle_utils._is_32b(ctx):
            ctx.env.append_unique('LINKFLAGS', ['-m32',])
        else:
            ctx.env.append_unique('LINKFLAGS', ['-m64',])

    # shared library link flags
    if waffle_utils._is_dbg(ctx) and not waffle_utils._is_windows(ctx):
        ctx.env.append_unique('SHLINKFLAGS', ['-g'])

    if waffle_utils._is_linux(ctx):
        ctx.env.append_unique(
            'SHLINKFLAGS',
            ['-Wl,--hash-style=both',
             '-Wl,--as-needed',
             '-Wl,--no-undefined',
             '-ldl'
             ]
            )
    elif waffle_utils._is_darwin(ctx):
        ctx.env.append_unique(
            'SHLINKFLAGS',
            ['-Wl,-dead_strip_dylibs',
             #'-Wl,--as-needed',
             #'-Wl,--no-undefined',
             # darwin linker doesn't know about --hash-style=both
             #'-Wl,--hash-style=both', 
             '-ldl'
             ]
            )
    elif waffle_utils._is_windows(ctx):
        #FIXME: what should the defaults be ?
        ctx.env.append_unique('SHLINKFLAGS', [])
        msg.warn('**FIXME**: dummy SHLINKFLAGS value for windows')

    else:
        raise RuntimeError('unhandled platform [%s]' % sys.platform)
    
    if waffle_utils._is_64b(ctx) and waffle_utils._is_linux(ctx):
        ctx.env.append_unique(
            'SHLINKFLAGS',            
            [
                # align at 4096b boundaries instead of 1Mb
                '-Wl,-z,max-page-size=0x1000',
                ]
            )
        
    # LDFLAGS: options for the linker
    # LIBS: -l options (library names) to pass to the linker
    
    # library path
    import os
    if waffle_utils._is_linux(ctx):
        if waffle_utils._is_64b(ctx):
            ctx.env.append_unique(
                'LIBPATH',
                [
                    # no need: implicitly taken from ldconfig...
                    #'/usr/lib64',
                 ]
                )
        else:
            ctx.env.append_unique(
                'LIBPATH',
                ['/usr/lib',
                 ]
                )
            pass
        pass
    elif waffle_utils._is_darwin(ctx):
        ctx.env.append_unique(
            'LIBPATH',
            ['/usr/lib',
             ]
            )
        pass
    
    if 'LD_LIBRARY_PATH' in os.environ:
        ll = []
        for l in os.getenv('LD_LIBRARY_PATH','.').split(os.pathsep):
            if l: ll.append(l)
            else: ll.append('.')
        ctx.env.append_unique(
            'LD_LIBRARY_PATH', 
            ll
            )
        del ll
        
    if waffle_utils._is_darwin(ctx):
        ll = []
        for l in os.getenv('LD_LIBRARY_PATH','.').split(os.pathsep):
            # this can confuse macports...
            if not l.startswith(('/usr','/opt/local')):
                if l: ll.append(l)
                else: ll.append('.')
        ctx.env.append_unique('DYLD_LIBRARY_PATH',
                              ll)
        del ll

    ctx.find_program('genCLIDDB.exe', var='GENCLIDDB',  mandatory=False)
    ctx.find_program('genconf.exe',   var='GENCONF',    mandatory=False)

    return

@conf
def configure_python(ctx, min_version=None):
    # FIXME: take it from a user configuration file ?
    if min_version is None:
        min_version=(2,6)
        pass
    if not ctx.env.PYTHON:
        # FIXME: force python2. needed to be done *before* 'ctx.load(python)'
        try:    ctx.find_program('python2', var='PYTHON')
        except: ctx.find_program('python',  var='PYTHON')
    
        ctx.load('python')
        ctx.check_python_version(min_version)
        # we remove the -m32 and -m64 options from these flags as they
        # can confuse 'check_python_headers' on darwin...
        save_flags = {}
        for n in ('CXXFLAGS','CFLAGS', 'LINKFLAGS'):
            save_flags[n] = ctx.env[n][:]
        if waffle_utils._is_darwin(ctx):
            for n in ('CXXFLAGS','CFLAGS', 'LINKFLAGS'):
                ctx.env[n] = []
                for v in save_flags[n]:
                    if v not in ('-m32', '-m64'):
                        ctx.env.append_unique(n, [v])
            
            pass
        
        ctx.check_python_headers()

        # restore these flags:
        for n in ('CXXFLAGS','CFLAGS', 'LINKFLAGS'):
            ctx.env[n] = save_flags[n][:]
            pass
        pass
    
    # hack for ROOT on macosx: LIBPATH_PYEMBED won't point at
    # the directory holding libpython.{so,a}
    pylibdir = ctx.env['LIBPATH_PYEMBED']
    cmd = waflib.Utils.subst_vars('${PYTHON_CONFIG}', ctx.env)
    for arg in [#('--includes', 'INCLUDES'),
                ('--ldflags', 'LIBPATH'),
                #('--cflags', 'CXXFLAGS'),
                ]:
        o = waflib.Utils.subprocess.check_output(
            [cmd, arg[0]]
            )
        o = str(o)
        ctx.parse_flags(o, 'python')
    pylibdir = waflib.Utils.to_list(ctx.env['LIBPATH_python'])[:]
    
    # rename the uselib variables from PYEMBED to python
    waffle_utils.copy_uselib_defs(ctx, 'python', 'PYEMBED')

    # FIXME: hack for python-lcg.
    # python-config --ldflags returns the wrong directory .../config...
    if pylibdir and \
           (os.path.exists(os.path.join(pylibdir[0],
                                       'libpython%s.so'%ctx.env['PYTHON_VERSION']))
            or
            os.path.exists(os.path.join(pylibdir[0],
                                       'libpython%s.a'%ctx.env['PYTHON_VERSION']))):
        ctx.env['LIBPATH_python'] = pylibdir[:]
    else:
        # PYEMBED value should be ok.
        pass
    
    # disable fat/universal archives on darwin
    if waffle_utils._is_darwin(ctx):
        for n in ('CFLAGS', 'CXXFLAGS', 'LINKFLAGS'):
            args = []
            indices = []
            for i,a in enumerate(ctx.env['%s_python'%n]):
                if a == '-arch':
                    # removes ['-arch', 'x86_64']
                    indices.append(i)
                    indices.append(i+1)
            args = [a for i,a in enumerate(ctx.env['%s_python'%n])
                    if not (i in indices)]
            ctx.env['%s_python'%n] = args[:]
            
    # make sure the correct arch is built (32/64 !!)
    arch_flag = []
    if waffle_utils._is_darwin(ctx):
        if waffle_utils._is_32b(ctx): arch_flag = ['-arch', 'i386']
        else:                         arch_flag = ['-arch', 'x86_64']
    elif waffle_utils._is_linux(ctx): 
        if waffle_utils._is_32b(ctx): arch_flag = ['-m32',]
        else:                         arch_flag = ['-m64',]
    else:
        pass
    
    for n in ('CFLAGS', 'CXXFLAGS', 'LINKFLAGS'):
        ctx.env.append_unique('%s_python'%n, arch_flag)
        
    # disable the creation of .pyo files
    ctx.env['PYO'] = 0

    # retrieve the prefix
    cmd = [ctx.env.PYTHON_CONFIG, "--prefix"]
    lines=ctx.cmd_and_log(cmd).split()
    ctx.env["PYTHON_PREFIX"] = lines[0]
    
    return

    
@conf
def error_handler(fct, exc):
    msg.warn ("-- handling error [%r]" % (exc,))
    msg.warn ("--   fct: %r" % (fct,))
    return waflib.Configure.BREAK


waflib.Tools.ccroot.USELIB_VARS['gen_reflex'] = set(['GCCXML_FLAGS', 'DEFINES', 'INCLUDES', 'CPPFLAGS', 'LIB'])

@feature('gen_reflex')
@after_method('apply_incpaths')
def gen_reflex_dummy(self):
    pass

@extension('.h')
def gen_reflex_hook(self, node):
    "Bind the .h file extension to the creation of a genreflex instance"
    source = node.name
    out_node_dir = self.path.get_bld().make_node(
        "_reflex_dicts").make_node(
        self.env['GENREFLEX_DICTNAME']
        )
    out_node_dir.mkdir()
    out_node = out_node_dir.make_node("%s.cxx" % source)
    dsomap_name = self.env['GENREFLEX_DSOMAP'].replace('--rootmap=','')
    dsomap_node = out_node_dir.make_node(dsomap_name)
    tsk = self.create_task('gen_reflex', node, [out_node,dsomap_node])
    #tsk = self.create_task('gen_reflex', node, out_node)
    self.source += tsk.outputs
    merge_dsomap_hook(self, dsomap_node).set_run_after(tsk)

# classes ---
class gen_reflex(waflib.Task.Task):
    vars = ['GENREFLEX', 'DEFINES', 'GCCXML_FLAGS', 'CPPFLAGS', 'INCLUDES']
    color= 'BLUE'
    run_str = '${GENREFLEX} ${SRC} -s ${GENREFLEX_SELECTION} -o ${TGT[0].abspath()} ${GCCXML_FLAGS} ${CPPPATH_ST:INCPATHS} ${DEFINES_ST:DEFINES} ${GENREFLEX_DSOMAP} ${GENREFLEX_DSOMAPLIB}'
    ext_in = ['.h',]
    ext_out= ['.cxx', '.dsomap']
    reentrant = True
    shell = False
    #shell = True

    def exec_command(self, cmd, **kw):
        cwd_node = self.outputs[0].parent
        out = self.outputs[0].change_ext('.genreflex.log')
        fout_node = cwd_node.find_or_declare(out.name)
        fout = open(fout_node.abspath(), 'w')
        kw['stdout'] = fout
        kw['stderr'] = fout
        rc = waflib.Task.Task.exec_command(self, cmd, **kw)
        if rc != 0:
            msg.error("** error running [%s]" % ' '.join(cmd))
            msg.error(fout_node.read())
        return rc
        
    def runnable_status(self):
        for tsk in self.run_after:
            if not getattr(tsk, 'hasrun', False):
                return waflib.Task.ASK_LATER
        for in_node in self.inputs:
            try:
                os.stat(in_node.abspath())
            except:
                return waflib.Task.ASK_LATER
        for out_node in self.outputs:
            try:
                os.stat(out_node.abspath())
            except:
                return waflib.Task.RUN_ME
        return waflib.Task.Task.runnable_status(self)

### ---------------------------------------------------------------------------
@feature('gen_map')
@after('symlink_tsk')
def schedule_gen_map(self):
    lnk_task = getattr(self, 'link_task', None)
    if not lnk_task:
        return
    for n in lnk_task.outputs:
        gen_map_hook(self, n)
    pass

@after('symlink_tsk')
def gen_map_hook(self, node):
    "Bind the .so file extension to the creation of a genmap task"
    dso = node.name
    bld_node = node.get_bld().parent
    dso_ext = waffle_utils._dso_ext(self)
    out_node = bld_node.make_node(dso.replace(dso_ext,".dsomap"))
    tsk = self.create_task('gen_map', node, out_node)
    self.source += tsk.outputs
    merge_dsomap_hook(self, out_node).set_run_after(tsk)

class gen_map(waflib.Task.Task):
    vars = ['GENMAP', 'DEFINES', 'CPPFLAGS', 'INCLUDES']
    color= 'BLUE'
    run_str = '${GENMAP} -input-library ${SRC[0].name} -o ${TGT[0].name}'
    ext_in  = ['.so']
    ext_out = ['.dsomap']
    shell = False
    reentrant = True
    after = ['cxxshlib', 'cxxprogram', 'symlink_tsk']

    def exec_command(self, cmd, **kw):
        cwd_node = self.outputs[0].parent
        out = self.outputs[0].change_ext('.genmap.log')
        fout_node = cwd_node.find_or_declare(out.name)
        fout = open(fout_node.abspath(), 'w')
        kw['stdout'] = fout
        kw['stderr'] = fout
        kw['env'] = waffle_utils._get_env_for_subproc(self)
        kw['cwd'] = self.inputs[0].get_bld().parent.abspath()
        rc = waflib.Task.Task.exec_command(self, cmd, **kw)
        if rc != 0:
            msg.error("** error running [%s]" % ' '.join(cmd))
            msg.error(fout_node.read())
        return rc

    def runnable_status(self):
        status = waflib.Task.Task.runnable_status(self)
        if status == waflib.Task.ASK_LATER:
            return status
        
        for out_node in self.outputs:
            try:
                os.stat(out_node.abspath())
            except:
                return waflib.Task.RUN_ME
        return status
    
### ----------------------------------------------------------------------------
@feature('gen_conf')
@after('symlink_tsk')
def schedule_gen_conf(self):
    lnk_task = getattr(self, 'link_task', None)
    if not lnk_task:
        return
    for n in lnk_task.outputs:
        gen_conf_hook(self, n)
    pass

@after('symlink_tsk')
def gen_conf_hook(self, node):
    "Bind the .dsomap file extension to the creation of a genconf task"
    dso = self.env['GENCONF_LIBNAME']
    bld_node = node.get_bld().parent
    pkg_name = bld_node.name # FIXME!!
    genconf_dir_node = bld_node.make_node('genConf').make_node(pkg_name)
    self.env['GENCONF_OUTPUTDIR'] = genconf_dir_node.abspath()
    genconf_node = genconf_dir_node.make_node('%sConf.py' % dso)
    initpy_node = genconf_dir_node.make_node('__init__.py')
    confdb_node = genconf_dir_node.make_node('%s_confDb.py' % dso)
    tsk = self.create_task('gen_conf',
                           node,
                           [genconf_node,genconf_dir_node,initpy_node,confdb_node])
    # schedule the merge of confdb.py files
    merge_confdb_hook(self, confdb_node).set_run_after(tsk)

    # schedule the installation of py-files
    src_node = self.path.get_src()
    py_dir = src_node.find_dir('python')
    py_files = [genconf_node, confdb_node]
    if not py_dir:
        py_files.append(initpy_node)
    PACKAGE_NAME = self.env['PACKAGE_NAME']
    self.bld.new_task_gen(
        features='py',
        name    ='py-genconf-%s' % PACKAGE_NAME,
        source  = py_files,
        install_path = '${INSTALL_AREA}/python/%s' % PACKAGE_NAME,
        )

class gen_conf(waflib.Task.Task):
    vars = ['GENCONF', 'DEFINES', 'CPPFLAGS', 'INCLUDES']
    color= 'BLUE'
    ext_in  = ['.bin', '.so']
    ext_out = ['.py']
    shell = False
    reentrant = True
    after = ['cxxshlib', 'cxxprogram', 'symlink_tsk', 'gen_map']
    depends_on = ['genconf',]
    
    def run(self):
        import os
        if not self.env['GENCONF']:
            # if GENCONF isn't set then this means GaudiKernel is
            # part of the local workarea.
            # retrieve the task for genconf.exe and extract its absolute path
            tgt = self.generator.bld.get_tgen_by_name('genconf')
            # tgt.post()
            genconf_exe = tgt.link_task.outputs[0].abspath()
            self.env['GENCONF'] = genconf_exe
            pass
    
        cmd = '${GENCONF} -p ${PACKAGE_NAME} -i %s -o ${GENCONF_OUTPUTDIR}' % (
            self.inputs[0].name,
            )
        cmd = waflib.Utils.subst_vars(cmd, self.env)

        bld_node = self.inputs[0].parent.get_bld()
    
        o = self.outputs[0].change_ext('.genconf.log')
        fout_node = bld_node.find_or_declare(o.name)
        fout = open(fout_node.abspath(), 'w')
        env = waffle_utils._get_env_for_subproc(self)
        rc = self.generator.bld.exec_command(
            cmd,
            stdout=fout,
            stderr=fout,
            env=env
            )
        if rc != 0:
            msg.error("** error running [%s]" % cmd)
            msg.error(fout_node.read())
        return rc
    
### ----------------------------------------------------------------------------
@feature('gen_cliddb')
@after('merge_dsomap')
def schedule_gen_cliddb(self):
    lnk_task = getattr(self, 'link_task', None)
    if not lnk_task:
        return
    for n in lnk_task.outputs:
        gen_cliddb_hook(self, n)
    pass

@after('symlink_tsk')
def gen_cliddb_hook(self, node):
    "Bind the .so file extension to the creation of a gencliddb task"
    dso = self.env['GENCLIDDB_LIB_NAME']
    bld_node = node.get_bld().parent
    pkg_name = bld_node.name # FIXME!!
    out = bld_node.make_node("%s_clid.db" % dso)
    tsk = self.create_task('gen_cliddb',
                           node,
                           [out])
    # schedule the merge of clid.db files
    merge_cliddb_hook(self, out).set_run_after(tsk)

class gen_cliddb(waflib.Task.Task):
    vars = ['GENCLIDDB', 'DEFINES', 'CPPFLAGS', 'INCLUDES']
    color= 'BLUE'
    ext_in  = ['.bin', '.so']
    ext_out = ['clid.db']
    shell = False
    reentrant = True
    after = ['cxxshlib', 'cxxprogram', 'symlink_tsk',
             'merge_dsomap', 'merge_confdb',
             ]
    depends_on = ['genCLIDDB',
                  'complib-CLIDComps',
                  ]

    def runnable_status(self):
        status = waflib.Task.Task.runnable_status(self)
        if status == waflib.Task.ASK_LATER:
            return status
        
        import os
        for in_node in self.inputs:
            try:
                os.stat(in_node.abspath())
            except:
                msg.debug("::missing input [%s]" % in_node.abspath())
                return waflib.Task.ASK_LATER

        for node in self.outputs:
            try:
                os.stat(node.abspath())
            except:
                msg.debug("::missing output [%s]" % node.abspath())
                return waflib.Task.RUN_ME
        return status
        
    def run(self):
        import os
        if not self.env['GENCLIDDB']:
            # if GENCLIDDB isn't set then this means AthenaKernel is
            # part of the local workarea.
            # retrieve the task for genconf.exe and extract its absolute path
            tgt = self.generator.bld.get_tgen_by_name('genCLIDDB')
            # tgt.post()
            gencliddb_exe = tgt.link_task.outputs[0].abspath()
            self.env['GENCLIDDB'] = gencliddb_exe
            pass
    
        cmd = '${GENCLIDDB} -p ${PACKAGE_NAME} -o %s' % (
            self.outputs[0].abspath(),
            )
        cmd = waflib.Utils.subst_vars(cmd, self.env)
        #cmd = 'echo ${LD_LIBRARY_PATH}; '+cmd
        bld_node = self.inputs[0].parent.get_bld()
    
        o = self.outputs[0].change_ext('.gencliddb.log')
        fout_node = bld_node.find_or_declare(o.name)
        fout = open(fout_node.abspath(), 'w')
        env = waffle_utils._get_env_for_subproc(self)
        rc = self.generator.bld.exec_command(
            cmd,
            stdout=fout,
            stderr=fout,
            env=env
            )
        if rc != 0:
            msg.error("** error running [%s]" % cmd)
            msg.error(fout_node.read())
        return rc
    
### ---------------------------------------------------------------------------
g_dsomap_merger = None
@feature('merge_dsomap')
def schedule_merge_dsomap(self):
    #bld_area = self.env['BUILD_INSTALL_AREA']
    pass

@extension('.dsomap')
def merge_dsomap_hook(self, node):
    global g_dsomap_merger
    if g_dsomap_merger is None:
        import os
        bld_area = os.path.basename(self.env['BUILD_INSTALL_AREA'])
        bld_node = self.bld.bldnode.find_dir(bld_area)
        out_node = bld_node.make_node('lib').make_node(
            'project_merged.rootmap')
        g_dsomap_merger = self.create_task('merge_dsomap', node, out_node)
        self.bld.install_files(
            '${INSTALL_AREA}/lib',
            out_node,
            relative_trick=False
            )
    else:
        g_dsomap_merger.inputs.append(node)
    return g_dsomap_merger

class merge_dsomap(waflib.Task.Task):
    color='PINK'
    ext_in = ['.dsomap']
    ext_out= ['.rootmap']
    after = ['gen_map', 'gen_reflex', 'symlink_tsk']
    run_str = 'cat ${SRC} > ${TGT}'
    shell = True

    def runnable_status(self):
        status = waflib.Task.Task.runnable_status(self)
        if status == waflib.Task.ASK_LATER:
            return status
        
        import os
        for in_node in self.inputs:
            try:
                os.stat(in_node.abspath())
            except:
                msg.debug("::missing input [%s]" % in_node.abspath())
                return waflib.Task.ASK_LATER
        return waflib.Task.RUN_ME
    
### ---------------------------------------------------------------------------
g_confdb_merger = None
@feature('merge_confdb')
def schedule_merge_confdb(self):
    pass

@extension('_confDb.py')
def merge_confdb_hook(self, node):
    global g_confdb_merger
    if g_confdb_merger is None:
        import os
        bld_area = os.path.basename(self.env['BUILD_INSTALL_AREA'])
        bld_node = self.bld.bldnode.find_dir(bld_area)
        py_node = bld_node.make_node('python')
        py_node.mkdir()
        out_node = py_node.make_node('project_merged_confDb.py')
        g_confdb_merger = self.create_task('merge_confdb', node, out_node)
        self.bld.install_files(
            '${INSTALL_AREA}/python',
            out_node,
            relative_trick=False
            )
    else:
        g_confdb_merger.inputs.append(node)
    return g_confdb_merger

class merge_confdb(waflib.Task.Task):
    color='PINK'
    ext_in = ['_confDb.py']
    #ext_out= ['.py']
    after = ['merge_dsomap',]
    run_str = 'cat ${SRC} > ${TGT}'
    reentrant = False
    
    def runnable_status(self):
        status = waflib.Task.Task.runnable_status(self)
        if status == waflib.Task.ASK_LATER:
            return status
        
        import os
        for in_node in self.inputs:
            try:
                os.stat(in_node.abspath())
            except:
                msg.debug("::missing input [%s]" % in_node.abspath())
                return waflib.Task.ASK_LATER
        return waflib.Task.RUN_ME
    
### ---------------------------------------------------------------------------
g_cliddb_merger = None
@feature('merge_cliddb')
def schedule_merge_cliddb(self):
    #bld_area = self.env['BUILD_INSTALL_AREA']
    pass

@extension('clid.db')
def merge_cliddb_hook(self, node):
    global g_cliddb_merger
    if g_cliddb_merger is None:
        import os
        bld_area = os.path.basename(self.env['BUILD_INSTALL_AREA'])
        bld_node = self.bld.bldnode.find_dir(bld_area)
        share_node = bld_node.make_node('share')
        share_node.mkdir()
        out_node = share_node.make_node('clid.db')
        g_cliddb_merger = self.create_task('merge_cliddb', node, out_node)
        self.bld.install_files(
            '${INSTALL_AREA}/share',
            out_node,
            relative_trick=False
            )
    else:
        g_cliddb_merger.inputs.append(node)
    return g_cliddb_merger

class merge_cliddb(waflib.Task.Task):
    color='PINK'
    ext_in = ['clid.db']
    ext_out= ['clid.db']
    after = ['merge_dsomap', 'merge_confdb',]
    run_str = 'cat ${SRC} > ${TGT}'
    shell = True

    def runnable_status(self):
        status = waflib.Task.Task.runnable_status(self)
        if status == waflib.Task.ASK_LATER:
            return status
        
        import os
        for in_node in self.inputs:
            try:
                os.stat(in_node.abspath())
            except:
                msg.debug("::missing input [%s]" % in_node.abspath())
                return waflib.Task.ASK_LATER
        return waflib.Task.RUN_ME
    
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
    
import waflib.Configure
waflib.Configure.ConfigurationContext.configure_python = configure_python
