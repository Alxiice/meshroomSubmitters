#!/usr/bin/env python

import re
import os
import logging
from meshroom.core.submitter import BaseSubmitter

currentDir = os.path.dirname(os.path.realpath(__file__))
binDir = os.path.dirname(os.path.dirname(os.path.dirname(currentDir)))
REZ_DELIMITER_PATTERN = re.compile(r"(-|==|>=|>|<=|<)")


def get_job_packages():
    reqPackages = []
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
            reqPackages.append("==".join([p, resolvedVersions[p]]))
        logging.debug(f'[DEBUG] REZ Packages: {str(reqPackages)}')
    elif 'REZ_MESHROOM_VERSION' in os.environ:
        reqPackages.append(f"meshroom-{os.environ.get('REZ_MESHROOM_VERSION', '')}")
    return reqPackages


class Task:
    def __init__(self, name: str, command, tags=None, rezPackages=None, **kwargs):
        self.name = name
        self.command = command
        self.tags = tags or {}
        self.rezPackages = rezPackages or []
        self.params = kwargs
        self._parents = []
        self._children = []
    
    def connect(self, parent):
        self._parents.append(parent)
        parent._children.append(self)


class Job:
    def __init__(self, name, tags=None, environment=None, user=None, **kwargs):
        self.name = name
        self.tags = tags or {}
        self.environment = environment or {}
        self.params = kwargs
        self.user = user or os.getenv("USER", "")
        self._tasks = []
    
    def addTask(self, task: Task):
        self._tasks.append(task)
    
    def submit(self, projectName: str, dryRun: bool=False):
        # TODO: The actual code to create the tasks and run the job in the background goes here
        return True


class LocalSubmitter(BaseSubmitter):

    dryRun = False
    environment = {}
    DEFAULT_TAGS = {'prod': ''}
    
    def __init__(self, parent=None):
        super().__init__(name='Local', parent=parent)
        self.project = "mvg"
        self.prod = os.environ.get('PROD', 'mvg')
        self.reqPackages = get_job_packages()
        if 'REZ_DEV_PACKAGES_ROOT' in os.environ:
            self.environment['REZ_DEV_PACKAGES_ROOT'] = os.environ['REZ_DEV_PACKAGES_ROOT']
        if 'REZ_PROD_PACKAGES_PATH' in os.environ:
            self.environment['REZ_PROD_PACKAGES_PATH'] = os.environ['REZ_PROD_PACKAGES_PATH']

    def createTask(self, meshroomFile, node):
        logging.info('node: ', node.name)
        tags = self.DEFAULT_TAGS.copy()  # copy to not modify default tags
        optionalArgs = {}
        if node.isParallelized:
            blockSize, fullSize, nbBlocks = node.nodeDesc.parallelization.getSizes(node)
            if nbBlocks > 1:
                optionalArgs["chunkInfo"] = {'start': 0, 'end': nbBlocks - 1, 'step': 1}
        tags['nbFrames'] = node.size
        tags['prod'] = self.prod
        exe = "meshroom_compute" if self.reqPackages else os.path.join(binDir, "meshroom_compute")
        taskCommand = f"{exe} --node {node.name} \"{meshroomFile}\" --extern"
        task = Task(
            name=node.name,
            command=taskCommand,
            tags=tags,
            rezPackages=self.reqPackages,
            **optionalArgs)
        return task

    def submit(self, nodes, edges, filepath, submitLabel="{projectName}"):
        projectName = os.path.splitext(os.path.basename(filepath))[0]
        name = submitLabel.format(projectName=projectName)
        comment = filepath
        maxNodeSize = max([node.size for node in nodes])
        mainTags = {
            'prod': self.prod,
            'nbFrames': str(maxNodeSize),
            'comment': comment,
        }

        # Create Job Graph
        job = Job(
            name,
            tags=mainTags,
            environment=self.environment,
            user=os.environ.get('USER'),
        )

        nodeNameToTask = {}

        for node in nodes:
            task = self.createTask(filepath, node)
            job.addTask(task)
            nodeNameToTask[node.name] = task

        for u, v in edges:
            nodeNameToTask[u.name].connect(nodeNameToTask[v.name])

        res = job.submit(projectName=self.project, dryRun=self.dryRun)
        return res
