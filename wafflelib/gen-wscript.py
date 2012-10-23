#!/usr/bin/env python
# gen-wscript.py
# script to convert a cmt/requirements file into a wscript

import os
import sys

#import xml.etree as etree
#from xml.etree import ElementTree

cmt_dir = os.path.join(sys.argv[1], 'cmt')
orig_dir = os.getcwd()

os.chdir(cmt_dir)
#os.system("cmt show uses -xml")

cmt_pkgfullname = sys.argv[1]
cmt_pkgname = os.path.basename(sys.argv[1])
cmt_pkgroot = sys.argv[2]
waffle_root = sys.argv[3]

cmt_installarea = os.path.join(cmt_pkgroot, 'InstallArea')
cmt_installarea_inc = os.path.join(cmt_pkgroot, 'InstallArea', 'include')
is_verbose = '--verbose' in sys.argv
#is_verbose = True
    
def my_print(*args, **kw):
    out = kw.get('file', sys.stdout)
    out.write(' '.join(map(str,args))+'\n')

my_print ("gen-wscript: massaging package [%s]..." % (cmt_pkgname,))

def cmt_show(cmd, xml=False):
    post_fix = ''
    if xml:
        post_fix = ' -xml'
    return ''.join(os.popen('cmt show '+cmd+post_fix+' 2> /dev/null').readlines())

__pkg_libs = {}
def _get_libs(libname):
    global __pkg_libs
    if libname in __pkg_libs:
        return __pkg_libs[libname]
    raw_libs = [l.strip() for l in cmt_show('macro_value %s_use_linkopts' % libname).split() if l.strip()] + \
               [l.strip() for l in cmt_show('macro_value %slinkopts' % libname).split() if l.strip()]
    #my_print (">>",raw_libs)
    libs = []
    for l in raw_libs:
        if l[:2] == '-l' and (l[2:].strip() != libname.strip()):
            libs.append(l[2:])
    if is_verbose:
        my_print('>>',libname,':',libs)
    #my_print ("@@",libs)
    __pkg_libs[libname] = libs
    return libs

__pkg_deps = {}
def _get_deps(libname):
    global __pkg_deps
    if libname in __pkg_deps:
        return __pkg_deps[libname]
    raw_deps = [l.strip()
                for l in cmt_show('macro_value %s_dependencies' %
                                  libname).split()
                if (l.strip() and not l.startswith('#CMT'))]
    deps = []
    for l in raw_deps:
        if l in ('install_includes',):
            continue
        if is_verbose:
            my_print ("+++", l)
        deps.append(l)
    deps = list(set(deps))
    if is_verbose:
        my_print('-- deps:', deps)
    __pkg_deps[libname] = deps
    return deps

#uses = cmt_show('uses', xml=True)
#my_print (uses)
#uses = etree.ElementTree.fromstring(uses)

pkg_root = cmt_show('macro_value %s_root' % cmt_pkgname).strip()
if is_verbose:
    my_print ("=== pkg-root:",repr(pkg_root))

if is_verbose:
    my_print ("=== include_dirs...")
_inc_dirs = [l.strip().replace('"', '')
            for l in cmt_show('macro_value includes').replace("  "," ").split(" -I")
            if l.strip()]
inc_dirs = []
for d in _inc_dirs:
    #my_print("==> %s" % d)
    if d == os.path.join(cmt_installarea_inc,cmt_pkgname):
        # replace InstallArea/include/FooPkg
        # with:   Path/To/FooPkg
        # FIXME
        d = os.path.join(waffle_root, cmt_pkgfullname)
    if d.startswith(cmt_installarea_inc):
        # replace InstallArea/include
        # with    install_area/include
        # FIXME
        d = os.path.join(waffle_root,'install_area','include')
        pass
    if not (d in inc_dirs):
        inc_dirs.append(d)
        #my_print("++> %s" % d)
        pass
    pass
del _inc_dirs
if is_verbose:
    my_print (inc_dirs)
#inc_dirs = etree.ElementTree.fromstring(inc_dirs)

#inc_dirs

if is_verbose:
    my_print ("=== defines...")
pkg_version = cmt_show('macro_value version').strip()
pkg_defines=['PACKAGE_VERSION="%s"'%pkg_version,
             'PACKAGE_VERSION_UQ=%s'%pkg_version]

if is_verbose:
    my_print ("=== constituents...")
constituents = cmt_show('constituents')
if is_verbose:
    my_print (constituents)

libs = {}
apps = {}
comp_libs = []
rflx_libs = {}
install_includes = False

python_modules = []
joboptions = []
bin_scripts= []

for l in constituents.splitlines():
    t = l.split()
    if is_verbose:
        my_print ("--->",t)
    if t[0] == 'document':
        if t[1] == '':
            pass
        elif t[1] == 'genconfig':
            comp_libs.append(t[2][:-len('Conf')])
            pass
        elif t[1] == 'reflex_dict':
            n = t[2][:-len('Gen')]
            # make all the paths relative to the pkg_root...
            selection_file = cmt_show(
                'macro_value reflex_dict%s_selection_file' % n
                ).strip()
            selection_file = ' '.join([s.replace(pkg_root+'/','')
                                       for s in selection_file.split()])
            # make all the paths relative to the pkg_root...
            source = ' '.join([s.replace(pkg_root+'/', '')
                               for s in t[3].strip().split()])
            if selection_file.startswith('../'):
                selection_file = selection_file[len('../'):]
            if source.startswith('../'): source = source[len('../'):]
            rflx_libs[n] = dict(name=n,
                                source=source,
                                selection_file=selection_file,
                                cmt_includes=inc_dirs,
                                cmt_deps = _get_deps(n+'Dict'),
                                libs     = _get_libs(n+'Dict'),
                                defines=pkg_defines)
        elif t[1] == 'atlas_data_installer':
            if t[2] == 'install_python_modules':
                for arg in t[3:]:
                    if arg.startswith('prefix='):
                        break
                    if arg.startswith('../'):
                        arg = arg[len('../'):]
                    python_modules.append(arg)
            elif t[2] == 'install_joboptions':
                for arg in t[3:]:
                    if arg.startswith('prefix='):
                        break
                    if arg.startswith('../'):
                        arg = arg[len('../'):]
                    joboptions.append(arg)
            elif t[2] == 'install_scripts':
                absroot = os.path.normpath(
                    os.path.join(waffle_root, cmt_pkgfullname)
                    ) + os.sep             # add trailing '/'
                for arg in t[3:]:
                    if arg.startswith('prefix='):
                        break
                    if arg.startswith('../'):
                        arg = arg[len('../'):]
                    if arg.startswith(absroot):
                        arg = arg[len(absroot):]
                    bin_scripts.append(arg)
            else:
                pass
        elif t[1] == 'install_includes':
            install_includes = True
        pass
    elif t[0] == 'library':
        srcs = []
        test = False
        if t[2].startswith('-suffix=_'):
            # reflex dict
            # veto that library, it will be built by other means
            if is_verbose:
                my_print ("      [REJECT]",t)
            continue
        for s in t[2:]:
            if s[0] != '-':
                if s.startswith('../'):
                    s = s[len('../'):]
                srcs.append(s)
            elif s == '-group=tests':
                test=True
        libs[t[1]] = dict(name     = t[1],
                          source   = ' '.join(srcs),
                          do_test  = test,
                          includes = inc_dirs,
                          libs     = _get_libs(t[1]),
                          cmt_deps = _get_deps(t[1]),
                          defines  = pkg_defines,
                          )
        pass
    
    elif t[0] == 'application':
        srcs = []
        test = False
        for s in t[2:]:
            if s[0] != '-':
                if s.startswith('../'):
                    s = s[len('../'):]
                srcs.append(s)
            elif s in ('-group=tests',
                       '-group=check',
                       '-group=CppUnit',):
                test=True
        apps[t[1]] = dict(name     = t[1],
                          source   = ' '.join(srcs),
                          do_test  = test,
                          includes = inc_dirs,
                          libs     = _get_libs(t[1]),
                          cmt_deps = _get_deps(t[1]),
                          defines  = pkg_defines,
                          )
        pass
    else:
        my_print ("@@@ unknown constituent [%s]" % (t[0],))
        pass
    
    pass

wscript_tmpl = """\
# -*- python -*-
# automatically generated by gen-wscript

import waflib.Logs as msg

PACKAGE = {
    'name': '%(wscript_pkgname)s',
    'author': %(wscript_authors)r,
}

def configure(ctx):
    msg.debug ('[configure] package name: '+PACKAGE['name'])
    return

def build(ctx):

"""

wscript_dct = {
 'wscript_pkgname': cmt_pkgname,
 'wscript_authors': ['binet',],
}

app_tmpl = """\
    ctx.build_app(
       name     = '%(name)s',
       source   = %(source)r,
       includes = %(includes)r,
       defines  = %(defines)r,
       lib      = %(libs)r,
       use      = %(libs)r + %(cmt_deps)r,
       do_test  = %(do_test)r,
    )
"""

complib_tmpl = """\
    ctx.build_complib(
       name     = '%(name)s',
       source   = %(source)r,
       includes = %(includes)r,
       defines  = %(defines)r,
       lib      = %(libs)r,
       use      = %(libs)r + %(cmt_deps)r,
    )
"""

linklib_tmpl = """\
    ctx.build_linklib(
       name     = '%(name)s',
       source   = %(source)r,
       includes = %(includes)r,
       defines  = %(defines)r,
       lib      = %(libs)r,
       use      = %(libs)r + %(cmt_deps)r,
    )
"""

rflxlib_tmpl = """\
    ctx.build_reflex_dict(
       name     = '%(name)s',
       source   = %(source)r,
       selection_file = %(selection_file)r,
       cmt_includes = %(cmt_includes)r,
       defines  = %(defines)r,
       lib      = %(libs)r,
       use      = %(libs)r + %(cmt_deps)r,
    )
"""

install_includes_tmpl = """\
    incdir = ctx.path.find_dir(PACKAGE['name'])
    includes = incdir.ant_glob('**/*', dir=False)
    ctx.install_files(
        '${INSTALL_AREA}/include', includes, 
        relative_trick=True
        )
"""
install_includes_tmpl = """\
    ctx.install_headers()
"""

python_modules_tmpl = """\
    ctx.build_pymodule(source=%r)
"""

joboptions_tmpl = """\
    ctx.install_joboptions(source=%r)
"""

install_scripts_tmpl = """\
    ctx.install_scripts(source=%r)
"""

with open("../wscript", "w") as fout:
    #fout = sys.stdout
    fout.write(wscript_tmpl % wscript_dct)
    fout.write("\n")
    for libname,v in libs.iteritems():
        tmpl = linklib_tmpl
        if libname in comp_libs:
            tmpl = complib_tmpl
        fout.write(tmpl % v)
        fout.write("\n")
        
    for appname,v in apps.iteritems():
        my_print(app_tmpl % v, file=fout)
        pass
        
    for libname,v in rflx_libs.iteritems():
        my_print(rflxlib_tmpl % v, file=fout)
        pass

    fout.write("\n")
    if install_includes:
        fout.write(install_includes_tmpl)
        fout.write("\n")
        pass

    if python_modules:
        fout.write(python_modules_tmpl % python_modules)
        fout.write("\n")
        pass
        
    if joboptions:
        fout.write(joboptions_tmpl % joboptions)
        fout.write("\n")
        pass

    if bin_scripts:
        fout.write(install_scripts_tmpl % bin_scripts)
        fout.write("\n")
        pass
        
    fout.write("    return\n")
    fout.write("### EOF ###\n")
    



