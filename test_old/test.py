#!/usr/bin/env python

import os
import re
import shlex
import getpass

REZ_DELIMITER_PATTERN = re.compile(r"-|==|>=|>|<=|<")
TRACTOR_JOB_URL = "http://tractor-engine/tv/#jid={jid}"


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


def createJob(tractorAuthor, tq):
    """
    Create a job with a single task
    The goal of this task is to spool additional tasks
    """
    name = "[Tractor test] creating tasks"
    mainTags = {'prod': "mvg", 'nbFrames': "1", 'comment': ""}
    allRequirements = ["mikrosRender"]
    # Create job
    job = tractorAuthor.Job(
        title="[Tractor test] (Job) creating tasks", 
        service="mikrosRender", 
        metadata="",
        envkey=get_envkey(),
        paused=False,
        comment="",
        spoolcwd='/tmp',
        projects=["vfx"]
    )
    # Job task
    jobTask = job.newTask(title="[Tractor test] (Job task) creating tasks", 
                          argv=None, serialsubtasks=True)
    # Create command
    cmd = "create_subtask" 
    cmd = rezWrapCommand(cmd)
    tractorCmd = shlex.split(cmd)
    # Create task
    task = tractorAuthor.Task(
        title="[Tractor test] (Task) creating tasks",
        argv=tractorCmd,
        service="mikrosRender",
        metadata="TASK_A"
    )
    for cmd in task.cmds:
        cmd.tags = []
        cmd.envkey = get_envkey()
        cmd.expand = True
    jobTask.addChild(task)
    # Submit
    user = os.environ.get('FARM_USER', os.environ.get('USER', getpass.getuser()))
    jid = job.spool(block=False, owner=user)
    return jid


def main():
    from tractor.api import author as tractorAuthor
    import tractorSubmitter.api.tractorJobQuery as tq
    jid = createJob(tractorAuthor, tq)
    print(f"Created job: {jid}")
    print(f"-> {TRACTOR_JOB_URL.format(jid=jid)}")
    

if __name__ == "__main__":
    main()
