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

import lsst.utils.tests
import lsst.geom
import lsst.afw.image as afwImage
import lsst.ip.isr as ipIsr


class IsrTestCases(lsst.utils.tests.TestCase):

    def setUp(self):
        self.overscanKeyword = "BIASSEC"

    def tearDown(self):
        del self.overscanKeyword

    def testOverscanCorrectionY(self, **kwargs):
        bbox = lsst.geom.Box2I(lsst.geom.Point2I(0, 0),
                               lsst.geom.Point2I(9, 12))
        maskedImage = afwImage.MaskedImageF(bbox)
        maskedImage.set(10, 0x0, 1)

        dataBox = lsst.geom.Box2I(lsst.geom.Point2I(0, 0), lsst.geom.Extent2I(10, 10))
        dataImage = afwImage.MaskedImageF(maskedImage, dataBox)

        # these should be functionally equivalent
        bbox = lsst.geom.Box2I(lsst.geom.Point2I(0, 10),
                               lsst.geom.Point2I(9, 12))
        biassec = '[1:10,11:13]'
        overscan = afwImage.MaskedImageF(maskedImage, bbox)
        overscan.set(2, 0x0, 1)

        exposure = afwImage.ExposureF(maskedImage, None)
        metadata = exposure.getMetadata()
        metadata.setString(self.overscanKeyword, biassec)

        ipIsr.overscanCorrection(dataImage, overscan.getImage(), **kwargs)

        height = maskedImage.getHeight()
        width = maskedImage.getWidth()
        for j in range(height):
            for i in range(width):
                if j >= 10:
                    self.assertEqual(maskedImage.image[i, j, afwImage.LOCAL], 0)
                else:
                    self.assertEqual(maskedImage.image[i, j, afwImage.LOCAL], 8)

    def testOverscanCorrectionX(self, **kwargs):
        bbox = lsst.geom.Box2I(lsst.geom.Point2I(0, 0),
                               lsst.geom.Point2I(12, 9))
        maskedImage = afwImage.MaskedImageF(bbox)
        maskedImage.set(10, 0x0, 1)

        dataBox = lsst.geom.Box2I(lsst.geom.Point2I(0, 0), lsst.geom.Extent2I(10, 10))
        dataImage = afwImage.MaskedImageF(maskedImage, dataBox)

        # these should be functionally equivalent
        bbox = lsst.geom.Box2I(lsst.geom.Point2I(10, 0),
                               lsst.geom.Point2I(12, 9))
        biassec = '[11:13,1:10]'
        overscan = afwImage.MaskedImageF(maskedImage, bbox)
        overscan.set(2, 0x0, 1)

        exposure = afwImage.ExposureF(maskedImage, None)
        metadata = exposure.getMetadata()
        metadata.setString(self.overscanKeyword, biassec)

        ipIsr.overscanCorrection(dataImage, overscan.getImage(), **kwargs)

        height = maskedImage.getHeight()
        width = maskedImage.getWidth()
        for j in range(height):
            for i in range(width):
                if i >= 10:
                    self.assertEqual(maskedImage.image[i, j, afwImage.LOCAL], 0)
                else:
                    self.assertEqual(maskedImage.image[i, j, afwImage.LOCAL], 8)

    def testMedianAndMedianPerRowOverscanCorrection(self):
        for fitType in ("MEDIAN", "MEDIAN_PER_ROW"):
            self.testOverscanCorrectionX(fitType=fitType)
            self.testOverscanCorrectionY(fitType=fitType)

    def checkPolyOverscanCorrectionX(self, **kwargs):
        bbox = lsst.geom.Box2I(lsst.geom.Point2I(0, 0),
                               lsst.geom.Point2I(12, 9))
        maskedImage = afwImage.MaskedImageF(bbox)
        maskedImage.set(10, 0x0, 1)

        dataBox = lsst.geom.Box2I(lsst.geom.Point2I(0, 0), lsst.geom.Extent2I(10, 10))
        dataImage = afwImage.MaskedImageF(maskedImage, dataBox)

        # these should be functionally equivalent
        bbox = lsst.geom.Box2I(lsst.geom.Point2I(10, 0),
                               lsst.geom.Point2I(12, 9))
        overscan = afwImage.MaskedImageF(maskedImage, bbox)
        overscan.set(2, 0x0, 1)
        for i in range(bbox.getDimensions()[1]):
            for j, off in enumerate([-0.5, 0.0, 0.5]):
                overscan.image[j, i, afwImage.LOCAL] = 2+i+off

        ipIsr.overscanCorrection(dataImage, overscan.getImage(), **kwargs)

        height = maskedImage.getHeight()
        width = maskedImage.getWidth()
        for j in range(height):
            for i in range(width):
                if i == 10:
                    self.assertEqual(maskedImage.image[i, j, afwImage.LOCAL], -0.5)
                elif i == 11:
                    self.assertEqual(maskedImage.image[i, j, afwImage.LOCAL], 0)
                elif i == 12:
                    self.assertEqual(maskedImage.image[i, j, afwImage.LOCAL], 0.5)
                else:
                    self.assertEqual(maskedImage.image[i, j, afwImage.LOCAL], 10 - 2 - j)

    def checkPolyOverscanCorrectionY(self, **kwargs):
        bbox = lsst.geom.Box2I(lsst.geom.Point2I(0, 0),
                               lsst.geom.Point2I(9, 12))
        maskedImage = afwImage.MaskedImageF(bbox)
        maskedImage.set(10, 0x0, 1)

        dataBox = lsst.geom.Box2I(lsst.geom.Point2I(0, 0), lsst.geom.Extent2I(10, 10))
        dataImage = afwImage.MaskedImageF(maskedImage, dataBox)

        # these should be functionally equivalent
        bbox = lsst.geom.Box2I(lsst.geom.Point2I(0, 10),
                               lsst.geom.Point2I(9, 12))
        overscan = afwImage.MaskedImageF(maskedImage, bbox)
        overscan.set(2, 0x0, 1)
        for i in range(bbox.getDimensions()[0]):
            for j, off in enumerate([-0.5, 0.0, 0.5]):
                overscan.image[i, j, afwImage.LOCAL] = 2+i+off

        ipIsr.overscanCorrection(dataImage, overscan.getImage(), **kwargs)

        height = maskedImage.getHeight()
        width = maskedImage.getWidth()
        for j in range(height):
            for i in range(width):
                if j == 10:
                    self.assertEqual(maskedImage.image[i, j, afwImage.LOCAL], -0.5)
                elif j == 11:
                    self.assertEqual(maskedImage.image[i, j, afwImage.LOCAL], 0)
                elif j == 12:
                    self.assertEqual(maskedImage.image[i, j, afwImage.LOCAL], 0.5)
                else:
                    self.assertEqual(maskedImage.image[i, j, afwImage.LOCAL], 10 - 2 - i)

    def testPolyOverscanCorrection(self):
        for fitType in ("POLY", "CHEB", "LEG"):
            self.checkPolyOverscanCorrectionX(fitType=fitType)
            self.checkPolyOverscanCorrectionY(fitType=fitType)

    def testSplineOverscanCorrection(self):
        for fitType in ("NATURAL_SPLINE", "CUBIC_SPLINE", "AKIMA_SPLINE"):
            self.checkPolyOverscanCorrectionX(fitType=fitType, order=5)
            self.checkPolyOverscanCorrectionY(fitType=fitType, order=5)


class MemoryTester(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()
