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


waflib.Tools.ccroot.USELIB_VARS['gen_reflex'] = set(['GCCXML_FLAGS', 'DEFINES', 'INCLUDES', 'CPPFLAGS', 'LIB'])

@feature('gen_reflex')
@after_method('apply_incpaths')
def gen_reflex_dummy(self):
    pass

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
        env = self.generator.bld._get_env_for_subproc()
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
        env = self.generator.bld._get_env_for_subproc()
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
    
