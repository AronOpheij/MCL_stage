from ctypes import *
import os, sys
import logging

class MCLMicroDrive:
    def __init__(self, dllpath=None, unit='um'):
        """
        Note: all units are in mm

        :param dllpath: path to the directory containing the dll (None for directory of this file) (default: None)
        :type dllpath: string or None
        :param serial: if serial is supplied it will connect automatically
        :type serial: b++ytestring or False (default: False)
        """
        self.logger = logging.getLogger(__name__)

        _unit_dict = {'m': 0.001, 'mm':1.0, 'um':1000.0}
        self.unit = unit
        if self.unit not in _unit_dict:
            self.logger.warning('Unit "" unknown. falling back to um')
            self.unit = 'um'
        self._unit_conversion = _unit_dict[self.unit]

        self.Xaxis = 1
        self.Yaxis = 2
        self.Zaxis = 3

        # self.Xlimits = (-20, 20)
        # self.Ylimits = (-20, 20)
        # self.Zlimits = (-20, 20)

        if dllpath is None:
            dllpath = os.path.dirname(os.path.abspath(__file__))

        os.add_dll_directory(dllpath)
        self.mdll = cdll.LoadLibrary("MicroDrive.dll")

        self.handle = self.mdll.MCL_InitHandle()
        if self.handle == 0:
            self.logger.error("Handle did not initialize properly. Exiting")
            return


        # global X,Y,microstepsize
        # print("MicroDrive python test program\n")


        # read different properties of the MicroDrive
        # first declare variables of type c_double
        # all variables must be turned into their ctype other than int and string
        self.encoderResolution = c_double()
        self.stepSize = c_double()
        self.maxVel = c_double()
        self.minVel = c_double()
        self.maxVelocityTwoAxis=c_double()
        self.maxVelocityThreeAxis=c_double()

        # next get pointers to each variable since we must pass by reference
        pER = pointer(self.encoderResolution)
        pSS = pointer(self.stepSize)
        pMxV = pointer(self.maxVel)
        pMnV = pointer(self.minVel)


        # finally read the info and then print(it out
        err = self.mdll.MCL_MicroDriveInformation(pER, pSS, pMxV,byref(self.maxVelocityTwoAxis),byref(self.maxVelocityThreeAxis), pMnV, self.handle)
        if err != 0:
            self.logger.error("MicroDrive could not correctly get its information.  Error Code: "+str(err)+" Exiting")
            self.disconnect()
            return
        else: # must use .value to convert from ctype to python type
            self.logger.info("MicroDrive information")
            self.logger.info("Encoder Resolution:", self.encoderResolution.value)
            self.logger.info("Step Size:", self.stepSize.value)
            self.logger.info("Max Velocity:", self.maxVel.value)
            self.logger.info("Min Velocity:", self.minVel.value)
            self.logger.info("maxVelocityTwoAxis:", self.maxVelocityTwoAxis.value)
            self.logger.info("maxVelocityThreeAxis:",  self.maxVelocityThreeAxis.value)

        err = self.readPosition()
        if err:
            self.logger.error("Error: MicroDrive did not read position properly. Error Code: Exiting")
            return
        else:
            self.logger.info("Current x position: "+str(self.xPos))
            self.logger.info("Current y postiion: "+str(self.yPos))

        self.microstepsize = 95.25e-6 * self._unit_conversion # in mm

        self._moving_tolerance = 80.0e-6 * self._unit_conversion # in mm  (keep it larger than 50e-6)
        self._max_iterations = 6

    def readPosition(self):
        pos1 = c_double()
        pos2 = c_double()
        pos3 = c_double()
        p1 = pointer(pos1)
        p2 = pointer(pos2)
        p3 = pointer(pos3)
        err = self.mdll.MCL_MicroDriveReadEncoders(p1, p2, p3, self.handle)
        if err:
            self.logger.warning("Error while attempting to read MicroDrive position: "+str(err))
            self.disconnect()
        else:
            self.pos = [pos1.value * self._unit_conversion, pos2.value * self._unit_conversion, pos3.value * self._unit_conversion]
            self.xPos = self.pos[self.Xaxis-1]
            self.yPos = self.pos[self.Yaxis-1]
            self.zPos = self.pos[self.Zaxis-1]
        return err

    def getPos(self):
        self.readPosition()
        return self.pos

    def disconnect(self):
        self.logger.info("Disconnecting MCL stage")
        self.mdll.MCL_ReleaseHandle(self.handle)

    def _stepA(self, axis, n):
        if n == 1 or n == -1:
            err = self.mdll.MCL_MDSingleStep(c_int(axis), c_int(n), self.handle)
        else:
            err = self.mdll.MCL_MDMoveM(c_int(axis), self.maxVel, c_int(n), self.handle)
        if err:
            self.logger.warning('Error occurred while attempting microstep: '+str(err))
        err = self.mdll.MCL_MicroDriveWait(self.handle)
        self.readPosition()

    def stepX(self, nx):
        return self._stepA(self.Xaxis, nx)

    def stepY(self, ny):
        return self._stepA(self.Xaxis, ny)

    def stepZ(self, nz):
        return self._stepsA(self.Zaxis, nz)

    def step(self, nx, ny, nz=0):
        err = self.mdll.MCL_MDMoveThreeAxesM(c_int(self.Xaxis), self.maxVel, c_int(nx),
                                             c_int(self.Yaxis), self.maxVel, c_int(ny),
                                             c_int(self.Zaxis), self.maxVel, c_int(nz),
                                             self.handle)
        if err:
            self.logger.warning('Error occurred while attempting microstep: '+str(err))
        err = self.mdll.MCL_MicroDriveWait(self.handle)
        self.readPosition()

    # def rel_micro(self, axis, steps):
    #     err = self.mdll.MCL_MDMoveM(c_int(axis), self.maxVel, c_int(steps), self.handle)
    #     if err:
    #         self.logger.warning('Error occurred while attempting relative move: ' + str(err))
    #     err = self.mdll.MCL_MicroDriveWait(self.handle)
    #     self.readPosition()

    def _relA(self, axis, d):
        self._absA(axis, self.pos[axis-1] + d)

    def relX(self, dx):
        return self._relA(self.Xaxis, dx)

    def relY(self, dy):
        return self._relA(self.Yaxis, dy)

    def relZ(self, dz):
        return self._relA(self.Zaxis, dz)

    def rel(self, dx, dy, dz=0):
        self.abs(self.xPos+dx, self.yPos+dy, self.zPos+dz)

    def _absA(self, axis, a):
        c=0
        while abs(self.pos[axis-1] - a) > self._moving_tolerance:
            rel_microsteps = round((a - self.pos[axis - 1]) / self.microstepsize)
            self._stepA(axis, int(rel_microsteps))
            c += 1
            if c>=self._max_iterations:
                break

    def absX(self, x):
        self._absA(self.Xaxis, x)

    def absY(self, y):
        self._absA(self.Yaxis, y)

    def absZ(self, z):
        self._absA(self.Zaxis, z)

    def abs(self, x, y, z=0):
        c=0

        while abs(self.xPos - x) > self._moving_tolerance or \
                abs(self.yPos - y) > self._moving_tolerance or \
                abs(self.zPos - z) > self._moving_tolerance:
            rel_microsteps_x = round((x - self.xPos) / self.microstepsize)
            rel_microsteps_y = round((y - self.yPos) / self.microstepsize)
            rel_microsteps_z = round((z - self.zPos) / self.microstepsize)
            self.step(int(rel_microsteps_x), int(rel_microsteps_y), int(rel_microsteps_z))
            c += 1
            if c>=self._max_iterations:
                break


class DummyMCLMicroDrive:
    def __init__(self, *args, **kwargs):
        self.xPos = 0
        self.yPos = 0
        self.zPos = 0
        self.microstepsize = 95.25e-6  # in mm

    def _stepA(self, axis, n):
        if axis == 1:
            self.xPos += n * self.microstepsize
        elif axis == 2:
            self.yPos += n * self.microstepsize

    def stepX(self, nx):
        self.xPos += nx * self.microstepsize

    def stepY(self, ny):
        self.yPos += ny * self.microstepsize

    def stepZ(self, nz):
        self.zPos += nz * self.microstepsize

    def step(self, nx, ny, nz=0):
        self.xPos += nx * self.microstepsize
        self.yPos += ny * self.microstepsize
        self.zPos += nz * self.microstepsize

    def _relA(self, axis, d):
        if axis == 1:
            self.xPos += d
        elif axis == 2:
            self.yPos += d

    def relX(self, dx):
        self.xPos += dx

    def relY(self, dy):
        self.yPos += dy

    def relZ(self, dz):
        self.zPos += dz

    def rel(self, dx, dy, dz=0):
        self.xPos += dx
        self.yPos += dy
        self.zPos += dz

    def absX(self, x):
        self.xPos = x

    def absY(self, y):
        self.yPos = y

    def absZ(self, z):
        self.zPos = z

    def abs(self, x, y, z=0):
        self.xPos = x
        self.yPos = y
        self.zPos = z

    def disconnext(self):
        pass

if __name__ == '__main__':

    dll_dir = r'E:\Action-Potential\Equipments\MCL_Python_Matlab'

    stage = MCLMicroDrive(dll_dir, units='mm')  # To look for the dll in a specific directory
    #stage = MCLMicroDrive()         # To look for the dll in the directory where this file lives
    #stage = DummyMCLMicroDrive()    # To test with Dummy version

    # # Some test code for the MCLMicroDrive class:
    # print(stage.xPos, stage.yPos)
    # stage.relX(2)
    # print(stage.xPos, stage.yPos)
    # stage.abs(-1,3)
    # print(stage.xPos, stage.yPos)
    # stage.step(5, 5)
    # print(stage.xPos, stage.yPos)
