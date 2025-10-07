#!/usr/bin/env python

"""
Helper functions to create subtasks

The queueSubtask will write on the stdout
>>> from tractorSubmitter.api.subtaskCreator import queueSubtask
>>> queueSubtask(command1, **args)
>>> queueSubtask(command2, **args)
"""

import sys
import json
import os
import re
import shlex
import getpass

REZ_DELIMITER_PATTERN = re.compile(r"-|==|>=|>|<=|<")

stdout_lines = []

def log(text):
    sys.stderr.write(text + "\n")

def rezWrapCommand(cmd):
    rezPackages = set()
    if 'REZ_REQUEST' in os.environ:
        packages = os.environ.get('REZ_USED_REQUEST', '').split()
        resolvedPackages = os.environ.get('REZ_RESOLVE', '').split()
        resolvedVersions = {}
        for r in resolvedPackages:
            if r.startswith('~'):  # remove implicit packages
                continue
            v = r.split('-')
            if len(v) == 2:
                resolvedVersions[v[0]] = v[1]
            elif len(v) > 2:  # Handle case with multiple hyphen-minus
                resolvedVersions[v[0]] = "-".join(v[1:])
        usedPackages = set()  # Use set to remove duplicates
        for p in packages:
            if p.startswith('~') or p.startswith("!"):
                continue
            v = REZ_DELIMITER_PATTERN.split(p)
            usedPackages.add(v[0])
        for p in usedPackages:
            # Use "==" to make sure we have the same version in the job that the one we have in the env
            # where meshroom is launched
            rezPackages.add("==".join([p, resolvedVersions[p]]))
    packagesStr = " ".join([p for p in rezPackages if p])
    if packagesStr:
        rezBin = "rez"
        if "REZ_BIN" in os.environ:
            rezBin = os.environ["REZ_BIN"]
        elif "REZ_PACKAGES_ROOT" in os.environ:
            rezBin = os.path.join(os.environ["REZ_PACKAGES_ROOT"], "/bin/rez")
        return f"{rezBin} env {packagesStr} -- {cmd}"
    return cmd


def get_envkey():
    environment = {}
    if 'REZ_DEV_PACKAGES_ROOT' in os.environ:
        environment['REZ_DEV_PACKAGES_ROOT'] = os.environ['REZ_DEV_PACKAGES_ROOT']
    if 'REZ_PROD_PACKAGES_PATH' in os.environ:
        environment['REZ_PROD_PACKAGES_PATH'] = os.environ['REZ_PROD_PACKAGES_PATH']
    if 'PROD' in os.environ:
        environment['PROD'] = os.environ['PROD']
    if 'PROD_ROOT' in os.environ:
        environment['PROD_ROOT'] = os.environ['PROD_ROOT']
    environment["FARM_USER"] = os.environ.get('FARM_USER', os.environ.get('USER', getpass.getuser()))
    return [f"setenv {k}={v}" for k, v in environment.items()]


def createTask(index) -> list[str]:
    """
    Create subtask
    Return a list of lines of tractor script
    """
    # Gather task infos
    name = f"[Tractor test] (Subtask) render job ({index})"
    metadata = {'prod': "mvg", 'comment': "", "iteration": str(index)}
    cmd = "subtask_cmd" 
    cmd = rezWrapCommand(cmd)
    service = "mikrosRender"
    cmd_tags = ["blender"]
    user = os.environ.get('FARM_USER', os.environ.get('USER', getpass.getuser()))
    metadata['user'] = user
    # Cast to string
    metadata_str = json.dumps(metadata)
    cmd_argv = " ".join(shlex.split(cmd))
    envkey_str = " ".join(get_envkey())
    tags_str = "".join(cmd_tags)
    # Create subtask
    subtask = f"""
Task -title {{{name}}} -service {{{service}}} -metadata {{{metadata_str}}} -cmds {{
    RemoteCmd {{{cmd_argv}}} -service {{{service}}} -tags {{{tags_str}}} -envkey {{{envkey_str}}}
}}
"""
    log(f"-> subtask script :\n{subtask}")
    return [l for l in subtask.split("\n") if l]


def createSubTasks(nbTasks=3):
    global stdout_lines
    log("Create subtasks !")
    import time
    time.sleep(2)    
    for subtask_index in range(nbTasks):
        log(f"[createSubTasks] Create subtask n.{subtask_index}")
        # TODO: Create task and update stdout
        for line in createTask(subtask_index):
            stdout_lines.append(line)
        log("")

createSubTasks()

print("\n".join(stdout_lines))
