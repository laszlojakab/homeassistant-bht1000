import socket
import binascii
import logging

_LOGGER = logging.getLogger(__name__)

WEEKLY_MODE = "weekly"
MANUAL_MODE = "manual"
ID0 = 0x01
ID1 = 0x01

FLAG_LOCK = 0x04
FLAG_MANUAL_MODE = 0x08
FLAG_POWER = 0x10

STATE_ON = 'on'
STATE_OFF = 'off'

class Payload:
    def __init__(self, command, id0, id1, data0, data1, data2, data3, checksum):
        self._command = command
        self._id0 = id0
        self._id1 = id1
        self._data0 = data0
        self._data1 = data1
        self._data2 = data2
        self._data3 = data3
        self._checksum = checksum
        return

    def get_command(self):
        return self._command

    def get_id0(self):
        return self._id0

    def get_id1(self):
        return self._id1

    def get_data0(self):
        return self._data0

    def get_data1(self):
        return self._data1

    def get_data2(self):
        return self._data2

    def get_data3(self):
        return self._data3

    def get_checksum(self):
        return self._checksum

class IncomingPayload(Payload):
    def __init__(self, payload):
        super().__init__(int(payload[:2], 16), int(payload[2:4], 16), int(payload[4:6], 16), int(payload[6:8], 16), int(payload[8:10], 16), int(
            payload[10:12], 16), int(payload[12:14], 16), int(payload[14:16], 16))
        self.payload = payload
        return

class StatusPayload(IncomingPayload):
    def is_valid(self):
        return self.get_command() == 0x50 and self.get_id0() == 0x01 and self.get_id1() == 0x01

    def is_locked(self):
        return (FLAG_LOCK & self.get_data0()) == FLAG_LOCK

    def get_mode(self):
        return MANUAL_MODE if ((FLAG_MANUAL_MODE & self.get_data0()) == FLAG_MANUAL_MODE) else WEEKLY_MODE

    def is_on(self):
        return (FLAG_POWER & self.get_data0()) == FLAG_POWER

    def get_calibration(self):
        return self.get_data1() - 256

    def get_setpoint(self):
        return float(self.get_data2()) / 2.0

    def get_temperature(self):
        return float(self.get_data3()) / 2.0

class OutgoingPayload(Payload):
    def __init__(self, command, data0, data1, data2, data3):
        super().__init__(command, ID0, ID1, data0, data1, data2, data3,
                         self.__calculate_checksum(command, ID0, ID1, data0, data1, data2, data3))
        return

    def __calculate_checksum(self, command, id0, id1, data0, data1, data2, data3):
        return ((command + id0 + id1 + data0 + data1 + data2 + data3) & 0xFF ^ 0xA5)

    def getBytesHex(self):
        result = bytearray()
        result.append(self.get_command())
        result.append(self.get_id0())
        result.append(self.get_id1())
        result.append(self.get_data0())
        result.append(self.get_data1())
        result.append(self.get_data2())
        result.append(self.get_data3())
        result.append(self.__calculate_checksum(self.get_command(), self.get_id0(), self.get_id1(), self.get_data0(), self.get_data1(), self.get_data2(), self.get_data3()))
        return result

class ReadStatusCommandPayload(OutgoingPayload):
    def __init__(self):
        super().__init__(0XA0, 0x00, 0x00, 0x00, 0x00)
        return

class SetAllDataCommandPayload(OutgoingPayload):
    def __init__(self, mode, power, lock, calibration, setpoint):
        data0 = 0x00
        data3 = 0x00

        if (lock == STATE_ON):
            data0 = data0 | FLAG_LOCK

        if (mode == MANUAL_MODE):
            data0 = data0 | FLAG_MANUAL_MODE

        if (power == STATE_ON):
            data0 = data0 | FLAG_POWER

        super().__init__(0xA1, data0, calibration + 256 if (calibration < 0) else calibration, int(setpoint * 2.0), data3)
        return 

class UnLockCommandPayload(OutgoingPayload):
    def __init__(self):
        super().__init__(0xA4, 0, 1, 1, 1)
        return

class LockCommandPayload(OutgoingPayload):
    def __init__(self):
        super().__init__(0xA4, 1, 1, 1, 1)
        return

class SetTimeCommandPayload(OutgoingPayload):
    def __init__(self, time):
        super().__init__(0xA8, time.second, time.minute, time.hour, time.weekday() + 1)
        return 

class BHT1000():
    def __init__(self, host, port, hysteresis = 1.0):
        self._host = host
        self._port = port
        self._hysteresis = hysteresis
        self._current_temperature = None
        self._setpoint = None
        self._power = None
        self._mode = None
        self._locked = None
        self._calibration = None
        self._hysteresis = hysteresis
        self._idle = None
        return
    
    def check_host(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(10)
                sock.connect((self._host, self._port))
            return True
        except:
            return False

    def read_status(self):
        try:
            _LOGGER.debug("read status (%s:%s)", self._host, self._port)
            self.__sendCommand(ReadStatusCommandPayload())
        except:
            pass
        
    def turn_on(self):
        if (self.__is_data_valid()):
            _LOGGER.debug("turn on (%s:%s)", self._host, self._port)
            self.__sendCommand(SetAllDataCommandPayload(
                self._mode, STATE_ON, self._locked, self._calibration, self._setpoint))

    def turn_off(self):
        if (self.__is_data_valid()):
            _LOGGER.debug("turn off (%s:%s)", self._host, self._port)
            self.__sendCommand(SetAllDataCommandPayload(
                self._mode, STATE_OFF, self._locked, self._calibration, self._setpoint))

    def set_temperature(self, temperature):
        if (self.__is_data_valid()):
            _LOGGER.debug("set temperature to %f (%s:%s)",
                          temperature, self._host, self._port)
            self.__sendCommand(SetAllDataCommandPayload(
                self._mode, self._power, self._locked, self._calibration, temperature))

    def lock(self):
        if (self.__is_data_valid()):
            _LOGGER.debug("lock (%s:%s)", self._host, self._port)
            self.__sendCommand(LockCommandPayload())

    def unlock(self):
        if (self.__is_data_valid()):
            _LOGGER.debug("unlock (%s:%s)", self._host, self._port)
            self.__sendCommand(UnLockCommandPayload())

    def set_manual_mode(self):
        if (self.__is_data_valid()):
            _LOGGER.debug("set manual mode (%s:%s)", self._host, self._port)
            self.__sendCommand(SetAllDataCommandPayload(
                MANUAL_MODE, self._power, self._locked, self._calibration, self._setpoint))

    def set_weekly_mode(self):
        if (self.__is_data_valid()):
            _LOGGER.debug("set weekly mode (%s:%s)", self._host, self._port)
            self.__sendCommand(SetAllDataCommandPayload(
                WEEKLY_MODE, self._power, self._locked, self._calibration, self._setpoint))

    def set_time(self, time):
        if (self.__is_data_valid()):
            _LOGGER.debug("set time (%s:%s)", self._host, self._port)
            self.__sendCommand(SetTimeCommandPayload(time))

    def __is_data_valid(self):
        result = (self._mode is not None) and (self._power is not None) and (
            self._locked is not None) and (self._calibration is not None) and (self._setpoint is not None)
        return result 

    @property
    def current_temperature(self):
        return self._current_temperature

    @property
    def mode(self):
        return self._mode

    @property
    def power(self):
        return self._power

    @property
    def setpoint(self):
        return self._setpoint

    @property
    def idle(self):
        return self._idle

    def __sendCommand(self, command):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(10)
                sock.connect((self._host, self._port))
                bytesToSend = command.getBytesHex()
                _LOGGER.debug("bytes to send (%s:%s): %s", self._host, self._port, bytesToSend)
                sock.send(bytesToSend)
                bytesReceived = binascii.hexlify(sock.recv(64))                
                _LOGGER.debug("bytes received (%s:%s): %s", self._host, self._port, bytesReceived)

            if (len(bytesReceived) > 3):
                response = StatusPayload(bytesReceived)
                if (response.is_valid()):
                    wasIdle = self._idle is True or self._idle is None
                    self._current_temperature = response.get_temperature()
                    self._setpoint = response.get_setpoint()
                    self._calibration = response.get_calibration()
                    self._power = STATE_ON if response.is_on() else STATE_OFF
                    self._mode = response.get_mode()
                    self._locked = STATE_ON if response.is_locked() else STATE_OFF

                    if (self._power is STATE_ON):                    
                        if (wasIdle and self._current_temperature < self._setpoint - self._hysteresis / 2.0):
                            self._idle = False
                        else:
                            if (wasIdle is False and self._current_temperature > self._setpoint + self._hysteresis / 2.0):
                                self._idle = True
                            else:
                                self._idle = wasIdle
                    else:
                        self._idle = True
                    return
        except:
            pass
        self._power = STATE_OFF
 