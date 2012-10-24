# -*- python -*-
# @purpose the main entry point for driving the build and installation steps
# @author Sebastien Binet <binet@cern.ch>

# imports ---------------------------------------------------------------------
import os

# globals ---------------------------------------------------------------------
top = '.'
out = '__build__'
PREFIX = 'install_area'
VERSION = '0.0.1' # FIXME: should take it from somewhere else
APPNAME = os.path.basename(os.getcwd())

# imports ---------------------------------------------------------------------

# waf imports --
import waflib.Logs
import waflib.Utils
import waflib.Options
import waflib.Context
import waflib.Logs as msg

# waffle imports
import wafflelib.waffle as waffle
import wafflelib.waffle_utils as waffle_utils
import wafflelib.packaging as waffle_packaging

# functions -------------------------------------------------------------------

def options(ctx):
    ctx.load('waffle')
    return

def configure(ctx):
    # load the waffle tool(s)
    ctx.load('waffle')
    return

def build(ctx):
    ctx.load('waffle')
    return

def check(ctx):
    return
