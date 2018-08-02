#
# LSST Data Management System
# Copyright 2008, 2009, 2010 LSST Corporation.
#
# This product includes software developed by the
# LSST Project (http://www.lsst.org/).
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
# You should have received a copy of the LSST License Statement and
# the GNU General Public License along with this program.  If not,
# see <http://www.lsstcorp.org/LegalNotices/>.
#

import unittest

import numpy as np

import lsst.utils.tests
import lsst.afw.image as afwImage
import lsst.meas.algorithms as measAlg
import lsst.afw.geom as afwGeom
import lsst.afw.display.ds9 as ds9
import lsst.afw.display.utils as displayUtils
import lsst.ip.isr as ipIsr

# set to True to display images in ds9
display = False


class DefectTestCases(lsst.utils.tests.TestCase):

    def setUp(self):
        self.setVal = 10.

    def tearDown(self):
        del self.setVal

    def testDefectBase(self):
        """Test DefectBases"""

        defectList = []
        ccdImage = afwImage.MaskedImageF(250, 225)
        ccdImage.set(self.setVal, 0, self.setVal)
        #
        # Insert some defects into the Ccd
        #
        for x0, y0, x1, y1 in [
            (34, 0, 35, 80),
            (34, 81, 34, 100),
            (180, 100, 182, 130),
        ]:
            bbox = afwGeom.Box2I(afwGeom.Point2I(x0, y0), afwGeom.Point2I(x1, y1), invert=False)
            defectList.append(measAlg.Defect(bbox))
            bad = ccdImage.Factory(ccdImage, bbox, afwImage.LOCAL)
            bad.set(100)

        ipIsr.maskPixelsFromDefectList(ccdImage, defectList, maskName='BAD')
        mask = ccdImage.getMask()
        bitMask = mask.getPlaneBitMask('BAD')
        for d in defectList:
            bad = mask.Factory(mask, d.getBBox(), afwImage.LOCAL)
            self.assertTrue((bad.getArray() & bitMask == bitMask).all())

        if display:
            ds9.mtv(ccdImage.getImage(), title="Defects")
            for d in defectList:
                displayUtils.drawBBox(d.getBBox(), ctype=ds9.CYAN, borderWidth=.5)
            ds9.incrDefaultFrame()

        ipIsr.interpolateDefectList(ccdImage, defectList, 2.)
        im = ccdImage.getImage()
        for d in defectList:
            intrp = im.Factory(im, d.getBBox())
            expect = np.empty_like(intrp.getArray())
            expect[:] = self.setVal
            self.assertImagesEqual(intrp, expect)

        if display:
            ds9.mtv(ccdImage.getImage(), title="Defects Interpolated")
            for d in defectList:
                displayUtils.drawBBox(d.getBBox(), ctype=ds9.CYAN, borderWidth=.5)
            ds9.incrDefaultFrame()

    def testDefectsFromMaskedImage(self):
        """Test creation of a DefectList from a MaskedImage."""
        mim = afwImage.MaskedImageF(10, 10)

        # Nothing masked -> no defects.
        defectList = ipIsr.getDefectListFromMask(mim, "BAD")
        self.assertEqual(len(defectList), 0)

        # Mask a single pixel.
        mask = mim.getMask()
        mask[5, 5, afwImage.LOCAL] = mask.getPlaneBitMask("BAD")
        defectList = ipIsr.getDefectListFromMask(mim, "BAD")
        self.assertEqual(len(defectList), 1)
        self.assertEqual(defectList[0].getX0(), 5)
        self.assertEqual(defectList[0].getY0(), 5)

        # Setting a different plane does not register as a defect.
        mask[1, 1, afwImage.LOCAL] = mask.getPlaneBitMask("SUSPECT")
        defectList = ipIsr.getDefectListFromMask(mim, "SUSPECT")
        self.assertEqual(len(defectList), 1)

        # But adding another BAD pixel does.
        mask[9, 9, afwImage.LOCAL] = mask.getPlaneBitMask("BAD")
        defectList = ipIsr.getDefectListFromMask(mim, "BAD")
        self.assertEqual(len(defectList), 2)


class MemoryTester(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()
