#!/usr/bin/env python3

"""
Tests backend_mavftp.py file.

MAVLink File Transfer Protocol support test - https://mavlink.io/en/services/ftp.html

This file is part of Ardupilot methodic configurator. https://github.com/ArduPilot/MethodicConfigurator

SPDX-FileCopyrightText: 2024-2025 Amilcar Lucas

SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
import unittest

# from unittest.mock import patch
from io import StringIO

from pymavlink import mavutil

# from ardupilot_methodic_configurator.backend_mavftp import ERR_NoErrorCodeInPayload
# from ardupilot_methodic_configurator.backend_mavftp import ERR_NoErrorCodeInNack
# from ardupilot_methodic_configurator.backend_mavftp import ERR_NoFilesystemErrorInPayload
# from ardupilot_methodic_configurator.backend_mavftp import ERR_PayloadTooLarge
# from ardupilot_methodic_configurator.backend_mavftp import ERR_InvalidOpcode
from ardupilot_methodic_configurator.backend_mavftp import (
    FTP_OP,
    MAVFTP,
    ERR_EndOfFile,
    ERR_Fail,
    ERR_FailErrno,
    ERR_FailToOpenLocalFile,
    ERR_FileExists,
    ERR_FileNotFound,
    ERR_FileProtected,
    ERR_InvalidArguments,
    ERR_InvalidDataSize,
    ERR_InvalidErrorCode,
    ERR_InvalidSession,
    ERR_None,
    ERR_NoSessionsAvailable,
    ERR_PutAlreadyInProgress,
    ERR_RemoteReplyTimeout,
    ERR_UnknownCommand,
    MAVFTPReturn,
    OP_Ack,
    OP_ListDirectory,
    OP_Nack,
    OP_ReadFile,
)


class TestMAVFTPPayloadDecoding(unittest.TestCase):
    """Test MAVFTP payload decoding."""

    def setUp(self) -> None:
        self.log_stream = StringIO()
        handler = logging.StreamHandler(self.log_stream)
        formatter = logging.Formatter("%(levelname)s: %(message)s")
        handler.setFormatter(formatter)
        logger = logging.getLogger()
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        # Mock mavutil.mavlink_connection to simulate a connection
        self.mock_master = mavutil.mavlink_connection(device="udp:localhost:14550", source_system=1)

        # Initialize MAVFTP instance for testing
        self.mav_ftp = MAVFTP(self.mock_master, target_system=1, target_component=1)

    def tearDown(self) -> None:
        self.log_stream.seek(0)
        self.log_stream.truncate(0)

    def test_logging(self) -> None:
        # Code that triggers logging
        logging.info("This is a test log message")

        # Flush and get log output
        log_output = self.log_stream.getvalue()

        # Assert to check if the expected log is in log_output
        assert "This is a test log message" in log_output

    @staticmethod
    def ftp_operation(seq: int, opcode: int, req_opcode: int, payload: bytearray) -> FTP_OP:
        return FTP_OP(
            seq=seq, session=1, opcode=opcode, size=0, req_opcode=req_opcode, burst_complete=0, offset=0, payload=payload
        )

    def test_decode_ftp_ack_and_nack(self) -> None:
        # Test cases grouped by expected outcome
        test_cases = [
            {
                "name": "Successful Operation",
                "op": self.ftp_operation(seq=1, opcode=OP_Ack, req_opcode=OP_ListDirectory, payload=None),
                "expected_message": "ListDirectory succeeded",
            },
            {
                "name": "Generic Failure",
                "op": self.ftp_operation(seq=2, opcode=OP_Nack, req_opcode=OP_ListDirectory, payload=bytes([ERR_Fail])),
                "expected_message": "ListDirectory failed, generic error",
            },
            {
                "name": "System Error",
                "op": self.ftp_operation(
                    seq=3, opcode=OP_Nack, req_opcode=OP_ListDirectory, payload=bytes([ERR_FailErrno, 1])
                ),  # System error 1
                "expected_message": "ListDirectory failed, system error 1",
            },
            {
                "name": "Invalid Data Size",
                "op": self.ftp_operation(
                    seq=4, opcode=OP_Nack, req_opcode=OP_ListDirectory, payload=bytes([ERR_InvalidDataSize])
                ),
                "expected_message": "ListDirectory failed, invalid data size",
            },
            {
                "name": "Invalid Session",
                "op": self.ftp_operation(
                    seq=5, opcode=OP_Nack, req_opcode=OP_ListDirectory, payload=bytes([ERR_InvalidSession])
                ),
                "expected_message": "ListDirectory failed, session is not currently open",
            },
            {
                "name": "No Sessions Available",
                "op": self.ftp_operation(
                    seq=6, opcode=OP_Nack, req_opcode=OP_ListDirectory, payload=bytes([ERR_NoSessionsAvailable])
                ),
                "expected_message": "ListDirectory failed, no sessions available",
            },
            {
                "name": "End of File",
                "op": self.ftp_operation(seq=7, opcode=OP_Nack, req_opcode=OP_ListDirectory, payload=bytes([ERR_EndOfFile])),
                "expected_message": "ListDirectory failed, offset past end of file",
            },
            {
                "name": "Unknown Command",
                "op": self.ftp_operation(
                    seq=8, opcode=OP_Nack, req_opcode=OP_ListDirectory, payload=bytes([ERR_UnknownCommand])
                ),
                "expected_message": "ListDirectory failed, unknown command",
            },
            {
                "name": "File Exists",
                "op": self.ftp_operation(seq=9, opcode=OP_Nack, req_opcode=OP_ListDirectory, payload=bytes([ERR_FileExists])),
                "expected_message": "ListDirectory failed, file/directory already exists",
            },
            {
                "name": "File Protected",
                "op": self.ftp_operation(
                    seq=10, opcode=OP_Nack, req_opcode=OP_ListDirectory, payload=bytes([ERR_FileProtected])
                ),
                "expected_message": "ListDirectory failed, file/directory is protected",
            },
            {
                "name": "File Not Found",
                "op": self.ftp_operation(
                    seq=11, opcode=OP_Nack, req_opcode=OP_ListDirectory, payload=bytes([ERR_FileNotFound])
                ),
                "expected_message": "ListDirectory failed, file/directory not found",
            },
            {
                "name": "No Error Code in Payload",
                "op": self.ftp_operation(seq=12, opcode=OP_Nack, req_opcode=OP_ListDirectory, payload=None),
                "expected_message": "ListDirectory failed, payload contains no error code",
            },
            {
                "name": "No Error Code in Nack",
                "op": self.ftp_operation(seq=13, opcode=OP_Nack, req_opcode=OP_ListDirectory, payload=bytes([ERR_None])),
                "expected_message": "ListDirectory failed, no error code",
            },
            {
                "name": "No Filesystem Error in Payload",
                "op": self.ftp_operation(seq=14, opcode=OP_Nack, req_opcode=OP_ListDirectory, payload=bytes([ERR_FailErrno])),
                "expected_message": "ListDirectory failed, file-system error missing in payload",
            },
            {
                "name": "Invalid Error Code",
                "op": self.ftp_operation(
                    seq=15, opcode=OP_Nack, req_opcode=OP_ListDirectory, payload=bytes([ERR_InvalidErrorCode])
                ),
                "expected_message": "ListDirectory failed, invalid error code",
            },
            {
                "name": "Payload Too Large",
                "op": self.ftp_operation(seq=16, opcode=OP_Nack, req_opcode=OP_ListDirectory, payload=bytes([0, 0, 0])),
                "expected_message": "ListDirectory failed, payload is too long",
            },
            {
                "name": "Invalid Opcode",
                "op": self.ftp_operation(seq=17, opcode=126, req_opcode=OP_ListDirectory, payload=None),
                "expected_message": "ListDirectory failed, invalid opcode 126",
            },
            {
                "name": "Unknown Opcode in Request",
                "op": self.ftp_operation(
                    seq=19, opcode=OP_Nack, req_opcode=OP_ListDirectory, payload=bytes([ERR_UnknownCommand])
                ),  # Assuming 100 is an unknown opcode
                "expected_message": "ListDirectory failed, unknown command",
            },
            {
                "name": "Payload with System Error",
                "op": self.ftp_operation(
                    seq=20, opcode=OP_Nack, req_opcode=OP_ListDirectory, payload=bytes([ERR_FailErrno, 2])
                ),  # System error 2
                "expected_message": "ListDirectory failed, system error 2",
            },
            {
                "name": "Invalid Error Code in Payload",
                "op": self.ftp_operation(
                    seq=21, opcode=OP_Nack, req_opcode=OP_ListDirectory, payload=bytes([105])
                ),  # Assuming 105 is an invalid error code
                "expected_message": "ListDirectory failed, invalid error code 105",
            },
            {
                "name": "Invalid Opcode with Payload",
                "op": self.ftp_operation(
                    seq=23, opcode=126, req_opcode=OP_ReadFile, payload=bytes([1, 1])
                ),  # Invalid opcode with payload
                "expected_message": "ReadFile failed, invalid opcode 126",
            },
            # Add more test cases as needed...
        ]

        for case in test_cases:
            ret = self.mav_ftp._MAVFTP__decode_ftp_ack_and_nack(case["op"])  # pylint: disable=protected-access
            ret.display_message()
            log_output = self.log_stream.getvalue().strip()
            assert case["expected_message"] in log_output, (
                f"Test {case['name']}: Expected {case['expected_message']} but got {log_output}"
            )
            self.log_stream.seek(0)
            self.log_stream.truncate(0)

        # Invalid Arguments
        ret = MAVFTPReturn("Command arguments", ERR_InvalidArguments)
        ret.display_message()
        log_output = self.log_stream.getvalue().strip()
        assert "Command arguments failed, invalid arguments" in log_output, "Expected invalid arguments message"
        self.log_stream.seek(0)
        self.log_stream.truncate(0)

        # Test for unknown error code in display_message
        op = self.ftp_operation(seq=22, opcode=OP_Nack, req_opcode=OP_ListDirectory, payload=bytes([255]))
        ret = self.mav_ftp._MAVFTP__decode_ftp_ack_and_nack(op, "ListDirectory")  # pylint: disable=protected-access
        ret.error_code = 125  # Set error code to 125 to trigger unknown error message
        ret.display_message()
        log_output = self.log_stream.getvalue().strip()
        assert "ListDirectory failed, unknown error 125 in display_message()" in log_output, (
            "Expected unknown error message for unknown error code"
        )
        self.log_stream.seek(0)
        self.log_stream.truncate(0)

        # Put already in progress
        ret = MAVFTPReturn("Put", ERR_PutAlreadyInProgress)
        ret.display_message()
        log_output = self.log_stream.getvalue().strip()
        assert "Put failed, put already in progress" in log_output, "Expected put already in progress message"
        self.log_stream.seek(0)
        self.log_stream.truncate(0)

        # Fail to open local file
        ret = MAVFTPReturn("Put", ERR_FailToOpenLocalFile)
        ret.display_message()
        log_output = self.log_stream.getvalue().strip()
        assert "Put failed, failed to open local file" in log_output, "Expected fail to open local file message"
        self.log_stream.seek(0)
        self.log_stream.truncate(0)

        # Remote Reply Timeout
        ret = MAVFTPReturn("Put", ERR_RemoteReplyTimeout)
        ret.display_message()
        log_output = self.log_stream.getvalue().strip()
        assert "Put failed, remote reply timeout" in log_output, "Expected remote reply timeout message"
        self.log_stream.seek(0)
        self.log_stream.truncate(0)


if __name__ == "__main__":
    unittest.main()
