"""
This file provides all kinds of configurable parameters for different application modules. Also, this is a source of the
default project config file stm32pio.ini.

Bottom part of the file contains some definitions specifically targeting continuous integration environment. They have
no effect on normal or test (local) runs.
"""

import inspect
import logging
import os
import platform
import shutil
from pathlib import Path


my_os = platform.system()


def _find_cubemx_executable():
    """Try to locate STM32CubeMX executable automatically.

    Strategies (in order):
    - Environment variables (common names)
    - executable on PATH (shutil.which)
    - common installation locations per-OS
    Returns absolute string path to executable or empty string if not found.
    """
    env_vars = [
        'STM32CUBEMX_HOME', 'STM32_CUBEMX_HOME', 'STM32_CUBEMX', 'STM32CUBEMX',
        'STM32_CUBEMX_PATH', 'STM32CUBEMX_PATH'
    ]

    # Check environment variables
    for v in env_vars:
        val = os.environ.get(v)
        if not val:
            continue
        p = Path(val)
        if p.exists():
            # If it's a directory, try to find the executable inside
            if p.is_dir():
                candidates = [
                    p / 'STM32CubeMX',
                    p / 'STM32CubeMX.exe',
                    p / 'STM32CubeMX.app' / 'Contents' / 'MacOS' / 'STM32CubeMX'
                ]
                for c in candidates:
                    if c.exists():
                        return str(c)
            else:
                return str(p)

    # Check PATH
    exec_name = 'STM32CubeMX.exe' if my_os == 'Windows' else 'STM32CubeMX'
    which_path = shutil.which(exec_name) or shutil.which('STM32CubeMX')
    if which_path:
        return which_path

    # Common locations
    common = []
    if my_os == 'Windows':
        common += [
            Path('C:/Program Files/STMicroelectronics/STM32Cube/STM32CubeMX/STM32CubeMX.exe'),
            Path('C:/Program Files (x86)/STMicroelectronics/STM32Cube/STM32CubeMX/STM32CubeMX.exe'),
            Path('C:/Program Files/STMicroelectronics/STM32CubeMX/STM32CubeMX.exe'),
            Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'STM32CubeMX' / 'STM32CubeMX.exe'
        ]
    elif my_os == 'Darwin':
        common += [
            Path('/Applications/STMicroelectronics/STM32CubeMX.app/Contents/MacOS/STM32CubeMX'),
        ]
    elif my_os == 'Linux':
        common += [
            Path.home() / 'STM32CubeMX' / 'STM32CubeMX',
            Path('/usr/local/bin/STM32CubeMX'),
            Path('/usr/bin/STM32CubeMX'),
        ]

    for p in common:
        try:
            if p and p.exists():
                return str(p)
        except Exception:
            continue

    return ''


def _find_java_bundled_with_cubemx(cubemx_path):
    """Given path to cubemx executable, try to find bundled java inside the CubeMX installation.

    Typical layout on Windows: <install>/jre/bin/java.exe
    Returns absolute string path to java executable or empty string if not found.
    """
    if not cubemx_path:
        return ''
    p = Path(cubemx_path)
    # If path points to the app bundle binary on macOS, go up appropriately
    candidates = []
    # If cubemx is an executable file, its parent folder is the install folder
    install_dir = p.parent
    candidates.append(install_dir / 'jre' / 'bin' / ('java.exe' if my_os == 'Windows' else 'java'))
    # Some installers place jre one level up
    candidates.append(install_dir.parent / 'jre' / 'bin' / ('java.exe' if my_os == 'Windows' else 'java'))
    # On macOS inside app bundle
    candidates.append(p.parent / 'jre' / 'bin' / 'java')

    for c in candidates:
        try:
            if c.exists() and os.access(str(c), os.X_OK):
                return str(c)
        except Exception:
            continue

    return ''

config_file_name = 'stm32pio.ini'

# Detect CubeMX and its bundled Java at import time (but fall back to previous defaults if detection fails)
_detected_cubemx = _find_cubemx_executable()
if not _detected_cubemx:
    # keep previous defaults as fallback
    _detected_cubemx = (
        '/Applications/STMicroelectronics/STM32CubeMX.app/Contents/MacOs/STM32CubeMX' if my_os == 'Darwin' else
        str(Path.home() / 'STM32CubeMX/STM32CubeMX') if my_os == 'Linux' else
        'C:/Program Files/STMicroelectronics/STM32Cube/STM32CubeMX/STM32CubeMX.exe' if my_os == 'Windows' else ''
    )

_detected_java = _find_java_bundled_with_cubemx(_detected_cubemx)
if not _detected_java:
    _detected_java = (
        'C:/Program Files/STMicroelectronics/STM32Cube/STM32CubeMX/jre/bin/java.exe' if my_os == 'Windows' else 'None'
    )

config_default = dict(
    # "app" section is used for listing commands/paths of utilized programs
    app={
        # How do you start the PlatformIO from command line?
        #  - If you're using PlatformIO IDE see
        #    https://docs.platformio.org/en/latest/core/installation.html#piocore-install-shell-commands
        #  - If you're using PlatformIO CLI but it is not available as 'platformio' command, add it to your PATH
        #    environment variable (refer to OS docs)
        #  - Or simply specify here a full path to the PlatformIO executable
        # Note: "python -m platformio" isn't supported yet
        'platformio_cmd': 'platformio',

        # STM32CubeMX doesn't register itself in PATH so we specify a full path to it. Here are default ones (i.e. when
        # you've installed CubeMX on your system)
        'cubemx_cmd': _detected_cubemx,

        # If you're on Windows or you have CubeMX version below 6.3.0, the Java command (which CubeMX is written on)
        # should be specified. For CubeMX starting from 6.3.0 JRE is bundled alongside, otherwise it must be installed
        # by a user yourself separately
        'java_cmd': _detected_java,
    },

    # "project" section focuses on parameters of the concrete stm32pio project
    project={
        # CubeMX can be fed with the script file to read commands from. This template is based on official user manual
        # PDF (UM1718)
        'cubemx_script_content': inspect.cleandoc('''
            config load ${ioc_file_absolute_path}
            generate code ${project_dir_absolute_path}
            exit
        '''),

        # In order for PlatformIO to "understand" a code generated by CubeMX, some tweaks (both in project structure and
        # config files) should be applied. One of them is to inject some properties into the platformio.ini file and
        # this option is a config-like string that should be merged with it. In other words, it should meet INI-style
        # requirements and be a valid platformio.ini config itself
        'platformio_ini_patch_content': inspect.cleandoc('''
            [platformio]
            include_dir = Inc
            src_dir = Src
        '''),

        'board': '',  # one of PlatformIO boards identifiers (e.g. "nucleo_f031k6")

        # CubeMX .ioc project config file. Typically, this will be filled in automatically on project initialization
        'ioc_file': '',

        'cleanup_ignore': '',
        'cleanup_use_git': False,  # controls what method 'clean' command should use

        'inspect_ioc': True
    }
)

# Values to match with on user input (both config and CLI) (use in conjunction with .lower() to ignore case)
none_options = ['none', 'no', 'null', '0']
no_options = ['n', 'no', 'false', '0']
yes_options = ['y', 'yes', 'true', '1']

# CubeMX 0 return code doesn't necessarily mean a successful operation (e.g. migration dialog has appeared and 'Cancel'
# was chosen, or CubeMX_version < ioc_file_version, etc.), we should analyze the actual output (STDOUT)
# noinspection SpellCheckingInspection
cubemx_str_indicating_success = 'Code succesfully generated'
cubemx_str_indicating_error = 'Exception in code generation'  # final line "KO" is also a good sign of error

# Longest name (not necessarily a method so a little bit tricky...)
# log_fieldwidth_function = max([len(member) for member in dir(stm32pio.lib.Stm32pio)]) + 1
log_fieldwidth_function = 20  # TODO: ugly and not so reliable anymore...

show_traceback_threshold_level = logging.DEBUG  # when log some error and need to print a traceback

pio_boards_cache_lifetime = 5.0  # in seconds


#
# Do not distract end-user with this CI s**t, take out from the main dict definition above
#
# TODO: Probably should remove those CI-specific logic from the source code entirely. This problem is related to having
#  an [optional] single (global) config
# Environment variable indicating we are running on a CI server and should tweak some parameters
CI_ENV_VARIABLE = os.environ.get('PIPELINE_WORKSPACE')
if CI_ENV_VARIABLE is not None:
    # TODO: Python 3.8+: some PyCharm static analyzer bug. Probably can be solved after introduction of TypedDict
    # noinspection PyTypedDict
    config_default['app'] = {
        'platformio_cmd': 'platformio',
        'cubemx_cmd': str(Path(os.environ.get('STM32PIO_CUBEMX_CACHE_FOLDER')) / 'STM32CubeMX.exe'),
        'java_cmd': 'java'
    }

    TEST_FIXTURES_PATH = Path(os.environ.get('STM32PIO_TEST_FIXTURES',
                                             default=Path(__file__).parent / '../../tests/fixtures'))
    TEST_CASE = os.environ.get('STM32PIO_TEST_CASE')
    patch_mixin = ''
    if TEST_FIXTURES_PATH is not None and TEST_CASE is not None:
        platformio_ini_lockfile = TEST_FIXTURES_PATH / TEST_CASE / 'platformio.ini.lockfile'
        if platformio_ini_lockfile.exists():
            patch_mixin = '\n\n' + platformio_ini_lockfile.read_text()
    config_default['project']['platformio_ini_patch_content'] += patch_mixin
