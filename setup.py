import os
import glob
import sys
from sys import platform as _platform
from setuptools import setup, find_packages
from setuptools.extension import Extension
from setuptools.command.build_ext import build_ext as _build_ext
from setuptools.command.sdist import sdist as _sdist
from setupext import \
    check_for_openmp, \
    check_for_pyembree, \
    read_embree_location, \
    in_conda_env
from distutils.version import LooseVersion
import pkg_resources


if sys.version_info < (2, 7) or (3, 0) < sys.version_info < (3, 5):
    print("yt currently supports Python 2.7 or versions newer than Python 3.5")
    print("certain features may fail unexpectedly and silently with older "
          "versions.")
    sys.exit(1)

try:
    distribute_ver = \
        LooseVersion(pkg_resources.get_distribution("distribute").version)
    if distribute_ver < LooseVersion("0.7.3"):
        print("Distribute is a legacy package obsoleted by setuptools.")
        print("We strongly recommend that you just uninstall it.")
        print("If for some reason you cannot do it, you'll need to upgrade it")
        print("to latest version before proceeding:")
        print("    pip install -U distribute")
        sys.exit(1)
except pkg_resources.DistributionNotFound:
    pass  # yay!

VERSION = "3.6.dev0"

if os.path.exists('MANIFEST'):
    os.remove('MANIFEST')

with open('README.md') as file:
    long_description = file.read()

if check_for_openmp() is True:
    omp_args = ['-fopenmp']
else:
    omp_args = None

if os.name == "nt":
    std_libs = []
else:
    std_libs = ["m"]

cython_extensions = [
    Extension("yt.analysis_modules.photon_simulator.utils",
              ["yt/analysis_modules/photon_simulator/utils.pyx"],
              include_dirs=["yt/utilities/lib"]),
    Extension("yt.analysis_modules.ppv_cube.ppv_utils",
              ["yt/analysis_modules/ppv_cube/ppv_utils.pyx"],
              libraries=std_libs),
    Extension("yt.utilities.lib.contour_finding",
              ["yt/utilities/lib/contour_finding.pyx"],
              include_dirs=["yt/utilities/lib/",
                            "yt/geometry/"],
              libraries=std_libs),
    Extension("yt.utilities.lib.geometry_utils",
              ["yt/utilities/lib/geometry_utils.pyx"],
              extra_compile_args=omp_args,
              extra_link_args=omp_args,
              libraries=std_libs),
    Extension("yt.utilities.lib.mesh_triangulation",
              ["yt/utilities/lib/mesh_triangulation.pyx"],
              depends=["yt/utilities/lib/mesh_triangulation.h"]),
    Extension("yt.utilities.lib.origami",
              ["yt/utilities/lib/origami.pyx",
               "yt/utilities/lib/origami_tags.c"],
              include_dirs=["yt/utilities/lib/"],
              depends=["yt/utilities/lib/origami_tags.h"]),
    Extension("yt.utilities.lib.grid_traversal",
              ["yt/utilities/lib/grid_traversal.pyx",
               "yt/utilities/lib/fixed_interpolator.c"],
              include_dirs=["yt/utilities/lib/"],
              libraries=std_libs,
              depends=["yt/utilities/lib/fixed_interpolator.h"]),
    Extension("yt.utilities.lib.image_samplers",
              ["yt/utilities/lib/image_samplers.pyx",
               "yt/utilities/lib/fixed_interpolator.c"],
              include_dirs=["yt/utilities/lib/"],
              libraries=std_libs,
              extra_compile_args=omp_args,
              extra_link_args=omp_args,
              depends=["yt/utilities/lib/fixed_interpolator.h"]),
    Extension("yt.utilities.lib.partitioned_grid",
              ["yt/utilities/lib/partitioned_grid.pyx",
               "yt/utilities/lib/fixed_interpolator.c"],
              include_dirs=["yt/utilities/lib/"],
              libraries=std_libs,
              depends=["yt/utilities/lib/fixed_interpolator.h"]),
    Extension("yt.utilities.lib.misc_utilities",
              ["yt/utilities/lib/misc_utilities.pyx"],
              extra_compile_args=omp_args,
              extra_link_args=omp_args,
              libraries=std_libs),
    Extension("yt.frontends.ramses.io_utils",
              ["yt/frontends/ramses/io_utils.pyx"],
              include_dirs=["yt/utilities/lib"],
              libraries=std_libs),
    Extension("yt.utilities.cython_fortran_utils",
              ["yt/utilities/cython_fortran_utils.pyx"],
              libraries=std_libs),
]

import yaml

ext_info = yaml.load(open("extensions.yml", "r"))
for lib_collection in ext_info:
    info = ext_info[lib_collection]
    libraries = []
    extra_link_args = []
    extra_compile_args = []
    if info.get("std_libs", False):
        libraries += std_libs
    if info.get("openmp", False):
        extra_link_args += omp_args
        extra_compile_args += omp_args
    depends = info.get("depends", [])
    include_dirs = info.get("include_dirs", [])
    for ext_name in info['names']:
        if isinstance(ext_name, dict):
            assert(len(ext_name) == 1)
            key_name = list(ext_name.keys())[0]
            sources = [info['path_format'].format(key_name)] + ext_name[key_name]
            ext_name = key_name
        else:
            sources = [info['path_format'].format(ext_name)]
        cython_extensions.append(
            Extension(info['name_format'].format(ext_name),
                      sources,
                      libraries = libraries,
                      include_dirs = include_dirs,
                      extra_link_args = extra_link_args,
                      extra_compile_args = extra_compile_args,
                      depends = depends)
        )

extensions = [
    Extension("yt.analysis_modules.halo_finding.fof.EnzoFOF",
              ["yt/analysis_modules/halo_finding/fof/EnzoFOF.c",
               "yt/analysis_modules/halo_finding/fof/kd.c"],
              libraries=std_libs),
    Extension("yt.analysis_modules.halo_finding.hop.EnzoHop",
              sorted(glob.glob("yt/analysis_modules/halo_finding/hop/*.c"))),
    Extension("yt.frontends.artio._artio_caller",
              ["yt/frontends/artio/_artio_caller.pyx"] +
              sorted(glob.glob("yt/frontends/artio/artio_headers/*.c")),
              include_dirs=["yt/frontends/artio/artio_headers/",
                            "yt/geometry/",
                            "yt/utilities/lib/"],
              depends=glob.glob("yt/frontends/artio/artio_headers/*.c")),
]

# EMBREE
if check_for_pyembree() is not None:
    embree_extensions = [
        Extension("yt.utilities.lib.mesh_construction",
                  ["yt/utilities/lib/mesh_construction.pyx"],
                  depends=["yt/utilities/lib/mesh_triangulation.h"]),
        Extension("yt.utilities.lib.mesh_traversal",
                  ["yt/utilities/lib/mesh_traversal.pyx"]),
        Extension("yt.utilities.lib.mesh_samplers",
                  ["yt/utilities/lib/mesh_samplers.pyx"]),
        Extension("yt.utilities.lib.mesh_intersection",
                  ["yt/utilities/lib/mesh_intersection.pyx"]),
    ]

    embree_prefix = os.path.abspath(read_embree_location())
    embree_inc_dir = [os.path.join(embree_prefix, 'include')]
    embree_lib_dir = [os.path.join(embree_prefix, 'lib')]
    if in_conda_env():
        conda_basedir = os.path.dirname(os.path.dirname(sys.executable))
        embree_inc_dir.append(os.path.join(conda_basedir, 'include'))
        embree_lib_dir.append(os.path.join(conda_basedir, 'lib'))

    if _platform == "darwin":
        embree_lib_name = "embree.2"
    else:
        embree_lib_name = "embree"

    for ext in embree_extensions:
        ext.include_dirs += embree_inc_dir
        ext.library_dirs += embree_lib_dir
        ext.language = "c++"
        ext.libraries += std_libs
        ext.libraries += [embree_lib_name]

    cython_extensions += embree_extensions

# ROCKSTAR
if os.path.exists("rockstar.cfg"):
    try:
        rd = open("rockstar.cfg").read().strip()
    except IOError:
        print("Reading Rockstar location from rockstar.cfg failed.")
        print("Please place the base directory of your")
        print("Rockstar install in rockstar.cfg and restart.")
        print("(ex: \"echo '/path/to/Rockstar-0.99' > rockstar.cfg\" )")
        sys.exit(1)

    rockstar_extdir = "yt/analysis_modules/halo_finding/rockstar"
    rockstar_extensions = [
        Extension("yt.analysis_modules.halo_finding.rockstar.rockstar_interface",
                  sources=[os.path.join(rockstar_extdir, "rockstar_interface.pyx")]),
        Extension("yt.analysis_modules.halo_finding.rockstar.rockstar_groupies",
                  sources=[os.path.join(rockstar_extdir, "rockstar_groupies.pyx")])
    ]
    for ext in rockstar_extensions:
        ext.library_dirs.append(rd)
        ext.libraries.append("rockstar")
        ext.define_macros.append(("THREADSAFE", ""))
        ext.include_dirs += [rd,
                             os.path.join(rd, "io"), os.path.join(rd, "util")]
    extensions += rockstar_extensions

if os.environ.get("GPERFTOOLS", "no").upper() != "NO":
    gpd = os.environ["GPERFTOOLS"]
    idir = os.path.join(gpd, "include")
    ldir = os.path.join(gpd, "lib")
    print(("INCLUDE AND LIB DIRS", idir, ldir))
    cython_extensions.append(
        Extension("yt.utilities.lib.perftools_wrap",
                  ["yt/utilities/lib/perftools_wrap.pyx"],
                  libraries=["profiler"],
                  library_dirs=[ldir],
                  include_dirs=[idir]))

class build_ext(_build_ext):
    # subclass setuptools extension builder to avoid importing cython and numpy
    # at top level in setup.py. See http://stackoverflow.com/a/21621689/1382869
    def finalize_options(self):
        try:
            import cython
            import numpy
        except ImportError:
            raise ImportError(
"""Could not import cython or numpy. Building yt from source requires
cython and numpy to be installed. Please install these packages using
the appropriate package manager for your python environment.""")
        if LooseVersion(cython.__version__) < LooseVersion('0.24'):
            raise RuntimeError(
"""Building yt from source requires Cython 0.24 or newer but
Cython %s is installed. Please update Cython using the appropriate
package manager for your python environment.""" %
                cython.__version__)
        if LooseVersion(numpy.__version__) < LooseVersion('1.10.4'):
            raise RuntimeError(
"""Building yt from source requires NumPy 1.10.4 or newer but
NumPy %s is installed. Please update NumPy using the appropriate
package manager for your python environment.""" %
                numpy.__version__)
        from Cython.Build import cythonize
        self.distribution.ext_modules[:] = cythonize(
            self.distribution.ext_modules,
            compiler_directives={'language_level': 2})
        _build_ext.finalize_options(self)
        # Prevent numpy from thinking it is still in its setup process
        # see http://stackoverflow.com/a/21621493/1382869
        if isinstance(__builtins__, dict):
            # sometimes this is a dict so we need to check for that
            # https://docs.python.org/3/library/builtins.html
            __builtins__["__NUMPY_SETUP__"] = False
        else:
            __builtins__.__NUMPY_SETUP__ = False
        self.include_dirs.append(numpy.get_include())

class sdist(_sdist):
    # subclass setuptools source distribution builder to ensure cython
    # generated C files are included in source distribution.
    # See http://stackoverflow.com/a/18418524/1382869
    def run(self):
        # Make sure the compiled Cython files in the distribution are up-to-date
        from Cython.Build import cythonize
        cythonize(
            cython_extensions,
            compiler_directives={'language_level': 2},
        )
        _sdist.run(self)

setup(
    name="yt",
    version=VERSION,
    description="An analysis and visualization toolkit for volumetric data",
    long_description = long_description,
    long_description_content_type='text/markdown',
    classifiers=["Development Status :: 5 - Production/Stable",
                 "Environment :: Console",
                 "Intended Audience :: Science/Research",
                 "License :: OSI Approved :: BSD License",
                 "Operating System :: MacOS :: MacOS X",
                 "Operating System :: POSIX :: AIX",
                 "Operating System :: POSIX :: Linux",
                 "Programming Language :: C",
                 "Programming Language :: Python :: 2",
                 "Programming Language :: Python :: 2.7",
                 "Programming Language :: Python :: 3",
                 "Programming Language :: Python :: 3.4",
                 "Programming Language :: Python :: 3.5",
                 "Topic :: Scientific/Engineering :: Astronomy",
                 "Topic :: Scientific/Engineering :: Physics",
                 "Topic :: Scientific/Engineering :: Visualization",
                 "Framework :: Matplotlib"],
    keywords='astronomy astrophysics visualization ' +
    'amr adaptivemeshrefinement',
    entry_points={'console_scripts': [
        'yt = yt.utilities.command_line:run_main',
    ],
        'nose.plugins.0.10': [
            'answer-testing = yt.utilities.answer_testing.framework:AnswerTesting'
    ]
    },
    packages=find_packages(),
    include_package_data = True,
    install_requires=[
        'matplotlib>=1.5.3',
        'setuptools>=19.6',
        'sympy>=1.0',
        'numpy>=1.10.4',
        'IPython>=1.0',
    ],
    extras_require = {
        'hub':  ["girder_client"],
        'mapserver': ["bottle"]
    },
    cmdclass={'sdist': sdist, 'build_ext': build_ext},
    author="The yt project",
    author_email="yt-dev@python.org",
    url="https://github.com/yt-project/yt",
    project_urls={
        'Homepage': 'https://yt-project.org/',
        'Documentation': 'https://yt-project.org/doc/',
        'Source': 'https://github.com/yt-project/yt/',
        'Tracker': 'https://github.com/yt-project/yt/issues'
    },
    license="BSD 3-Clause",
    zip_safe=False,
    scripts=["scripts/iyt"],
    ext_modules=cython_extensions + extensions,
    python_requires='>=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*,!=3.4.*'
)
