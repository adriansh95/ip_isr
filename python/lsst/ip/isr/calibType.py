# This file is part of ip_isr.
#
# Developed for the LSST Data Management System.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import abc
import copy
import datetime
import os.path
import warnings
import yaml
from astropy.table import Table
from astropy.io import fits

from lsst.log import Log
from lsst.daf.base import PropertyList


__all__ = ["IsrCalib", "IsrProvenance"]


class IsrCalib(abc.ABC):
    """Generic calibration type.

    Subclasses must implement the toDict, fromDict, toTable, fromTable
    methods that allow the calibration information to be converted
    from dictionaries and afw tables.  This will allow the calibration
    to be persisted using the base class read/write methods.

    The validate method is intended to provide a common way to check
    that the calibration is valid (internally consistent) and
    appropriate (usable with the intended data).  The apply method is
    intended to allow the calibration to be applied in a consistent
    manner.

    Parameters
    ----------
    detectorName : `str`, optional
        Name of the detector this calibration is for.
    detectorSerial : `str`, optional
        Identifier for the detector.
    detector : `lsst.afw.cameraGeom.Detector`, optional
        Detector to extract metadata from.
    log : `lsst.log.Log`, optional
        Log for messages.

    """
    _OBSTYPE = 'generic'
    _SCHEMA = 'NO SCHEMA'
    _VERSION = 0

    def __init__(self, detectorName=None, detectorSerial=None, detectorId=None,
                 detector=None, log=None, **kwargs):
        self._detectorName = detectorName
        self._detectorSerial = detectorSerial
        self._detectorId = detectorId
        self.setMetadata(PropertyList())

        # Define the required attributes for this calibration.
        self.requiredAttributes = set(['_OBSTYPE', '_SCHEMA', '_VERSION'])
        self.requiredAttributes.update(['_detectorName', '_detectorSerial', '_metadata'])

        self.log = log if log else Log.getLogger(__name__.partition(".")[2])

        if detector:
            self.fromDetector(detector)
        self.updateMetadata(setDate=False)

    def __str__(self):
        return f"{self.__class__.__name__}(obstype={self._OBSTYPE}, detector={self._detectorName}, )"

    def __eq__(self, other):
        """Calibration equivalence.

        Subclasses will need to check specific sub-properties.  The
        default is only to check common entries.
        """
        if not isinstance(other, self.__class__):
            return False

        for attr in self._requiredAttributes:
            if getattr(self, attr) != getattr(other, attr):
                return False

        return True

    @property
    def requiredAttributes(self):
        return self._requiredAttributes

    @requiredAttributes.setter
    def requiredAttributes(self, value):
        self._requiredAttributes = value

    def getMetadata(self):

        """Retrieve metadata associated with this calibration.

        Returns
        -------
        meta : `lsst.daf.base.PropertyList`
            Metadata. The returned `~lsst.daf.base.PropertyList` can be
            modified by the caller and the changes will be written to
            external files.
        """
        return self._metadata

    def setMetadata(self, metadata):
        """Store a copy of the supplied metadata with this calibration.

        Parameters
        ----------
        metadata : `lsst.daf.base.PropertyList`
            Metadata to associate with the calibration.  Will be copied and
            overwrite existing metadata.
        """
        if metadata is not None:
            self._metadata = copy.copy(metadata)

        # Ensure that we have the obs type required by calibration ingest
        self._metadata["OBSTYPE"] = self._OBSTYPE
        self._metadata[self._OBSTYPE + "_SCHEMA"] = self._SCHEMA
        self._metadata[self._OBSTYPE + "_VERSION"] = self._VERSION

    def updateMetadata(self, setDate=False, **kwargs):
        """Update metadata keywords with new values.

        Parameters
        ----------
        setDate : `bool`, optional
            Ensure the metadata CALIBDATE fields are set to the current datetime.
        kwargs : `dict` or `collections.abc.Mapping`, optional
            Set of key=value pairs to assign to the metadata.
        """
        mdOriginal = self.getMetadata()
        mdSupplemental = dict()

        self._metadata["DETECTOR"] = self._detectorName
        self._metadata["DETECTOR_SERIAL"] = self._detectorSerial

        if setDate:
            date = datetime.datetime.now()
            mdSupplemental['CALIBDATE'] = date.isoformat()
            mdSupplemental['CALIB_CREATION_DATE'] = date.date().isoformat()
            mdSupplemental['CALIB_CREATION_TIME'] = date.time().isoformat()

        mdSupplemental.update(kwargs)
        mdOriginal.update(mdSupplemental)

    @classmethod
    def readText(cls, filename):
        """Read calibration representation from a yaml/ecsv file.

        Parameters
        ----------
        filename : `str`
            Name of the file containing the calibration definition.

        Returns
        -------
        calib : `~lsst.ip.isr.IsrCalibType`
            Calibration class.

        Raises
        ------
        RuntimeError :
            Raised if the filename does not end in ".ecsv" or ".yaml".
        """
        if filename.endswith((".ecsv", ".ECSV")):
            data = Table.read(filename, format='ascii.ecsv')
            return cls.fromTable([data])

        elif filename.endswith((".yaml", ".YAML")):
            with open(filename, 'r') as f:
                data = yaml.load(f, Loader=yaml.CLoader)
            return cls.fromDict(data)
        else:
            raise RuntimeError(f"Unknown filename extension: {filename}")

    def writeText(self, filename, format='auto'):
        """Write the calibration data to a text file.

        Parameters
        ----------
        filename : `str`
            Name of the file to write.
        format : `str`
            Format to write the file as.  Supported values are:
                ``"auto"`` : Determine filetype from filename.
                ``"yaml"`` : Write as yaml.
                ``"ecsv"`` : Write as ecsv.
        Returns
        -------
        used : `str`
            The name of the file used to write the data.  This may
            differ from the input if the format is explicitly chosen.

        Raises
        ------
        RuntimeError :
            Raised if filename does not end in a known extension, or
            if all information cannot be written.

        Notes
        -----
        The file is written to YAML/ECSV format and will include any
        associated metadata.

        """
        if format == 'yaml' or (format == 'auto' and filename.lower().endswith((".yaml", ".YAML"))):
            outDict = self.toDict()
            path, ext = os.path.splitext(filename)
            filename = path + ".yaml"
            with open(filename, 'w') as f:
                yaml.dump(outDict, f)
        elif format == 'ecsv' or (format == 'auto' and filename.lower().endswith((".ecsv", ".ECSV"))):
            tableList = self.toTable()
            if len(tableList) > 1:
                # ECSV doesn't support multiple tables per file, so we
                # can only write the first table.
                raise RuntimeError(f"Unable to persist {len(tableList)}tables in ECSV format.")

            table = tableList[0]
            path, ext = os.path.splitext(filename)
            filename = path + ".ecsv"
            table.write(filename, format="ascii.ecsv")
        else:
            raise RuntimeError(f"Attempt to write to a file {filename} "
                               "that does not end in '.yaml' or '.ecsv'")

        return filename

    @classmethod
    def readFits(cls, filename):
        """Read calibration data from a FITS file.

        Parameters
        ----------
        filename : `str`
            Filename to read data from.

        Returns
        -------
        calib : `lsst.ip.isr.IsrCalib`
            Calibration contained within the file.
        """
        tableList = []
        tableList.append(Table.read(filename, hdu=1))
        extNum = 2  # Fits indices start at 1, we've read one already.
        try:
            with warnings.catch_warnings("error"):
                newTable = Table.read(filename, hdu=extNum)
                tableList.append(newTable)
                extNum += 1
        except Exception:
            pass

        return cls.fromTable(tableList)

    def writeFits(self, filename):
        """Write calibration data to a FITS file.

        Parameters
        ----------
        filename : `str`
            Filename to write data to.

        Returns
        -------
        used : `str`
            The name of the file used to write the data.

        """
        tableList = self.toTable()
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=Warning, module="astropy.io")
            astropyList = [fits.table_to_hdu(table) for table in tableList]
            astropyList.insert(0, fits.PrimaryHDU())

            writer = fits.HDUList(astropyList)
            writer.writeto(filename, overwrite=True)
        return filename

    def fromDetector(self, detector):
        """Modify the calibration parameters to match the supplied detector.

        Parameters
        ----------
        detector : `lsst.afw.cameraGeom.Detector`
            Detector to use to set parameters from.

        Raises
        ------
        NotImplementedError
            This needs to be implemented by subclasses for each
            calibration type.
        """
        raise NotImplementedError("Must be implemented by subclass.")

    @classmethod
    def fromDict(cls, dictionary):
        """Construct a calibration from a dictionary of properties.

        Must be implemented by the specific calibration subclasses.

        Parameters
        ----------
        dictionary : `dict`
            Dictionary of properties.

        Returns
        ------
        calib : `lsst.ip.isr.CalibType`
            Constructed calibration.

        Raises
        ------
        NotImplementedError :
            Raised if not implemented.
        """
        raise NotImplementedError("Must be implemented by subclass.")

    def toDict(self):
        """Return a dictionary containing the calibration properties.

        The dictionary should be able to be round-tripped through
        `fromDict`.

        Returns
        -------
        dictionary : `dict`
            Dictionary of properties.

        Raises
        ------
        NotImplementedError :
            Raised if not implemented.
        """
        raise NotImplementedError("Must be implemented by subclass.")

    @classmethod
    def fromTable(cls, tableList):
        """Construct a calibration from a dictionary of properties.

        Must be implemented by the specific calibration subclasses.

        Parameters
        ----------
        tableList : `list` [`lsst.afw.table.Table`]
            List of tables of properties.

        Returns
        ------
        calib : `lsst.ip.isr.CalibType`
            Constructed calibration.

        Raises
        ------
        NotImplementedError :
            Raised if not implemented.
        """
        raise NotImplementedError("Must be implemented by subclass.")

    def toTable(self):
        """Return a list of tables containing the calibration properties.

        The table list should be able to be round-tripped through
        `fromDict`.

        Returns
        -------
        tableList : `list` [`lsst.afw.table.Table`]
            List of tables of properties.

        Raises
        ------
        NotImplementedError :
            Raised if not implemented.
        """
        raise NotImplementedError("Must be implemented by subclass.")

    def validate(self, other=None):
        """Validate that this calibration is defined and can be used.

        Parameters
        ----------
        other : `object`, optional
            Thing to validate against.

        Returns
        -------
        valid : `bool`
            Returns true if the calibration is valid and appropriate.
        """
        return False

    def apply(self, target):
        """Method to apply the calibration to the target object.

        Parameters
        ----------
        target : `object`
            Thing to validate against.

        Returns
        -------
        valid : `bool`
            Returns true if the calibration was applied correctly.

        Raises
        ------
        NotImplementedError :
            Raised if not implemented.
        """
        raise NotImplementedError("Must be implemented by subclass.")


class IsrProvenance(IsrCalib):
    """Class for the provenance of data used to construct calibration.

    Provenance is not really a calibration, but we would like to
    record this when constructing the calibration, and it provides an
    example of the base calibration class.

    Parameters
    ----------
    instrument : `str`, optional
        Name of the instrument the data was taken with.
    calibType : `str`, optional
        Type of calibration this provenance was generated for.
    detectorName : `str`, optional
        Name of the detector this calibration is for.
    detectorSerial : `str`, optional
        Identifier for the detector.

    """
    _OBSTYPE = 'IsrProvenance'

    def __init__(self, instrument="unknown", calibType="unknown",
                 **kwargs):
        self.instrument = instrument
        self.calibType = calibType
        self.dimensions = set()
        self.dataIdList = list()

        super().__init__(**kwargs)

        self.requiredAttributes.update(['instrument', 'calibType', 'dimensions', 'dataIdList'])

    def __str__(self):
        return f"{self.__class__.__name__}(obstype={self._OBSTYPE}, calibType={self.calibType}, )"

    def __eq__(self, other):
        return super().__eq__(other)

    def updateMetadata(self, setDate=False, **kwargs):
        """Update calibration metadata.

        Parameters
        ----------
        setDate : `bool, optional
            Update the CALIBDATE fields in the metadata to the current
            time. Defaults to False.
        kwargs : `dict` or `collections.abc.Mapping`, optional
            Other keyword parameters to set in the metadata.
        """
        kwargs["DETECTOR"] = self._detectorName
        kwargs["DETECTOR_SERIAL"] = self._detectorSerial

        kwargs['INSTRUME'] = self.instrument
        kwargs['calibType'] = self.calibType
        super().updateMetadata(setDate=setDate, **kwargs)

    def fromDataIds(self, dataIdList):
        """Update provenance from dataId List.

        Parameters
        ----------
        dataIdList : `list` [`lsst.daf.butler.DataId`]
            List of dataIds used in generating this calibration.
        """
        for dataId in dataIdList:
            for key in dataId:
                if key not in self.dimensions:
                    self.dimensions.add(key)
            self.dataIdList.append(dataId)

    @classmethod
    def fromTable(cls, tableList):
        """Construct provenance from table list.

        Parameters
        ----------
        tableList : `list` [`lsst.afw.table.Table`]
            List of tables to construct the provenance from.

        Returns
        -------
        provenance : `lsst.ip.isr.IsrProvenance`
            The provenance defined in the tables.
        """
        table = tableList[0]
        metadata = table.meta
        inDict = dict()
        inDict['metadata'] = metadata
        inDict['detectorName'] = metadata['DETECTOR']
        inDict['detectorSerial'] = metadata['DETECTOR_SERIAL']
        inDict['instrument'] = metadata['INSTRUME']
        inDict['calibType'] = metadata['calibType']
        inDict['dimensions'] = set()
        inDict['dataIdList'] = list()

        schema = dict()
        for colName in table.columns:
            schema[colName.lower()] = colName
            inDict['dimensions'].add(colName.lower())
        inDict['dimensions'] = sorted(inDict['dimensions'])

        for row in table:
            entry = dict()
            for dim in sorted(inDict['dimensions']):
                entry[dim] = row[schema[dim]]
            inDict['dataIdList'].append(entry)

        return cls.fromDict(inDict)

    @classmethod
    def fromDict(cls, dictionary):
        """Construct provenance from a dictionary.

        Parameters
        ----------
        dictionary : `dict`
            Dictionary of provenance parameters.

        Returns
        -------
        provenance : `lsst.ip.isr.IsrProvenance`
            The provenance defined in the tables.
        """
        calib = cls()
        calib.updateMetadata(setDate=False, **dictionary['metadata'])
        calib._detectorName = dictionary['detectorName']
        calib._detectorSerial = dictionary['detectorSerial']
        calib.instrument = dictionary['instrument']
        calib.calibType = dictionary['calibType']
        calib.dimensions = set(dictionary['dimensions'])
        calib.dataIdList = dictionary['dataIdList']

        calib.updateMetadata()
        return calib

    def toDict(self):
        """Return a dictionary containing the provenance information.

        Returns
        -------
        dictionary : `dict`
            Dictionary of provenance.
        """
        self.updateMetadata(setDate=True)

        outDict = {}

        metadata = self.getMetadata()
        outDict['metadata'] = metadata
        outDict['detectorName'] = self._detectorName
        outDict['detectorSerial'] = self._detectorSerial
        outDict['instrument'] = self.instrument
        outDict['calibType'] = self.calibType
        outDict['dimensions'] = list(self.dimensions)
        outDict['dataIdList'] = self.dataIdList

        return outDict

    def toTable(self):
        """Return a list of tables containing the provenance.

        This seems inefficient and slow, so this may not be the best
        way to store the data.

        Returns
        -------
        tableList : `list` [`lsst.afw.table.Table`]
            List of tables containing the provenance information

        """
        tableList = []
        self.updateMetadata(setDate=True)
        catalog = Table(rows=self.dataIdList,
                        names=self.dimensions)
        catalog.meta = self.getMetadata().toDict()
        tableList.append(catalog)
        return tableList
