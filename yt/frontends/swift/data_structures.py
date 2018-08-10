"""
Data structures for OWLS frontend




"""
from __future__ import print_function

#-----------------------------------------------------------------------------
# Copyright (c) 2014, yt Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import numpy as np

from yt.utilities.on_demand_imports import _h5py as h5py

from uuid import uuid4

from yt.utilities.logger import ytLogger as mylog

from yt.frontends.sph.data_structures import \
    SPHDataset, \
    SPHParticleIndex

from .fields import \
    SwiftFieldInfo

from yt.data_objects.static_output import \
    ParticleFile

class SwiftDataset(SPHDataset):
    _index_class = SPHParticleIndex
    _field_info_class = SwiftFieldInfo
    _file_class = ParticleFile

    _particle_mass_name = "Masses"
    _particle_coordinates_name = "Coordinates"
    _particle_velocity_name = "Velocities"
    _sph_ptype = "PartType0"
    _suffix = ".hdf5"

    def __init__(self, filename, dataset_type='swift',
                 storage_filename=None,
                 units_override=None):

        self.filename = filename

        super().__init__(filename, dataset_type, units_override=units_override)
        self.storage_filename = storage_filename

    def _set_code_unit_attributes(self):
        """
        Sets the units from the SWIFT internal unit system.

        Currently sets length, mass, time, and temperature.

        Swift outputs in proper coordinates  no h factors required.
        """
        units = self._get_info_attributes("Units")

        self.length_unit = self.quan(
            float(units["Unit length in cgs (U_L)"]), "cm")
        self.mass_unit = self.quan(
            float(units["Unit mass in cgs (U_M)"]), "g")
        self.time_unit = self.quan(
            float(units["Unit time in cgs (U_t)"]), "s")
        self.temperature_unit = self.quan(
            float(units["Unit temperature in cgs (U_T)"]), "K")

        return

    def _get_info_attributes(self, dataset):
        """
        Gets the information from a header-style dataset and returns it as a
        python dictionary.

        Example: self._get_info_attributes(header) returns a dictionary of all
        of the information in the Header.attrs.
        """

        with h5py.File(self.filename, "r") as handle:
            header = dict(handle[dataset].attrs)

        return header

    def _parse_parameter_file(self):
        """
        Parse the SWIFT "parameter file" -- really this actually reads info
        from the main HDF5 file as everything is replicated there and usually
        parameterfiles are not transported.

        The header information from the HDF5 file is stored in an un-parsed
        format in self.parameters should users wish to use it.
        """

        self.unique_identifier = uuid4()

        # Read from the HDF5 file, this gives us all the info we need. The rest
        # of this function is just parsing.
        header = self._get_info_attributes("Header")
        runtime_parameters = self._get_info_attributes("RuntimePars")

        policy = self._get_info_attributes("Policy")
        # These are the parameterfile parameters from *.yml at runtime
        parameters = self._get_info_attributes("Parameters")

        # Not used in this function, but passed to parameters
        hydro = self._get_info_attributes("HydroScheme")
        subgrid = self._get_info_attributes("SubgridScheme")

        self.domain_right_edge = header["BoxSize"]
        self.domain_left_edge = np.zeros_like(self.domain_right_edge)

        self.dimensionality = int(header["Dimension"])

        # SWIFT is either all periodic, or not periodic at all
        periodic = int(runtime_parameters["PeriodicBoundariesOn"])

        if periodic:
            self.periodicity = [True] * self.dimensionality
        else:
            self.periodicity = [False] * self.dimensionality

        self.current_time = float(header["Time"])

        # Now cosmology enters the fray, as a runtime parameter.
        self.cosmological_simulation = int(policy["cosmological integration"])

        if self.cosmological_simulation:
            try:
                self.current_redshift = float(header["Redshift"])
                # These won't be present if self.cosmological_simulation is false
                self.omega_lambda = float(parameters["Cosmology:Omega_lambda"])
                self.omega_matter = float(parameters["Cosmology:Omega_m"])
                # This is "little h"
                self.hubble_constant = float(parameters["Cosmology:h"])
            except KeyError:
                mylog.info(
                    "Could not find cosmology information in Parameters."
                )
                mylog.info(
                    "Setting up as a non-cosmological run. Check this!"
                )
                self.cosmological_simulation = 0
                self.current_redshift = 0.0
                self.omega_lambda = 0.0
                self.omega_matter = 0.0
                self.hubble_constant = 0.0
        else:
            self.current_redshift = 0.0
            self.omega_lambda = 0.0
            self.omega_matter = 0.0
            self.hubble_constant = 0.0


        # Store the un-parsed information should people want it.
        self.parameters = dict(
            header=header,
            runtime_parameters=runtime_parameters,
            policy=policy,
            parameters=parameters,
            hydro=hydro,
            subgrid=subgrid)

        ## TODO: we need to deal with num_files per snapshot
        self.file_count = 1
        print(header.keys())
        self.filename_template = self.parameter_filename

        return

    @classmethod
    def _is_valid(self, *args, **kwargs):
        """
        Checks to see if the file is a valid output from SWIFT.
        This requires the file to have the Code attribute set in the
        Header dataset to "SWIFT".
        """
        filename = args[0]
        valid = True
        # Attempt to open the file, if it's not a hdf5 then this will fail:
        try:
            handle = h5py.File(filename, "r")
        except:
            valid = False

        # If we have been able to open the file, we can check for the specific
        # header attribute that has been added to identify SWIFT files
        try:
            valid = handle["Header"].attrs["Code"] == b"SWIFT"
            handle.close()
        except:
            valid = False

        return valid