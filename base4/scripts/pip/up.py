import datetime
import os
import subprocess

from base4.utilities.files import get_project_root


def find_upgraded_packages(targets):
    # Run `pip freeze` and capture the output
    result = subprocess.run(['pip', 'freeze'], capture_output=True, text=True)
    installed_packages = result.stdout.splitlines()
    # Extract package names (without versions)

    found_packages = []
    for t in targets:
        pck = t.split('==')[0]
        if len(pck) > 1:
            for i in installed_packages:
                if pck in i:
                    found_packages.append(i)

    # Find matches
    return found_packages


def save_to_file(packages):
    with open(f'{get_project_root()}/requirements-upgraded.txt', 'w') as file:
        for package in packages:
            file.write(f"{package}\n")


def extract_dependencies(toml_file):
    dependencies = []
    reading_dependencies = False
    freeze = ''

    with open(toml_file, 'r') as file:
        for line in file:
            line = line.strip()

            if line.startswith('dependencies ='):
                reading_dependencies = True
                continue

            # Stop reading if we hit an empty line or another section
            if reading_dependencies:
                if line == '' or line.startswith('['):
                    break

                # Remove commas and brackets, then extract package names
                line = line.strip('[],')
                for dep in line.split(','):
                    dep = dep.strip().strip("'").strip('"')
                    dependencies.append(dep)
                    freeze += f'{dep}\n'

    # backup versions from toml
    try:
        with open(f'requirements-old.txt', 'w') as f:
            f.write(freeze)
    except:
        print('[*] backup requirements.txt not found')

    # upgrade libs
    pkg_list = ''
    for package in dependencies:
        pkg_list += package.split('==')[0] + ' '
    os.system(f'pip install {pkg_list} -U')

    upgraded = set(find_upgraded_packages(dependencies))

    print(f'\ncopy --> {get_project_root()}/pyproject.toml')
    print('-' * 50)
    print(f'\t# GENERATED ON: {datetime.datetime.now().replace(microsecond=0)}')
    for u in upgraded:
        for o in dependencies:
            if o.split('==')[0] == u.split('==')[0]:
                print(f"\t'{u}',", f"{ '#' + o.split('==')[1] if u.split('==')[1] > o.split('==')[1] else ''}")
    print('-' * 50)

    save_to_file(upgraded)


def do():
    os.system('pip install wheel setuptools pip -U')
    extract_dependencies(f"{get_project_root()}/pyproject.toml")


if __name__ == '__main__':
    do()
