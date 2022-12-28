""" Module of BHT1000 controller. """
import asyncio
import binascii
import datetime
import logging
from dataclasses import dataclass
from typing import Final, Union

import async_timeout

_LOGGER = logging.getLogger(__name__)

WEEKLY_MODE = "weekly"
MANUAL_MODE = "manual"
ID0 = 0x01
ID1 = 0x01

FLAG_LOCK = 0x04
FLAG_MANUAL_MODE = 0x08
FLAG_POWER = 0x10

STATE_ON = "on"
STATE_OFF = "off"


@dataclass
# pylint: disable=too-many-instance-attributes
class Payload:
    """
    Represents the base class of payload to send from or receive from the thermostat.

    Attributes:
        command: The command field of the payload.
        id0: The id0 field of the payload.
        id1: The id1 field of the payload.
        data0: The data0 field of the payload.
        data1: The data1 field of the payload.
        data2: The data2 field of the payload.
        data3: The data3 field of the payload.
        checksum: The checksum of the payload.
    """

    # pylint: disable=invalid-name
    command: Final[int]
    """The command field of the payload."""
    # pylint: disable=invalid-name
    id0: Final[int]
    """The id0 field of the payload."""
    # pylint: disable=invalid-name
    id1: Final[int]
    """The id1 field of the payload."""
    # pylint: disable=invalid-name
    data0: Final[int]
    """The data0 field of the payload."""
    # pylint: disable=invalid-name
    data1: Final[int]
    """The data1 field of the payload."""
    # pylint: disable=invalid-name
    data2: Final[int]
    """The data2 field of the payload."""
    # pylint: disable=invalid-name
    data3: Final[int]
    """The data3 field of the payload."""
    # pylint: disable=invalid-name
    checksum: Final[int]
    """The checksum of the payload."""


# pylint: disable=too-few-public-methods
class IncomingPayload(Payload):
    """Represents an incoming message payload."""

    def __init__(self, payload: bytes):
        """
        Initialize a new instance of `IncomingPayload` class.

        Args:
            payload: The received bytes from the device.
        """
        super().__init__(
            int(payload[:2], 16),
            int(payload[2:4], 16),
            int(payload[4:6], 16),
            int(payload[6:8], 16),
            int(payload[8:10], 16),
            int(payload[10:12], 16),
            int(payload[12:14], 16),
            int(payload[14:16], 16),
        )
        self.payload = payload


class StatusPayload(IncomingPayload):
    """Represents a status message incoming message payload."""

    def is_valid(self) -> bool:
        """Gets the value indicates whether the message is valid."""
        return self.command == 0x50 and self.id0 == 0x01 and self.id1 == 0x01

    def is_locked(self) -> bool:
        """Gets the value indicates whether the device is locked."""
        return (FLAG_LOCK & self.data0) == FLAG_LOCK

    def get_mode(self) -> str:
        """Gets the mode set on the device."""
        return (
            MANUAL_MODE
            if ((FLAG_MANUAL_MODE & self.data0) == FLAG_MANUAL_MODE)
            else WEEKLY_MODE
        )

    def is_on(self) -> bool:
        """Gets the value indicates whether the device is turned on."""
        return (FLAG_POWER & self.data0) == FLAG_POWER

    def get_calibration(self) -> int:
        """Gets the calibration value of the device."""
        return self.data1 - 256

    def get_setpoint(self) -> float:
        """Gets the current set point value of the device."""
        return float(self.data2) / 2.0

    def get_temperature(self) -> float:
        """Gets the current temperature returned by the device."""
        return float(self.data3) / 2.0


class OutgoingPayload(Payload):
    """Represents an outgoing message payload."""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        command: int,
        data0: int,
        data1: int,
        data2: int,
        data3: int,
    ):
        """
        Initialize a new instance of `OutgoingPayload` class.

        Args:

            command: The command field of the payload.
            data0: The data0 field of the payload.
            data1: The data1 field of the payload.
            data2: The data2 field of the payload.
            data3: The data3 field of the payload.
        """
        super().__init__(
            command,
            ID0,
            ID1,
            data0,
            data1,
            data2,
            data3,
            self.__calculate_checksum(command, ID0, ID1, data0, data1, data2, data3),
        )

    # pylint: disable=too-many-arguments
    @classmethod
    def __calculate_checksum(
        cls,
        command: int,
        id0: int,
        id1: int,
        data0: int,
        data1: int,
        data2: int,
        data3: int,
    ):
        """
        Calculates the checksum of the payload.

        Args:
            command: The command field of the payload.
            id0: The id0 field of the payload.
            id1: The id1 field of the payload.
            data0: The data0 field of the payload.
            data1: The data1 field of the payload.
            data2: The data2 field of the payload.
            data3: The data3 field of the payload.
        """
        return (command + id0 + id1 + data0 + data1 + data2 + data3) & 0xFF ^ 0xA5

    def get_bytes_array(self) -> bytearray:
        """Returns the outgoing message as a byte array."""
        result = bytearray()
        result.append(self.command)
        result.append(self.id0)
        result.append(self.id1)
        result.append(self.data0)
        result.append(self.data1)
        result.append(self.data2)
        result.append(self.data3)
        result.append(
            self.__calculate_checksum(
                self.command,
                self.id0,
                self.id1,
                self.data0,
                self.data1,
                self.data2,
                self.data3,
            )
        )
        return result


class ReadStatusCommandPayload(OutgoingPayload):
    """Represents a request to query the current state of the device."""

    def __init__(self):
        """Initialize a new instance of  `ReadStatusCommandPayload` class."""
        super().__init__(0xA0, 0x00, 0x00, 0x00, 0x00)


class SetAllDataCommandPayload(OutgoingPayload):
    """Represents a request to set all parameters of the device."""

    # pylint: disable=too-many-arguments
    def __init__(
        self, mode: str, power: str, lock: str, calibration: int, setpoint: float
    ):
        """
        Initialize a new instance of `SetAllDataCommandPayload` class.

        Args:
            mode: The requested mode of the device.
            power: The "on"/"off" value indicates whether the device should turned on.
            lock: The "on"/"off" value indicates whether the device is locked.
            calibration: The calibration value to set on device.
            setpoint: The set point of the device.
        """
        data0 = 0x00
        data3 = 0x00

        if lock == STATE_ON:
            data0 = data0 | FLAG_LOCK

        if mode == MANUAL_MODE:
            data0 = data0 | FLAG_MANUAL_MODE

        if power == STATE_ON:
            data0 = data0 | FLAG_POWER

        super().__init__(
            0xA1,
            data0,
            calibration + 256 if (calibration < 0) else calibration,
            int(setpoint * 2.0),
            data3,
        )


class UnLockCommandPayload(OutgoingPayload):
    """Represents a command to unlock the device."""

    def __init__(self):
        """Initialize a new instance of  `UnLockCommandPayload` class."""
        super().__init__(0xA4, 0, 1, 1, 1)


class LockCommandPayload(OutgoingPayload):
    """Represents a command to lock the device."""

    def __init__(self):
        """Initialize a new instance of  `LockCommandPayload` class."""
        super().__init__(0xA4, 1, 1, 1, 1)


class SetTimeCommandPayload(OutgoingPayload):
    """Represents a command to set the time on the device."""

    def __init__(self, time: datetime.datetime):
        """
        Initialize a new instance of  `SetTimeCommandPayload` class.

        Args
            time: The date time value to set on the device.
        """
        super().__init__(0xA8, time.second, time.minute, time.hour, time.weekday() + 1)


class BHT1000:
    """Responsible for the communication with the BHT1000 thermostat."""

    def __init__(self, host: str, port: int, hysteresis: float = 1.0):
        """
        Initialize a new instance of `BHT1000` class.

        Args:
            host: The host or the IP address of the thermostat.
            port: The port to communicate with the thermostat.
            hysteresis: The hysteresis set on the thermostat.
                        This value cannot be queried and need to
                        determine the actual heating state
                        (which is also can't be queried from the thermostat).
        """
        self._host: Final[str] = host
        self._port: Final[int] = port
        self._hysteresis: Final[float] = hysteresis
        self._current_temperature: Union[float, None] = None
        self._setpoint: Union[float, None] = None
        self._power: Union[str, None] = None
        self._mode: Union[str, None] = None
        self._locked: Union[str, None] = None
        self._calibration: Union[int, None] = None
        self._idle: Union[bool, None] = None

    async def check_host(self) -> bool:
        """
        Checks if the thermostat is reachable.

        Returns:
            The value indicates whether the thermostat is reachable.
        """
        try:
            writer = (
                await asyncio.wait_for(
                    asyncio.open_connection(self._host, self._port), 10
                )
            )[1]
            writer.close()
            await writer.wait_closed()
            return True
        # pylint: disable=bare-except
        except:
            return False

    async def read_status(self) -> bool:
        """
        Updates the current status of the thermostat.

        Returns:
            The value indicates whether the update was successful.
        """
        try:
            _LOGGER.debug("read status (%s:%s)", self._host, self._port)
            await self.__send_command(ReadStatusCommandPayload())
            return True
        # pylint: disable=broad-except
        except Exception as error:
            _LOGGER.error(error)
            return False

    async def turn_on(self) -> bool:
        """
        Turns on the thermostat.

        Returns:
            The value indicates whether the turning on was successful.
        """
        if self.__is_data_valid():
            _LOGGER.debug("turn on (%s:%s)", self._host, self._port)
            return await self.__send_command(
                SetAllDataCommandPayload(
                    self._mode,
                    STATE_ON,
                    self._locked,
                    self._calibration,
                    self._setpoint,
                )
            )
        return False

    async def turn_off(self) -> bool:
        """
        Turns off the thermostat.

        Returns:
            The value indicates whether the turning off was successful.
        """
        if self.__is_data_valid():
            _LOGGER.debug("turn off (%s:%s)", self._host, self._port)
            return await self.__send_command(
                SetAllDataCommandPayload(
                    self._mode,
                    STATE_OFF,
                    self._locked,
                    self._calibration,
                    self._setpoint,
                )
            )
        return False

    async def set_temperature(self, temperature: float) -> bool:
        """
        Sets the set point on the thermostat

        Returns:
            The value indicates whether the setting was successful.
        """
        if self.__is_data_valid():
            _LOGGER.debug(
                "set temperature to %f (%s:%s)", temperature, self._host, self._port
            )
            return await self.__send_command(
                SetAllDataCommandPayload(
                    self._mode,
                    self._power,
                    self._locked,
                    self._calibration,
                    temperature,
                )
            )
        return False

    async def lock(self) -> bool:
        """
        Locks the thermostat.

        Returns:
            The value indicates whether the locking was successful.
        """
        if self.__is_data_valid():
            _LOGGER.debug("lock (%s:%s)", self._host, self._port)
            return await self.__send_command(LockCommandPayload())
        return False

    async def unlock(self) -> bool:
        """
        Unlocks the thermostat.

        Returns:
            The value indicates whether the unlocking was successful.
        """
        if self.__is_data_valid():
            _LOGGER.debug("unlock (%s:%s)", self._host, self._port)
            return await self.__send_command(UnLockCommandPayload())
        return False

    async def set_manual_mode(self) -> bool:
        """
        Sets the thermostat into manual mode.

        Returns:
            The value indicates whether the setting was successful.
        """
        if self.__is_data_valid():
            _LOGGER.debug("set manual mode (%s:%s)", self._host, self._port)
            return await self.__send_command(
                SetAllDataCommandPayload(
                    MANUAL_MODE,
                    self._power,
                    self._locked,
                    self._calibration,
                    self._setpoint,
                )
            )
        return False

    async def set_weekly_mode(self) -> bool:
        """
        Sets the thermostat into weekly mode.

        Returns:
            The value indicates whether the setting was successful.
        """
        if self.__is_data_valid():
            _LOGGER.debug("set weekly mode (%s:%s)", self._host, self._port)
            return await self.__send_command(
                SetAllDataCommandPayload(
                    WEEKLY_MODE,
                    self._power,
                    self._locked,
                    self._calibration,
                    self._setpoint,
                )
            )
        return False

    async def set_time(self, time: datetime.datetime) -> bool:
        """
        Sets the time on the thermostat.

        Args:
            time: The date time value to set.

        Returns:
            The value indicates whether the setting was successful.
        """
        if self.__is_data_valid():
            _LOGGER.debug("set time (%s:%s)", self._host, self._port)
            return await self.__send_command(SetTimeCommandPayload(time))
        return False

    def __is_data_valid(self) -> bool:
        """
        Gets the value indicates all state data stored in memory is valid.
        """
        result = (
            (self._mode is not None)
            and (self._power is not None)
            and (self._locked is not None)
            and (self._calibration is not None)
            and (self._setpoint is not None)
        )
        return result

    @property
    def current_temperature(self) -> Union[float, None]:
        """Gets the current temperature."""
        return self._current_temperature

    @property
    def mode(self) -> Union[str, None]:
        """Gets the mode of the thermostat."""
        return self._mode

    @property
    def power(self) -> Union[str, None]:
        """Gets the power state of the thermostat ("on"/"off")."""
        return self._power

    @property
    def setpoint(self) -> Union[float, None]:
        """Gets the current set point temperature."""
        return self._setpoint

    @property
    def idle(self) -> Union[bool, None]:
        """
        Gets the value indicates whether the thermostat is currently not heating.

        *NOTE*:
            This is a calculated value not queried from the thermostat (it can't be queried)!
        """
        return self._idle

    def locked(self) -> Union[bool, None]:
        """Gets the value indicates whether the child lock is active."""
        return self._locked

    async def __send_command(self, command: OutgoingPayload) -> bool:
        """
        Sends the specified command message to the thermostat.

        Returns:
            The value indicates whether the sending was successful.
        """
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port), 10
            )

            async with async_timeout.timeout(3):
                try:
                    bytes_to_send = command.get_bytes_array()
                    _LOGGER.debug(
                        "bytes to send (%s:%s): %s", self._host, self._port, bytes_to_send
                    )
                    writer.write(bytes_to_send)
                    received_bytes = binascii.hexlify(await reader.read(64))
                    _LOGGER.debug(
                        "bytes received (%s:%s): %s", self._host, self._port, received_bytes
                    )
                except asyncio.TimeoutError:
                    return False
                finally:
                    writer.close()
                    await writer.wait_closed()

            if len(received_bytes) < 16:
                return False

            response = StatusPayload(received_bytes)
            if not response.is_valid():
                return False

            was_idle = self._idle is True or self._idle is None
            self._current_temperature = response.get_temperature()
            self._setpoint = response.get_setpoint()
            self._calibration = response.get_calibration()
            self._power = STATE_ON if response.is_on() else STATE_OFF
            self._mode = response.get_mode()
            self._locked = STATE_ON if response.is_locked() else STATE_OFF

            if self._power is STATE_ON:
                if (
                    was_idle
                    and self._current_temperature
                    < self._setpoint - self._hysteresis / 2.0
                ):
                    self._idle = False
                else:
                    if (
                        was_idle is False
                        and self._current_temperature
                        > self._setpoint + self._hysteresis / 2.0
                    ):
                        self._idle = True
                    else:
                        self._idle = was_idle
            else:
                self._idle = True

            return True
        # pylint: disable=broad-except
        except Exception:
            return False
