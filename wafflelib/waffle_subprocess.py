# redirection layer to subprocess to handle py2/py3
try: from waflib.extras.waffle_py2_subprocess import *
# py-3
except SyntaxError: from subprocess import *
