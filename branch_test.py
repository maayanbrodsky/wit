from datetime import datetime
import filecmp
import os
import pathlib
import random
import shutil
import sys


def copy_file_or_dir(src, dst):
    """A function that takes a source path and destination path, checks if the source
    is a file or a directory and copies it to the destination"""
    if os.path.isfile(src):
        shutil.copy2(src, dst)
    elif os.path.isdir(src):
        dst = dst / src
        shutil.copytree(src, dst)


def check_backup_dir(subdir=None):
    """A function that takes a subdirectory name, checks if a '.wit' backup directory
    exists and returns a path object with the subdirectory. If no subdirectory name
    is passed the function retruns the '.wit' directory. If the '.wit' directory does
    not exist up the directory tree it raises a FileNotFoundError"""
    main_backup_dir = '.wit'
    backup_dir = pathlib.Path(os.getcwd())
    while backup_dir.parent != backup_dir and main_backup_dir not in os.listdir(backup_dir):
        backup_dir = backup_dir.parent
    backup_home_dir = backup_dir / main_backup_dir
    if backup_dir == backup_dir.parent and not backup_home_dir.exists():
        raise FileNotFoundError('No backup folder found.')
    if subdir is None:
        return backup_home_dir
    return backup_home_dir / subdir


def determine_parent():
    """A function that returns the parent in the references file or 'None' if
    there is none."""
    parent = 'None'
    main_backup_dir = check_backup_dir()
    if (main_backup_dir / 'references.txt').exists():
        with open(main_backup_dir / 'references.txt', 'r') as references:
            parent = references.readlines()[0][5:45]
    return parent


def make_meta_data(backup_dir, commit_id, message, parent):
    """A function that takes a path, a randomly generated file id,
    and a message, and generates a metadata txt file."""
    now = datetime.now()
    date = now.strftime('%c')
    with open(backup_dir / f'{commit_id}.txt', 'w') as meta_file:
        meta_file.write(f'parent={parent}\n')
        meta_file.write(f'date={date} +0300\n')
        meta_file.write(f'message={message}\n')


def replace_dir_content(dst, src):
    """A function that takes a source path and a destination path,
    empties the destination directory, and then fills it with the
    contents of ths source directory."""
    dst_files = os.listdir(dst)
    for file in dst_files:
        item = dst / file
        pathlib.Path.unlink(item)
    src_files = os.listdir(src)
    for file in src_files:
        copy_file_or_dir(src / file, dst / file)


def update_head(main_backup_dir, commit_id):
    """A function that takes a path for the main wit directory and a commit_id string
    and updates the references file."""
    with open(main_backup_dir / 'references.txt', 'r') as references:
        lines = references.readlines()
        lines[0] = f'HEAD={commit_id}\n'
    with open(main_backup_dir / 'references.txt', 'w') as references:
        references.writelines(lines)


def update_branch_id(main_backup_dir, active_branch, commit_id):
    """A function that updates the active branch's commit id if it is equal
    to the head."""
    with open(main_backup_dir / 'references.txt', 'r') as references:
        lines = references.readlines()
    new_lines = []
    for line in lines:
        separator = line.find('=')
        title = line[:separator]
        new_line = line
        if title == active_branch:
            new_line = f'{active_branch}={commit_id}\n'
        new_lines.append(new_line)
    with open(main_backup_dir / 'references.txt', 'w') as references:
        references.writelines(new_lines)


def update_references(main_backup_dir, commit_id):
    """A function that updates the references file in the commit function.
    if the head and the master are identical in the current version of the references
    file it changes the commit id of the head and the master to the commit id passed to it
    If they are different it only changes the commit id of the head."""
    if(main_backup_dir / 'references.txt').exists():
        with open(main_backup_dir / 'references.txt', 'r') as references:
            lines = references.readlines()
        head = lines[0][5:45]
        master = lines[1][14:54]
        active_branch, active_branch_id = active_branch_commit_id(main_backup_dir)
        if active_branch_id == head:
            update_branch_id(main_backup_dir, active_branch, commit_id)
        lines[0] = f'HEAD={commit_id}\n'
        if head == master and active_branch == 'master':
            lines[1] = f'master commit={commit_id}\n'
        with open(main_backup_dir / 'references.txt', 'w') as references:
                references.writelines(lines)
    else:
        with open(main_backup_dir / 'references.txt', 'w') as references:
            references.write(f'HEAD={commit_id}\n'
                             f'master commit={commit_id}')


def active_branch_commit_id(main_backup_dir):
    "A function that returns the branch activated in the 'activated.txt' file."
    with open(main_backup_dir / 'activated.txt', 'r') as activated:
        activated_branch = activated.read()
        commit_dict = create_commit_dict(main_backup_dir)
        if activated_branch in commit_dict.keys():
            return activated_branch, commit_dict[activated_branch]


def create_commit_dict(main_backup_dir):
    """A function that takes the main backup directory, runs through the lines
    in the references file and returns a dictionary of title and corresponding
    commit ids."""
    with open(main_backup_dir / 'references.txt', 'r') as references:
        lines = references.readlines()
    commit_dict = {}
    for line in lines:
         separator  = line.find('=')
         title = line[:separator]
         commit_num = line[separator+1:-1]
         commit_dict[title] = commit_num
    return commit_dict


def print_dict(dictionary):
    "A function that prints the key-value pairs of a dictionary line by line."
    for key in dictionary:
        print(f'{key}: {dictionary[key]}')


def check_status(stat):
    """A function the checks if there are changes not yet committed or staged.
    If there are such changes it prints the status dictionary  and raises an exception
    that stops the checkout process and informs the user."""
    if stat['Changes to be committed'] != [] or stat['Changes not staged for commit'] != []:
        print_dict(stat)
        raise Exception('Unsaved changes detected, please check your work and commit changes.')


def copy_tracked_files_to_current_dir(image_dir, current_dir, stat):
    """A function that copies all files tracked for change from the image directory
    passed to it into the the current working directory."""
    image_files = os.listdir(image_dir)
    for file in image_files:
        if file not in stat['Untracked files']:
            copy_file_or_dir(image_dir / file, current_dir / file)


def branch_or_commit(user_input, main_backup_dir):
    """A function that determines if the user passed a branch name or a commit id
    to the checkout function and returns either the commit id associated with the
    branch or the commit id passed to it."""
    commit_dict = (create_commit_dict(main_backup_dir))
    if user_input in commit_dict.keys():
        with open(main_backup_dir / 'activated.txt', 'w') as activated:
            activated.write(user_input)
        return commit_dict[user_input]
    else:
        return user_input


def init():
    """A function that initializes the main and secondary backup directories and sets up
    the activated branch file with a default value of 'master'."""
    main_backup_dir = '.wit'
    parent_dir = os.getcwd()
    new_dir = pathlib.Path() / parent_dir / main_backup_dir / 'images'  #Changed syntax according to notes on submission
    new_dir.mkdir(parents=True, exist_ok=True)
    new_dir = pathlib.Path() / parent_dir / main_backup_dir / 'staging_area'
    new_dir.mkdir(parents=True, exist_ok=True)
    with open(new_dir.parent / 'activated.txt', 'w') as activated:
        activated.write('master')


def add(src):
    """A function that takes a source path and copies the
    file to a subdirectory (staging area)"""
    subfolder = 'staging_area'
    src = pathlib.Path(src)
    src = src.absolute().resolve()
    dst = check_backup_dir(subfolder)
    copy_file_or_dir(src, dst)


def commit(message):
    """A function that commits the content of the staging area to an image folder
    and generates meta-data files."""
    images = check_backup_dir('images')
    main_backup_dir = check_backup_dir()
    commit_id = ''.join(random.choices(list('1234567890abcdef'), k=40))
    parent = determine_parent()
    make_meta_data(images, commit_id, message, parent)
    shutil.copytree(main_backup_dir / 'staging_area', images / commit_id)  # creates the new image
    update_references(main_backup_dir, commit_id)


def status():
    """A function that prints out data on the state of the changes not yet committed."""
    backup_dir = check_backup_dir()
    with open(backup_dir / 'references.txt', 'r') as references:
        recent_commit_id = references.readlines()[0][5:45]
    recent_backup_dir = backup_dir / 'images' / recent_commit_id
    staging_area = backup_dir / 'staging_area'
    current_dir = os.getcwd()
    staging_vs_recent_commit = filecmp.dircmp(staging_area, recent_backup_dir)
    staging_vs_cwd = filecmp.dircmp(staging_area, current_dir)
    stat = {'Most recent commit id': recent_commit_id,
            'Changes to be committed': staging_vs_recent_commit.left_only,
            'Changes not staged for commit': staging_vs_cwd.diff_files,
            'Untracked files': staging_vs_cwd.right_only}
    return stat


def checkout(user_input):
    """A function that takes either a commit id or branch name. If a branch name is passed
    it is updated in the 'activated' file and its associated commit id is used. If a commit id
    is passed, that will be the commit id used. the function uses the image directory id and
    replaces the contents of the cwd with the contents of that image directory."""
    main_backup_dir = check_backup_dir()
    commit_id = branch_or_commit(user_input, main_backup_dir)
    if user_input == 'master':
        main_backup_dir = check_backup_dir()
        with open(main_backup_dir / 'references.txt', 'r') as references:
            commit_id = references.readlines()[1][14:54]
    images = check_backup_dir('images')
    staging_area = check_backup_dir('staging_area')
    image_dir = images / commit_id
    current_dir = os.getcwd()
    current_dir = pathlib.Path(current_dir)
    stat = status()
    check_status(stat)
    copy_tracked_files_to_current_dir(image_dir, current_dir, stat)
    replace_dir_content(staging_area, image_dir)
    update_head(staging_area.parent, commit_id)


def branch(name):
    """A function that adds a new branch name to the references file and adds the
    head commit to it."""
    main_backup_dir = check_backup_dir()
    with open(main_backup_dir / 'references.txt', 'r') as references:
        lines = references.readlines()
        commit_id = lines[0][5:45]
        lines.append(f'{name}={commit_id}\n')
    with open(main_backup_dir / 'references.txt', 'w') as references:
        references.writelines(lines)






if __name__ == '__main__':
    command = sys.argv[1]
    if command == 'init':
        init()
    if command == 'add':
        add(sys.argv[2])
    if command == 'commit':
        commit(sys.argv[2])
    if command == 'status':
        print_dict(status())
    if command == 'checkout':
        checkout(sys.argv[2])
    if command == 'branch':
        branch(sys.argv[2])
