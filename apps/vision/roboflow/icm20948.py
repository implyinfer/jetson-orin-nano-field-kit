#!/usr/bin/env python3
"""
ICM-20948 9-DOF IMU Driver for Python

This module provides a pure Python implementation for reading data from the
ICM-20948 9-axis IMU sensor (accelerometer, gyroscope, magnetometer) via I2C.

Based on the Waveshare ICM20948 C driver implementation.
"""

import math
import time
import threading
from dataclasses import dataclass
from typing import Optional, Tuple

try:
    import smbus2
    SMBUS_AVAILABLE = True
except ImportError:
    SMBUS_AVAILABLE = False


# ICM-20948 I2C Addresses
I2C_ADD_ICM20948 = 0x68
I2C_ADD_ICM20948_AK09916 = 0x0C
I2C_ADD_ICM20948_AK09916_READ = 0x80
I2C_ADD_ICM20948_AK09916_WRITE = 0x00

# Register Bank Selection
REG_ADD_REG_BANK_SEL = 0x7F
REG_VAL_REG_BANK_0 = 0x00
REG_VAL_REG_BANK_1 = 0x10
REG_VAL_REG_BANK_2 = 0x20
REG_VAL_REG_BANK_3 = 0x30

# User Bank 0 Registers
REG_ADD_WIA = 0x00
REG_VAL_WIA = 0xEA
REG_ADD_USER_CTRL = 0x03
REG_VAL_BIT_I2C_MST_EN = 0x20
REG_ADD_PWR_MIGMT_1 = 0x06
REG_VAL_ALL_RGE_RESET = 0x80
REG_VAL_RUN_MODE = 0x01

REG_ADD_ACCEL_XOUT_H = 0x2D
REG_ADD_GYRO_XOUT_H = 0x33
REG_ADD_EXT_SENS_DATA_00 = 0x3B

# User Bank 2 Registers
REG_ADD_GYRO_SMPLRT_DIV = 0x00
REG_ADD_GYRO_CONFIG_1 = 0x01
REG_VAL_BIT_GYRO_DLPCFG_6 = 0x30
REG_VAL_BIT_GYRO_FS_1000DPS = 0x04
REG_VAL_BIT_GYRO_DLPF = 0x01
REG_ADD_ACCEL_SMPLRT_DIV_2 = 0x11
REG_ADD_ACCEL_CONFIG = 0x14
REG_VAL_BIT_ACCEL_DLPCFG_6 = 0x30
REG_VAL_BIT_ACCEL_FS_2g = 0x00
REG_VAL_BIT_ACCEL_DLPF = 0x01

# User Bank 3 Registers
REG_ADD_I2C_SLV0_ADDR = 0x03
REG_ADD_I2C_SLV0_REG = 0x04
REG_ADD_I2C_SLV0_CTRL = 0x05
REG_VAL_BIT_SLV0_EN = 0x80
REG_VAL_BIT_MASK_LEN = 0x07
REG_ADD_I2C_SLV1_ADDR = 0x07
REG_ADD_I2C_SLV1_REG = 0x08
REG_ADD_I2C_SLV1_CTRL = 0x09
REG_ADD_I2C_SLV1_DO = 0x0A

# Magnetometer Registers
REG_ADD_MAG_WIA1 = 0x00
REG_VAL_MAG_WIA1 = 0x48
REG_ADD_MAG_WIA2 = 0x01
REG_VAL_MAG_WIA2 = 0x09
REG_ADD_MAG_ST2 = 0x10
REG_ADD_MAG_DATA = 0x11
REG_ADD_MAG_CNTL2 = 0x31
REG_VAL_MAG_MODE_20HZ = 0x04

# Sensitivity Scale Factors
GYRO_SSF_AT_FS_1000DPS = 32.8
ACCEL_SSF_AT_FS_2g = 16384
MAG_SSF_AT_FS_4900uT = 0.15

MAG_DATA_LEN = 6


@dataclass
class IMUAngles:
    """Roll, Pitch, Yaw angles in degrees"""
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0


@dataclass
class IMUSensorData:
    """3-axis sensor data"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class ICM20948:
    """
    ICM-20948 9-DOF IMU Driver

    Provides access to accelerometer, gyroscope, and magnetometer data
    with AHRS (Attitude and Heading Reference System) orientation calculation.
    """

    def __init__(self, i2c_bus: int = 7):
        """
        Initialize the ICM-20948 sensor.

        Args:
            i2c_bus: I2C bus number (default: 7 for Jetson)
        """
        if not SMBUS_AVAILABLE:
            raise ImportError("smbus2 is required. Install with: pip install smbus2")

        self.i2c_bus = i2c_bus
        self.bus = None
        self.initialized = False

        # Gyro offset calibration
        self.gyro_offset = [0, 0, 0]

        # AHRS quaternion state
        self.q0, self.q1, self.q2, self.q3 = 1.0, 0.0, 0.0, 0.0

        # AHRS filter gains
        self.Kp = 4.50
        self.Ki = 1.0

        # Averaging buffers for noise reduction
        self._gyro_avg = [[0]*8, [0]*8, [0]*8]
        self._gyro_idx = [0, 0, 0]
        self._accel_avg = [[0]*8, [0]*8, [0]*8]
        self._accel_idx = [0, 0, 0]
        self._mag_avg = [[0]*8, [0]*8, [0]*8]
        self._mag_idx = [0, 0, 0]

        # Thread lock for concurrent access
        self._lock = threading.Lock()

    def _read_byte(self, reg: int) -> int:
        """Read a single byte from a register"""
        return self.bus.read_byte_data(I2C_ADD_ICM20948, reg)

    def _write_byte(self, reg: int, value: int) -> None:
        """Write a single byte to a register"""
        self.bus.write_byte_data(I2C_ADD_ICM20948, reg, value)

    def _select_bank(self, bank: int) -> None:
        """Select register bank (0-3)"""
        self._write_byte(REG_ADD_REG_BANK_SEL, bank << 4)

    def _read_secondary(self, i2c_addr: int, reg_addr: int, length: int) -> bytes:
        """Read from secondary I2C device (magnetometer)"""
        self._select_bank(3)
        self._write_byte(REG_ADD_I2C_SLV0_ADDR, i2c_addr)
        self._write_byte(REG_ADD_I2C_SLV0_REG, reg_addr)
        self._write_byte(REG_ADD_I2C_SLV0_CTRL, REG_VAL_BIT_SLV0_EN | length)

        self._select_bank(0)
        temp = self._read_byte(REG_ADD_USER_CTRL)
        temp |= REG_VAL_BIT_I2C_MST_EN
        self._write_byte(REG_ADD_USER_CTRL, temp)
        time.sleep(0.005)
        temp &= ~REG_VAL_BIT_I2C_MST_EN
        self._write_byte(REG_ADD_USER_CTRL, temp)

        data = []
        for i in range(length):
            data.append(self._read_byte(REG_ADD_EXT_SENS_DATA_00 + i))

        self._select_bank(3)
        temp = self._read_byte(REG_ADD_I2C_SLV0_CTRL)
        temp &= ~(REG_VAL_BIT_I2C_MST_EN & REG_VAL_BIT_MASK_LEN)
        self._write_byte(REG_ADD_I2C_SLV0_CTRL, temp)
        self._select_bank(0)

        return bytes(data)

    def _write_secondary(self, i2c_addr: int, reg_addr: int, data: int) -> None:
        """Write to secondary I2C device (magnetometer)"""
        self._select_bank(3)
        self._write_byte(REG_ADD_I2C_SLV1_ADDR, i2c_addr)
        self._write_byte(REG_ADD_I2C_SLV1_REG, reg_addr)
        self._write_byte(REG_ADD_I2C_SLV1_DO, data)
        self._write_byte(REG_ADD_I2C_SLV1_CTRL, REG_VAL_BIT_SLV0_EN | 1)

        self._select_bank(0)
        temp = self._read_byte(REG_ADD_USER_CTRL)
        temp |= REG_VAL_BIT_I2C_MST_EN
        self._write_byte(REG_ADD_USER_CTRL, temp)
        time.sleep(0.005)
        temp &= ~REG_VAL_BIT_I2C_MST_EN
        self._write_byte(REG_ADD_USER_CTRL, temp)

        self._select_bank(3)
        temp = self._read_byte(REG_ADD_I2C_SLV0_CTRL)
        temp &= ~(REG_VAL_BIT_I2C_MST_EN & REG_VAL_BIT_MASK_LEN)
        self._write_byte(REG_ADD_I2C_SLV0_CTRL, temp)
        self._select_bank(0)

    def _calc_avg(self, idx_list: list, avg_buffer: list, axis: int, in_val: int) -> int:
        """Calculate moving average for noise reduction"""
        avg_buffer[axis][idx_list[axis]] = in_val
        idx_list[axis] = (idx_list[axis] + 1) & 0x07
        return sum(avg_buffer[axis]) >> 3

    def _check_device(self) -> bool:
        """Check if ICM-20948 is present"""
        try:
            wia = self._read_byte(REG_ADD_WIA)
            return wia == REG_VAL_WIA
        except Exception:
            return False

    def _check_magnetometer(self) -> bool:
        """Check if magnetometer is present"""
        try:
            data = self._read_secondary(
                I2C_ADD_ICM20948_AK09916 | I2C_ADD_ICM20948_AK09916_READ,
                REG_ADD_MAG_WIA1, 2
            )
            return data[0] == REG_VAL_MAG_WIA1 and data[1] == REG_VAL_MAG_WIA2
        except Exception:
            return False

    def _calibrate_gyro(self) -> None:
        """Calibrate gyroscope offset"""
        sums = [0, 0, 0]
        for _ in range(32):
            gx, gy, gz = self._read_gyro_raw()
            sums[0] += gx
            sums[1] += gy
            sums[2] += gz
            time.sleep(0.01)

        self.gyro_offset = [s >> 5 for s in sums]

    def initialize(self) -> bool:
        """
        Initialize the IMU sensor.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self.bus = smbus2.SMBus(self.i2c_bus)

            if not self._check_device():
                print(f"ICM-20948 not found on I2C bus {self.i2c_bus}")
                return False

            # Reset device
            self._select_bank(0)
            self._write_byte(REG_ADD_PWR_MIGMT_1, REG_VAL_ALL_RGE_RESET)
            time.sleep(0.01)
            self._write_byte(REG_ADD_PWR_MIGMT_1, REG_VAL_RUN_MODE)

            # Configure gyro and accelerometer
            self._select_bank(2)
            self._write_byte(REG_ADD_GYRO_SMPLRT_DIV, 0x07)
            self._write_byte(REG_ADD_GYRO_CONFIG_1,
                           REG_VAL_BIT_GYRO_DLPCFG_6 | REG_VAL_BIT_GYRO_FS_1000DPS | REG_VAL_BIT_GYRO_DLPF)
            self._write_byte(REG_ADD_ACCEL_SMPLRT_DIV_2, 0x07)
            self._write_byte(REG_ADD_ACCEL_CONFIG,
                           REG_VAL_BIT_ACCEL_DLPCFG_6 | REG_VAL_BIT_ACCEL_FS_2g | REG_VAL_BIT_ACCEL_DLPF)

            self._select_bank(0)
            time.sleep(0.1)

            # Calibrate gyro offset
            self._calibrate_gyro()

            # Initialize magnetometer
            if self._check_magnetometer():
                self._write_secondary(
                    I2C_ADD_ICM20948_AK09916 | I2C_ADD_ICM20948_AK09916_WRITE,
                    REG_ADD_MAG_CNTL2, REG_VAL_MAG_MODE_20HZ
                )

            self.initialized = True
            return True

        except Exception as e:
            print(f"Failed to initialize ICM-20948: {e}")
            return False

    def _read_gyro_raw(self) -> Tuple[int, int, int]:
        """Read raw gyroscope values"""
        self._select_bank(0)
        data = self.bus.read_i2c_block_data(I2C_ADD_ICM20948, REG_ADD_GYRO_XOUT_H, 6)

        gx = (data[0] << 8) | data[1]
        gy = (data[2] << 8) | data[3]
        gz = (data[4] << 8) | data[5]

        # Convert to signed
        if gx > 32767: gx -= 65536
        if gy > 32767: gy -= 65536
        if gz > 32767: gz -= 65536

        return gx, gy, gz

    def _read_accel_raw(self) -> Tuple[int, int, int]:
        """Read raw accelerometer values"""
        self._select_bank(0)
        data = self.bus.read_i2c_block_data(I2C_ADD_ICM20948, REG_ADD_ACCEL_XOUT_H, 6)

        ax = (data[0] << 8) | data[1]
        ay = (data[2] << 8) | data[3]
        az = (data[4] << 8) | data[5]

        # Convert to signed
        if ax > 32767: ax -= 65536
        if ay > 32767: ay -= 65536
        if az > 32767: az -= 65536

        return ax, ay, az

    def _read_mag_raw(self) -> Tuple[int, int, int]:
        """Read raw magnetometer values"""
        # Wait for data ready
        for _ in range(20):
            time.sleep(0.01)
            data = self._read_secondary(
                I2C_ADD_ICM20948_AK09916 | I2C_ADD_ICM20948_AK09916_READ,
                REG_ADD_MAG_ST2, 1
            )
            if data[0] & 0x01:
                break
        else:
            return 0, 0, 0

        data = self._read_secondary(
            I2C_ADD_ICM20948_AK09916 | I2C_ADD_ICM20948_AK09916_READ,
            REG_ADD_MAG_DATA, MAG_DATA_LEN
        )

        mx = (data[1] << 8) | data[0]
        my = (data[3] << 8) | data[2]
        mz = (data[5] << 8) | data[4]

        # Convert to signed
        if mx > 32767: mx -= 65536
        if my > 32767: my -= 65536
        if mz > 32767: mz -= 65536

        return mx, -my, -mz

    def _inv_sqrt(self, x: float) -> float:
        """Fast inverse square root approximation"""
        if x <= 0:
            return 0.0
        return 1.0 / math.sqrt(x)

    def _ahrs_update(self, gx: float, gy: float, gz: float,
                     ax: float, ay: float, az: float,
                     mx: float, my: float, mz: float) -> None:
        """Update AHRS orientation estimate using Madgwick/Mahony filter"""
        halfT = 0.024

        q0, q1, q2, q3 = self.q0, self.q1, self.q2, self.q3

        # Normalize accelerometer
        norm = self._inv_sqrt(ax*ax + ay*ay + az*az)
        ax *= norm
        ay *= norm
        az *= norm

        # Normalize magnetometer
        norm = self._inv_sqrt(mx*mx + my*my + mz*mz)
        mx *= norm
        my *= norm
        mz *= norm

        # Auxiliary variables
        q0q0, q0q1, q0q2, q0q3 = q0*q0, q0*q1, q0*q2, q0*q3
        q1q1, q1q2, q1q3 = q1*q1, q1*q2, q1*q3
        q2q2, q2q3 = q2*q2, q2*q3
        q3q3 = q3*q3

        # Reference direction of magnetic field
        hx = 2*mx*(0.5 - q2q2 - q3q3) + 2*my*(q1q2 - q0q3) + 2*mz*(q1q3 + q0q2)
        hy = 2*mx*(q1q2 + q0q3) + 2*my*(0.5 - q1q1 - q3q3) + 2*mz*(q2q3 - q0q1)
        hz = 2*mx*(q1q3 - q0q2) + 2*my*(q2q3 + q0q1) + 2*mz*(0.5 - q1q1 - q2q2)
        bx = math.sqrt(hx*hx + hy*hy)
        bz = hz

        # Estimated direction of gravity and magnetic field
        vx = 2*(q1q3 - q0q2)
        vy = 2*(q0q1 + q2q3)
        vz = q0q0 - q1q1 - q2q2 + q3q3
        wx = 2*bx*(0.5 - q2q2 - q3q3) + 2*bz*(q1q3 - q0q2)
        wy = 2*bx*(q1q2 - q0q3) + 2*bz*(q0q1 + q2q3)
        wz = 2*bx*(q0q2 + q1q3) + 2*bz*(0.5 - q1q1 - q2q2)

        # Error is cross product between estimated and measured direction
        ex = (ay*vz - az*vy) + (my*wz - mz*wy)
        ey = (az*vx - ax*vz) + (mz*wx - mx*wz)
        ez = (ax*vy - ay*vx) + (mx*wy - my*wx)

        if ex != 0.0 and ey != 0.0 and ez != 0.0:
            gx += self.Kp*ex
            gy += self.Kp*ey
            gz += self.Kp*ez

        # Integrate quaternion rate
        q0 += (-q1*gx - q2*gy - q3*gz) * halfT
        q1 += (q0*gx + q2*gz - q3*gy) * halfT
        q2 += (q0*gy - q1*gz + q3*gx) * halfT
        q3 += (q0*gz + q1*gy - q2*gx) * halfT

        # Normalize quaternion
        norm = self._inv_sqrt(q0*q0 + q1*q1 + q2*q2 + q3*q3)
        self.q0, self.q1, self.q2, self.q3 = q0*norm, q1*norm, q2*norm, q3*norm

    def read(self) -> Tuple[IMUAngles, IMUSensorData, IMUSensorData, IMUSensorData]:
        """
        Read all sensor data and calculate orientation angles.

        Returns:
            Tuple of (angles, gyro_data, accel_data, mag_data)
        """
        if not self.initialized:
            return IMUAngles(), IMUSensorData(), IMUSensorData(), IMUSensorData()

        with self._lock:
            try:
                # Read raw sensor data
                gx_raw, gy_raw, gz_raw = self._read_gyro_raw()
                ax_raw, ay_raw, az_raw = self._read_accel_raw()
                mx_raw, my_raw, mz_raw = self._read_mag_raw()

                # Apply averaging
                gx = self._calc_avg(self._gyro_idx, self._gyro_avg, 0, gx_raw) - self.gyro_offset[0]
                gy = self._calc_avg(self._gyro_idx, self._gyro_avg, 1, gy_raw) - self.gyro_offset[1]
                gz = self._calc_avg(self._gyro_idx, self._gyro_avg, 2, gz_raw) - self.gyro_offset[2]

                ax = self._calc_avg(self._accel_idx, self._accel_avg, 0, ax_raw)
                ay = self._calc_avg(self._accel_idx, self._accel_avg, 1, ay_raw)
                az = self._calc_avg(self._accel_idx, self._accel_avg, 2, az_raw)

                mx = self._calc_avg(self._mag_idx, self._mag_avg, 0, mx_raw)
                my = self._calc_avg(self._mag_idx, self._mag_avg, 1, my_raw)
                mz = self._calc_avg(self._mag_idx, self._mag_avg, 2, mz_raw)

                # Convert to physical units for AHRS
                motion_gx = gx / 32.8 * 0.0175  # deg/s to rad/s
                motion_gy = gy / 32.8 * 0.0175
                motion_gz = gz / 32.8 * 0.0175

                # Update AHRS
                self._ahrs_update(motion_gx, motion_gy, motion_gz,
                                float(ax), float(ay), float(az),
                                float(mx), float(my), float(mz))

                # Calculate Euler angles from quaternion
                q0, q1, q2, q3 = self.q0, self.q1, self.q2, self.q3
                pitch = math.asin(-2*q1*q3 + 2*q0*q2) * 57.3
                roll = math.atan2(2*q2*q3 + 2*q0*q1, -2*q1*q1 - 2*q2*q2 + 1) * 57.3
                yaw = math.atan2(-2*q1*q2 - 2*q0*q3, 2*q2*q2 + 2*q3*q3 - 1) * 57.3

                # Create output data structures
                angles = IMUAngles(roll=roll, pitch=pitch, yaw=yaw)

                gyro_data = IMUSensorData(
                    x=gx / GYRO_SSF_AT_FS_1000DPS,
                    y=gy / GYRO_SSF_AT_FS_1000DPS,
                    z=gz / GYRO_SSF_AT_FS_1000DPS
                )

                accel_data = IMUSensorData(
                    x=ax / ACCEL_SSF_AT_FS_2g,
                    y=ay / ACCEL_SSF_AT_FS_2g,
                    z=az / ACCEL_SSF_AT_FS_2g
                )

                mag_data = IMUSensorData(
                    x=mx * MAG_SSF_AT_FS_4900uT,
                    y=my * MAG_SSF_AT_FS_4900uT,
                    z=mz * MAG_SSF_AT_FS_4900uT
                )

                return angles, gyro_data, accel_data, mag_data

            except Exception as e:
                print(f"IMU read error: {e}")
                return IMUAngles(), IMUSensorData(), IMUSensorData(), IMUSensorData()

    def close(self) -> None:
        """Close the I2C bus"""
        if self.bus:
            self.bus.close()
            self.bus = None
        self.initialized = False


class ThreadedIMU:
    """
    Threaded IMU reader that continuously updates IMU data in the background.
    """

    def __init__(self, i2c_bus: int = 7, update_rate: float = 0.05):
        """
        Initialize threaded IMU reader.

        Args:
            i2c_bus: I2C bus number
            update_rate: Update interval in seconds (default: 50ms / 20Hz)
        """
        self.imu = ICM20948(i2c_bus)
        self.update_rate = update_rate
        self._running = False
        self._thread = None
        self._lock = threading.Lock()

        # Latest data
        self._angles = IMUAngles()
        self._gyro = IMUSensorData()
        self._accel = IMUSensorData()
        self._mag = IMUSensorData()
        self._available = False

    def start(self) -> bool:
        """Start the IMU reading thread"""
        if not self.imu.initialize():
            return False

        self._running = True
        self._available = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        return True

    def _read_loop(self) -> None:
        """Background thread that continuously reads IMU data"""
        while self._running:
            angles, gyro, accel, mag = self.imu.read()
            with self._lock:
                self._angles = angles
                self._gyro = gyro
                self._accel = accel
                self._mag = mag
            time.sleep(self.update_rate)

    def get_data(self) -> Tuple[IMUAngles, IMUSensorData, IMUSensorData, IMUSensorData]:
        """Get the latest IMU data (thread-safe)"""
        with self._lock:
            return self._angles, self._gyro, self._accel, self._mag

    def get_angles(self) -> IMUAngles:
        """Get just the orientation angles (thread-safe)"""
        with self._lock:
            return self._angles

    @property
    def available(self) -> bool:
        """Check if IMU is available and running"""
        return self._available and self._running

    def stop(self) -> None:
        """Stop the IMU reading thread"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
        self.imu.close()


if __name__ == '__main__':
    # Test the IMU
    print("Testing ICM-20948 IMU...")

    imu = ThreadedIMU()
    if not imu.start():
        print("Failed to initialize IMU")
        exit(1)

    print("IMU initialized. Reading data...")
    try:
        while True:
            angles, gyro, accel, mag = imu.get_data()
            print(f"\r Roll: {angles.roll:7.2f}  Pitch: {angles.pitch:7.2f}  Yaw: {angles.yaw:7.2f}", end="")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping...")
        imu.stop()
