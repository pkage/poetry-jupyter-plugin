from functools import reduce
from pprint import pprint
import tempfile
import os
import json
import platform

import asset
from cleo.commands.command import Command
from poetry.plugins.application_plugin import ApplicationPlugin
from poetry.utils.env import EnvManager, VirtualEnv
from jupyter_client.kernelspec import KernelSpecManager

def optional_chain(root, keys):
    try:
        return reduce(lambda a,c: a.get(c), keys.split('.'), root)
    except AttributeError:
        return None


class JupyterCommand(Command):
    name = 'base jupyter command'
    description = '(internal) jupyter base methods'


    def get_requested_kernel_opts(self):
        # load the configuration
        data = self.application.poetry.pyproject.data

        # get the current name or default to project name
        name = optional_chain(data, 'tool.jupyter.kernel.name')
        if name is None:
            name = optional_chain(data, 'tool.poetry.name')

        # get the current display name or default to project name
        display_name = optional_chain(data, 'tool.jupyter.kernel.display')
        if display_name is None:
            display_name = optional_chain(data, 'tool.poetry.name')

        # get the current display name or default to project name
        icon = optional_chain(data, 'tool.jupyter.kernel.icon') # None is an ok default

        # create kernel object
        return {
            'icon': icon,
            'name': name,
            'display': display_name
        }


    def get_venv(self):
        manager = EnvManager(self.application.poetry)

        if len(manager.list()) == 0:
            return None

        return manager.list()[0]


    def has_ipykernel(self):
        venv = self.get_venv()
        if venv is None:
            return False
        
        ipykernels = venv.site_packages.find('ipykernel')

        if len(ipykernels) == 0:
            return False

        return True


    def install_venv(self):
        # print(f'virtualenv python: {venv.python}')
        return False


    def get_all_installed_kernels(self):
        ksm = KernelSpecManager()
        return ksm.get_all_specs()
        

    def get_kernelspec_for_project(self):
        kernels = self.get_all_installed_kernels()

        venv = self.get_venv()
        if venv is None:
            return None

        for key, obj in kernels.items():
            argv = optional_chain(obj, 'spec.argv')
            if argv is None:
                continue

            if argv[0] == venv.python:
                obj['key'] = key
                return obj

        return None

    def get_preferred_spec_prefix(self):
        # fixes on macOS
        if platform.system() == 'Darwin':
            manager = KernelSpecManager()
            for dir in list(manager.kernel_dirs):

                if dir.endswith('/Library/Jupyter/kernels'):
                    return dir

        return None

class JupyterShowCommand(JupyterCommand):
    name = 'jupyter show'
    description = 'Show Jupyter kernels in this project.'

    def handle(self) -> int:
        venv = self.get_venv()
        if venv is None:
            self.line('<info>No virtualenv has been created for this project yet.</>')
            return 1
        
        spec = self.get_kernelspec_for_project()

        if spec is None:
            kernel = self.get_requested_kernel_opts()
            # self.line('<info>This kernel is not installed yet.</>')
            self.line(f'Kernel <c1>{kernel["name"]}</> has not yet been installed.')
            return 1


        self.line(f"<c1>{spec['spec']['display_name']}</> ({spec['resource_dir']})")

        return 0


class JupyterEnableCommand(JupyterCommand):

    name = 'jupyter install'
    description = 'Register this project as a Jupyter kernel.'

    def handle(self) -> int:

        # check if it's already installed
        spec = self.get_kernelspec_for_project()
        if spec is not None:
            self.line(f'Kernel <c1>{spec["key"]}</> is already installed!')
            return 1


        # check if pkgs are available
        if not self.has_ipykernel():
            self.line('<error>ipykernel is not installed in this project!</>')
            self.line('You can install it with <c2>poetry add ipykernel -G dev</>')
            return 1

        # get requested config details
        kernel = self.get_requested_kernel_opts()

        # get icon
        if kernel['icon'] is not None and not os.path.exists(kernel['icon']):
            self.line(f'<error>Requested icon {kernel["icon"]} does not exist!')
            return 1



        with tempfile.TemporaryDirectory() as tmpdir:
            spec = {
                 'argv': [
                     self.get_venv().python,
                     '-m',
                     'ipykernel_launcher',
                     '-f',
                     '{connection_file}'
                 ],
                 'display_name': kernel['display'],
                 'env': {},
                 'interrupt_mode': 'signal',
                 'language': 'python',
                 'metadata': {'debugger': True}
            }

            # asset lib only gets you bytes, so we'll do it like this
            if kernel['icon'] is None:
                icon_data = asset.load('poetry_jupyter_plugin:assets/poetry.png').read()
            else:
                icon_data = open(kernel['icon'], 'rb').read()

            with open(os.path.join(tmpdir, 'logo-32x32.png'), 'wb') as fp:
                fp.write(icon_data)

            with open(os.path.join(tmpdir, 'logo-64x64.png'), 'wb') as fp:
                fp.write(icon_data)

            with open(os.path.join(tmpdir, 'kernel.json'), 'w') as fp:
                json.dump(spec, fp, indent=4)

            manager = KernelSpecManager()
            manager.install_kernel_spec(
                tmpdir,
                kernel_name=kernel['name'],
                user=True
            )

        self.line(f'Kernel <c1>{kernel["name"]}</> has been installed!')

        return 0


class JupyterDisableCommand(JupyterCommand):

    name = 'jupyter remove'
    description = 'Remove this project\'s Jupyter kernel.'

    def handle(self):
        spec = self.get_kernelspec_for_project()
        kernel = self.get_requested_kernel_opts()
        if spec is None:
            self.line(f'Kernel <c1>{kernel["name"]}</> is not installed!')
            return 1

        if not self.confirm(f'Really remove kernel <c2>{kernel["name"]}</c2>?', False):
            return 0

        manager = KernelSpecManager()

        manager.remove_kernel_spec(kernel['name'])

        self.line(f'\nSuccessfully removed kernel <c1>{kernel["name"]}</>.')

        return 0


class JupyterKernelPlugin(ApplicationPlugin):
    def activate(self, application):
        commands = [
            ('jupyter show', lambda: JupyterShowCommand()),
            ('jupyter install', lambda: JupyterEnableCommand()),
            ('jupyter remove', lambda: JupyterDisableCommand())
        ]

    
        for command, factory in commands:
            application.command_loader.register_factory(
                command,
                factory
            )
