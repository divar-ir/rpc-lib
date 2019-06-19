import os
import pkg_resources
import re
import sys
import subprocess
from shutil import copyfile
from setuptools import find_packages, setup
from setuptools.command.build_py import build_py as _build_py

# taken later modified from https://github.com/numpy/numpy/blob/master/setup.py
# Return the git revision as a string
def run_cmd(cmd):
    cwd = os.path.abspath(os.path.dirname(__file__))
    # construct minimal environment
    env = {}
    for k in ['SYSTEMROOT', 'PATH', 'HOME']:
        v = os.environ.get(k)
        if v is not None:
            env[k] = v
    # LANGUAGE is used on win32
    env['LANGUAGE'] = 'C'
    env['LANG'] = 'C'
    env['LC_ALL'] = 'C'
    child = subprocess.Popen(cmd, stdout=subprocess.PIPE, env=env, cwd=cwd)
    out = child.communicate()[0]
    if child.returncode != 0:
        raise RuntimeError
    return out

def read_version(version_file_path):
    """
    Reads the package version from the supplied file
    :param version_file_path: Path of the file containing current version
    """
    version_file = open(os.path.join(version_file_path)).read()
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", version_file).group(1)


# taken later modified from https://github.com/numpy/numpy/blob/master/setup.py
# Return the git revision as a string
def git_version():
    try:
        out = run_cmd(['git', 'describe', '--abbrev=1', '--tags'])
        GIT_REVISION = out.strip().decode('ascii')
    except:
        try:
            out = run_cmd(['git', 'rev-parse', '--short', 'HEAD'])
            GIT_REVISION = out.strip().decode('ascii')
        except OSError:
            GIT_REVISION = "Unknown"
    return GIT_REVISION

version = git_version()



def build_package_protos(package_root):
    from grpc_tools import protoc

    proto_files = []
    inclusion_root = os.path.abspath(package_root)
    for root, _, files in os.walk(inclusion_root):
        for filename in files:
            if filename.endswith('.proto'):
                proto_files.append(
                    os.path.abspath(os.path.join(root, filename)))

    well_known_protos_include = pkg_resources.resource_filename(
        'grpc_tools', '_proto')

    for proto_file in proto_files:
        command = [
            'grpc_tools.protoc',
            '--proto_path={}'.format(inclusion_root),
            '--proto_path={}'.format(well_known_protos_include),
            '--python_out={}'.format(inclusion_root),
            '--grpc_python_out={}'.format(inclusion_root),
        ] + [proto_file]
        if protoc.main(command) != 0:
            raise Exception('Command {} failed'.format(command))



class BuildExtraPyCommand(_build_py):
    def run(self):
        # Create version file
        with open("src/python/rpc_lib/version.py", "w") as version_file:
            version_file.write("RPC_LIB_VERSION=\"%s\"" % version)
        # Compile protos to python
        os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))
        build_package_protos('src/proto')
        for root, _, files in os.walk('src/proto'):
            for filename in files:
                if filename.endswith('_pb2.py') or filename.endswith('_pb2_grpc.py'):
                    filepath = os.path.join(root, filename)
                    destpath = re.sub('^%s' % 'src/proto', 'src/python', filepath)
                    copyfile(filepath, destpath)
        return _build_py.run(self)


setup(
    name='rpc_lib',
    version=git_version(),
    package_dir={'': 'src/python'},
    packages=find_packages('src/python', exclude=("tests",)),
    include_package_data=True,
    install_requires=[
        "prometheus_client",
        "grpcio-tools",
        "kubernetes",
        "urllib3", # for python 2.7: <=1.23
        "kombu",
    ],
    cmdclass={
        'build_py': BuildExtraPyCommand,
    },
    classifiers=[
        'Programming Language :: Python',
        'Project :: Divar'
    ],
)
