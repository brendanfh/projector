#!/usr/bin/env python3

import sys
import os
import subprocess
import argparse
import yaml
import shutil
import re
from pprint import pprint

def get_env(x, d):
    if x in os.environ:
        return os.environ[x]
    else:
        return d

projectsfile = os.path.expanduser(get_env('PROJECTOR_PROJECT_FILE', '~/projects.txt'))
projectsdirectory = os.path.expanduser(get_env('PROJECTOR_PROJECTS', '~/Documents/Projects'))
githubusername = get_env('PROJECTOR_GITHUB_USERNAME', '')
tmuxcommand = get_env('PROJECTOR_TMUX', 'tmux')

def open_project(project, attach=True):
    with open(projectsfile, 'r+') as f:
        projects = { name : path for name, path in [line.strip().split(' ') for line in f.readlines()]}
        if project not in projects:
            picked_project = os.popen('echo \"' + '\n'.join([key for key, value in projects.items()]) + '\" | fzf --height=20 --query=' + project + ' --layout=reverse --border --preview="cat ' + projectsfile + ' | grep \'^{} \' | sed \'s/.* //\' | sed \'s/$/\/README.md/\' | xargs cat"').read().replace('\n', '')
            if picked_project == '':
                exit()
            elif picked_project in projects:
                project = picked_project
            else:
                print("Project {} not found".format(picked_project))
                exit(1)
        if os.popen('{} ls | grep "{}:"'.format(tmuxcommand, project)).read() != '':
            if attach:
                print('{} session already running, connecting now'.format(project))
                os.system('{} a -t {}'.format(tmuxcommand, project))
            else:
                print('{} session already running, connect with `projector open|connect {}`'.format(project, project))
            return
        if not os.path.isfile(os.path.expanduser(projects[project]) + '/.projector.yml'):
            os.system('cd {} && {} new-session -d -s {}'.format(projects[project], tmuxcommand, project))
            if attach:
                os.system('{} a -t {}'.format(tmuxcommand, project))
                return
        with open(os.path.expanduser(projects[project]) + '/.projector.yml', 'r') as pyml:
            try:
                config = yaml.safe_load(pyml)
                os.system('cd {} && {} new-session -d -s {}'.format(projects[project], tmuxcommand, project))
                counter = 1
                for title, options in config['wins'].items():
                    if counter > 1:
                        os.system('{} new-window -t {}:{}'.format(tmuxcommand, project, counter))
                    os.system('{} rename-window -t {}:{} "{}"'.format(tmuxcommand, project, counter, title))
                    os.system('{} select-window -t {}:{}'.format(tmuxcommand, project, title))
                    counter2 = 0
                    for start_command in options['panes']:
                        if counter2 > 0:
                            # rework to be able to split on some configuration
                            os.system('{} split-window -v'.format(tmuxcommand))
                        os.system('{} send-keys -t {}:{}.{} {} Enter'.format(tmuxcommand, project, title, counter2, start_command))
                        counter2 += 1
                    os.system('{} select-layout -t {}:{} {}'.format(tmuxcommand, project, title, options['layout'] if 'layout' in options else 'tiled'))
                    if 'main-pane-height' in options:
                        os.system('{} set-window-option -t {}:{} main-pane-height {}'.format(tmuxcommand, project, title, options['main-pane-height']))
                    if 'main-pane-width' in options:
                        os.system('{} set-window-option -t {}:{} main-pane-width {}'.format(tmuxcommand, project, title, options['main-pane-width']))
                    counter += 1
                os.system('{} select-window -t {}:{}'.format(tmuxcommand, project, config['select'] if 'select' in config else list(config['wins'].items())[0][0]))
                if attach:
                    os.system('{} a -t {}'.format(tmuxcommand, project))
            except yaml.YAMLError as err:
                print(err)

def add_project(project, project_path, open_project_bool, attach):
    projects = []
    with open(projectsfile, 'r+') as f:
        projects = [line.strip().split(' ')[0] for line in f.readlines()]
    while project == '' or project in projects:
        project = input('Project Name >> ')
        if project == '':
            print('No name specified, aborting')
            return
        if project in projects:
            print('Project `{}` already exists, try again (Enter to abort)'.format(project))
    if project_path == '':
        project_path = os.popen('tmp="$(mktemp)" ; lf -last-dir-path="$tmp" >/dev/null ; cat "$tmp" ; rm "$tmp"').read().strip()
        if project_path == '':
            print('No directory selected, aborting')
            exit(1)
        else:
            with open(projectsfile, 'r+') as f:
                lines = [line.strip() for line in f.readlines()]
                lines.insert(0, '{} {}'.format(project, project_path))
                f.seek(0)
                f.writelines('\n'.join(lines))
                f.truncate()
            if open_project_bool:
                open_project(project, attach)
    else:
        with open(projectsfile, 'r+') as f:
            lines = [line.strip() for line in f.readlines()]
            lines.insert(0, '{} {}'.format(project, project_path))
            f.seek(0)
            f.writelines('\n'.join(lines))
            f.truncate()
        if open_project_bool:
            open_project(project, attach)
    if os.path.isdir(os.path.expanduser(project_path) + '/.git'):
        with open(os.path.expanduser(project_path) + '/.gitignore', 'a+') as f:
            f.write('\n\n# ignore projector (my custom project manager) configuration files\n.projector.yml')
    with open(os.path.expanduser(project_path) + '/.projector.yml', 'w+') as f:
        f.write('select: one\nwins:\n  one:\n    layout: tiled\n    panes:\n      - clear')

def remove_project(project, remove_from_disk):
    projects = []
    with open(projectsfile, 'r+') as f:
        projects = { name : path for name, path in [line.strip().split(' ') for line in f.readlines()]}
    if project == '':
        project = os.popen('echo \"' + '\n'.join([key for key, value in projects.items()]) + '\" | fzf --height=20 --query=' + project + ' --layout=reverse --border --preview="cat ' + projectsfile + ' | grep \'^{} \' | sed \'s/.* //\' | sed \'s/$/\/README.md/\' | xargs cat"').read().replace('\n', '')
        if project == '':
            print('No project specified, aborting')
            return
    else:
        with open(projectsfile, 'r+') as f:
            if project not in projects:
                print('Project `{}` not found, aborting'.format(project))
                return
    if remove_from_disk:
        try:
            shutil.rmtree(os.path.expanduser(projects[project]))
        except OSError as e:
            print('Error removing project `{}` ERROR: {}'.format(project, e.strerror))
    del projects[project]
    with open(projectsfile, 'w') as f:
        f.seek(0)
        f.write('\n'.join(['{} {}'.format(key, value) for key, value in projects.items()]))
        f.truncate()
    print('Project `{}` removed'.format(project))

def new_project(project, project_path, github, open_project, attach):
    projects = []
    with open(projectsfile, 'r+') as f:
        projects = [line.strip().split(' ')[0] for line in f.readlines()]
    while project == '' or project in projects:
        project = input('Project Name >> ')
        if project == '':
            print('No name specified, aborting')
            return
        if project in projects:
            print('Project `{}` already exists, try again (Enter to abort)'.format(project))
    if project_path == '':
        project_path = os.path.expanduser('~/Documents/Projects/{}'.format(project))
    if github != None:
        if github == True:
            os.system('git clone https://github.com/{}/{} {}'.format(githubusername, project, project_path))
        else:
            print('"{}"'.format(github))
            if re.match('^https:\/\/github\.com\/[a-zA-Z0-9\-_$]+\/[a-zA-Z0-9\-_$]+\/?$', github):
                os.system('git clone {} {}'.format(github, project_path))
            elif re.match('^github\.com\/[a-zA-Z0-9\-_$]+\/[a-zA-Z0-9\-_$]+\/?$', github):
                os.system('git clone https://{} {}'.format(github, project_path))
            elif re.match('^[a-zA-Z0-9\-_$]+\/[a-zA-Z0-9\-_$]+$', github):
                os.system('git clone https://github.com/{} {}'.format(github, project_path))
            elif re.match('^[a-zA-Z0-9\-_$]+$', github):
                os.system('git clone https://github.com/{}/{}'.format(githubusername, github, project_path))
            else:
                print('Invalid value for --github')
                return
    else:
        os.mkdir(project_path)
    add_project(project, project_path, open_project, attach)
    os.system('chmod -R 774 {}'.format(project_path))

if len(sys.argv) == 1:
    open_project('')
    exit()

def validate_directory(directory):
    if os.path.isdir(directory) or directory == '':
        return directory
    raise argparse.ArgumentTypeError('Directory {} does not exist'.format(directory))

parser = argparse.ArgumentParser()

parser.add_argument('command', type=str, choices=['add', 'a', 'open', 'o', 'connect', 'c', 'remove', 'r', 'new', 'n'], help='The command to execute')
parser.add_argument('-n', '--name', type=str, default='', help='The name for the project being removed, added, opened, connected to, or created')
parser.add_argument('-g', '--github', nargs='?', type=str, const=True, default=None, help='Flag to specify whether project name is from a repository on github')
parser.add_argument('-p', '--path', type=validate_directory, default='', help='The path to use with the add and new project commands')
parser.add_argument('-o', '--open', action='store_true', help='Include this option to automatically open a project that is being added or created')
parser.add_argument('--no-attach', dest='attach', action='store_false', help='Tell projector not to attach to tmux session after creation') # this is intentionally backwards, since it has to be inverted later
parser.add_argument('--remove-from-disk', action='store_true', help='Include this option when using the delete command to delete project from the projectsfile and from disk')

args = parser.parse_args()

if args.command in ['add', 'a']:
    add_project(args.name, args.path, args.open, args.attach)
elif args.command in ['open', 'o', 'connect', 'c']:
    open_project(args.name, args.attach)
elif args.command in ['remove', 'r']:
    remove_project(args.name, args.remove_from_disk)
elif args.command in ['new', 'n']:
    new_project(args.name, args.path, args.github, args.open, args.attach)
