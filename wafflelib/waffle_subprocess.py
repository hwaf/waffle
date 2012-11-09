# redirection layer to subprocess to handle py2/py3
try: import waflib.extras.waffle_py2_subprocess as subprocess
# py-3
except SyntaxError: import subprocess
