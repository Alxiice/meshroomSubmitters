# -*- coding: utf-8 -*-

name = 'meshroomSubmitters'

version = 'sonoleta'

plugin_for = ['meshroom']

requires = [
]

private_build_requires = ['cmake-3.27+']

def commands():
    env.PYTHONPATH.append("{root}")
    env.PYTHONPATH.append("{root}/meshroom")
    # Command line nodes
    env.MESHROOM_SUBMITTERS_PATH.append('{root}/meshroom')
