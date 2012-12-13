#!/usr/bin/env python

import os
import glob
import shutil
import subprocess as sub
import sys

def println(*args):
    sys.stdout.write(' '.join(args) + '\n')
    
kitdir = os.path.realpath(os.path.dirname(__file__))
waffledir=os.path.dirname(kitdir)

waf_tools=','.join([
    'batched_cc',
    'compat',
    'compat15',
    'ocaml',
    'go',
    'cython',
    'scala',
    'erlang',
    'cuda',
    'gcj',
    'boost',
    'pep8',
    'subprocess',
    'parallel_debug',
    ])

lib_tools = []

# libdir=os.path.join(waffledir, 'wafflelib')
# libdir=os.path.realpath(libdir)
# lib_tools += [p for p in glob.glob(os.path.join(libdir,"waffle*.py"))]

tools=','.join([waf_tools]+lib_tools)


println("::::::::::::::::::::::::")
println(":: build-kit with tools: %s" % tools)
println("::::::::::::::::::::::::")
println("")

#println("kitdir: %s" % kitdir)
#println("waffle: %s" % waffledir)

os.chdir(os.path.join(waffledir,'src-waf'))

## prelude = '''\
## from waflib.extras.wafflelib import waffle_main
## waffle_main.start(cwd, VERSION, wafdir)
## sys.exit(0)
## '''

waf_light = os.path.join(os.getcwd(), 'waf-light')
cmd = [
    sys.executable,
    waf_light,
    'configure', 'build',
    '--tools=%s' % tools,
    #'--prelude=\tfrom waflib.extras import waffle_main;waffle_main.start(cwd, VERSION, wafdir);sys.exit(0)',
    ]
#println(":: cmd: %s" % cmd)

sub.check_call(
    cmd,
    cwd=os.path.join(waffledir,'src-waf'),
    )

os.chdir(waffledir)

for exe in ('waf', 'tmp-waf'):
    if os.path.exists(exe):
        os.remove(exe)
shutil.move(src=os.path.join(waffledir,'src-waf','waf'),
            dst='waf')

## ## force python2 by default
## with open('waf', 'wb') as waf:
##     waf.write('#!/usr/bin/env %s\n' % os.getenv('WAF_PYTHON', 'python2'))
##     lines = open('tmp-waf', 'rb').readlines()[1:]
##     for l in lines:
##         waf.write(l)
##     waf.flush()
## os.remove('tmp-waf')
## os.chmod('waf', 0755)

println(":: done")
println("::::::::::::::::::::::::")

