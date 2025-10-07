#!/usr/bin/env python

"""
In this script we will execute a small process
then create some subtasks
"""

import sys
import json
import os
import re
import shlex
import getpass
import tempfile
from contextlib import redirect_stdout
import tractorSubmitter.api.tractorJobQuery as tq

REZ_DELIMITER_PATTERN = re.compile(r"-|==|>=|>|<=|<")

tmp_folder = "/s/prods/mvg/_source_global/users/sonoleta/tmp/logs"
stdout_lines = []

log_root = f"/s/xchange/Prods/tractor"


def getLogFile():
    job_id = os.environ.get('TR_ENV_JID')
    if not job_id:
        return None
    task_id = os.environ.get('TR_ENV_TID')
    if not task_id:
        return None
    log_file = os.path.join(log_root, job_id, f"{task_id}.log")
    return log_file


logFile = getLogFile()
alt_logFile = "/s/prods/mvg/_source_global/users/sonoleta/tmp/logs/logFile.txt"

def log(text, on_stderr=True):
    if on_stderr:
        sys.stderr.write(text + "\n")
    else:
        with open(logFile, 'a+') as f:
            f.write(text)


with open(alt_logFile, 'a+') as f:
    f.write(f"[Job log file] -> {logFile}")
    f.write(f"[Job log file] dir exists  : {os.path.exists(os.path.dirname(logFile))}")
    f.write(f"[Job log file] file exists : {os.path.exists(logFile)}\n")


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


if logFile:
    with open(logFile, 'w') as f, redirect_stdout(f):
        createSubTasks()
else:
    # with tempfile.NamedTemporaryFile(suffix='.txt', mode='w', delete=False) as tmp:
    # with tempfile.NamedTemporaryFile(suffix='.txt', mode='w') as tmp:
    with tempfile.NamedTemporaryFile(dir=tmp_folder, suffix='.txt', mode='w+', delete=False) as tmp:
        with redirect_stdout(tmp):
            createSubTasks()

print("\n".join(stdout_lines))
