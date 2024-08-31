import sys

path = "/home/deploy/mmt-py"
if path not in sys.path:
    sys.path.append(path)

from mmt_backend import create_app
app = create_app()
