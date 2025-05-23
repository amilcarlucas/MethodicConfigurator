#!/usr/bin/python3
# PYTHON_ARGCOMPLETE_OK

"""
Extracts parameter values or parameter default values from an ArduPilot .bin log file.

Supports Mission Planner, MAVProxy and QGCS file format output

Currently has 95% unit test coverage

SPDX-FileCopyrightText: 2024-2025 Amilcar do Carmo Lucas <amilcar.lucas@iav.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""

import argparse
import contextlib
import re
from typing import Union

import argcomplete
from argcomplete.completers import FilesCompleter
from pymavlink import mavutil

NO_DEFAULT_VALUES_MESSAGE = "The .bin file contained no parameter default values. Update to a newer ArduPilot firmware version"
PARAM_NAME_REGEX = r"^[A-Z][A-Z_0-9]*$"
PARAM_NAME_MAX_LEN = 16
MAVLINK_SYSID_MAX = 2**24
MAVLINK_COMPID_MAX = 2**8
MAV_PARAM_TYPE_REAL32 = 9


def create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extracts parameter default values from an ArduPilot .bin log file.")
    parser.add_argument(
        "-f",
        "--format",
        choices=["missionplanner", "mavproxy", "qgcs"],
        default="missionplanner",
        help="Output file format. Default is %(default)s.",
    )
    parser.add_argument(
        "-s",
        "--sort",
        choices=["none", "missionplanner", "mavproxy", "qgcs"],
        default="",
        help="Sort the parameters in the file. Default is the same as the format.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="%(prog)s 1.1",
        help="Display version information and exit.",
    )
    parser.add_argument(
        "-i",
        "--sysid",
        type=int,
        default=-1,
        help="System ID for qgcs output format. Default is SYSID_THISMAV if defined else 1.",
    )
    parser.add_argument(
        "-c",
        "--compid",
        type=int,
        default=-1,
        help="Component ID for qgcs output format. Default is 1.",
    )
    parser.add_argument(
        "-t",
        "--type",
        choices=["defaults", "values", "non_default_values"],
        default="defaults",
        help="Type of parameter values to extract. Default is %(default)s.",
    )
    parser.add_argument(
        "bin_file",
        help="The ArduPilot .bin log file to read",
    ).completer = FilesCompleter(allowednames=[".bin"])  # type: ignore[attr-defined, no-untyped-call]

    argcomplete.autocomplete(parser)
    return parser


def parse_arguments(args: Union[None, argparse.Namespace] = None) -> argparse.Namespace:
    """
    Parses command line arguments for the script.

    Args:
        args: List of command line arguments. Default is None, which means it uses sys.argv.

    Returns:
        Namespace object containing the parsed arguments.

    """
    parser = create_argument_parser()
    args, _ = parser.parse_known_args(args)  # type: ignore[arg-type]

    if args is None:
        msg = "No arguments provided"
        raise ValueError(msg)

    if args.sort == "":
        args.sort = args.format

    if args.format != "qgcs":
        if args.sysid != -1:
            msg = "--sysid parameter is only relevant if --format is qgcs"
            raise SystemExit(msg)
        if args.compid != -1:
            msg = "--compid parameter is only relevant if --format is qgcs"
            raise SystemExit(msg)

    return args


def extract_parameter_values(logfile: str, param_type: str = "defaults") -> dict[str, float]:  # pylint: disable=too-many-branches
    """
    Extracts the parameter values from an ArduPilot .bin log file.

    Args:
        logfile: The path to the ArduPilot .bin log file.
        param_type: The type of parameter values to extract. Can be 'defaults', 'values' or 'non_default_values'.

    Returns:
        A dictionary with parameter names as keys and their values as float.

    """
    try:
        mlog = mavutil.mavlink_connection(logfile)
    except Exception as e:
        msg = f"Error opening the {logfile} logfile: {e!s}"
        raise SystemExit(msg) from e
    values: dict[str, float] = {}
    while True:
        m = mlog.recv_match(type=["PARM"])
        if m is None:
            if not values:
                raise SystemExit(NO_DEFAULT_VALUES_MESSAGE)
            return values
        pname = str(m.Name)
        if len(pname) > PARAM_NAME_MAX_LEN:
            msg = f"Too long parameter name: {pname}"
            raise SystemExit(msg)
        if not re.match(PARAM_NAME_REGEX, pname):
            msg = f"Invalid parameter name {pname}"
            raise SystemExit(msg)
        # parameter names are supposed to be unique
        if pname in values:
            continue
        if param_type == "defaults":
            if hasattr(m, "Default") and m.Default is not None:
                try:
                    values[pname] = float(m.Default)
                except ValueError as e:
                    msg = f"Error converting {m.Default} to float"
                    raise SystemExit(msg) from e
        elif param_type == "values":
            if hasattr(m, "Value") and m.Value is not None:
                try:
                    values[pname] = float(m.Value)
                except ValueError as e:
                    msg = f"Error converting {m.Value} to float"
                    raise SystemExit(msg) from e
        elif param_type == "non_default_values":
            if hasattr(m, "Value") and hasattr(m, "Default") and m.Value != m.Default and m.Value is not None:
                try:
                    values[pname] = float(m.Value)
                except ValueError as e:
                    msg = f"Error converting {m.Value} to float"
                    raise SystemExit(msg) from e
        else:
            msg = f"Invalid type {param_type}"
            raise SystemExit(msg)


def missionplanner_sort(item: str) -> tuple[str, ...]:
    """
    Sorts a parameter name according to the rules defined in the Mission Planner software.

    Args:
        item: The parameter name to sort.

    Returns:
        A tuple representing the sorted parameter name.

    """
    parts = item.split("_")  # Split the parameter name by underscore
    # Compare the parts separately
    return tuple(parts)


def mavproxy_sort(item: str) -> str:
    """
    Sorts a parameter name according to the rules defined in the MAVProxy software.

    Args:
        item: The parameter name to sort.

    Returns:
        The sorted parameter name.

    """
    return item


def sort_params(params: dict[str, float], sort_type: str = "none") -> dict[str, float]:
    """
    Sorts parameter names according to sort_type.

    Args:
        params: A dictionary with parameter names as keys and their values as float.
        sort_type: The type of sorting to apply. Can be 'none', 'missionplanner', 'mavproxy' or 'qgcs'.

    Returns:
        A dictionary with parameter names as keys and their values as float.

    """
    if sort_type == "missionplanner":
        params = dict(sorted(params.items(), key=lambda x: missionplanner_sort(x[0])))
    elif sort_type == "mavproxy":
        params = dict(sorted(params.items(), key=lambda x: mavproxy_sort(x[0])))
    elif sort_type == "qgcs":
        params = {k: params[k] for k in sorted(params)}
    return params


def output_params(
    params: dict[str, float],
    format_type: str = "missionplanner",
    sysid: int = -1,
    compid: int = -1,
) -> None:
    """
    Outputs parameters names and their values to the console.

    Args:
        params: A dictionary with parameter names as keys and their values as float.
        format_type: The output file format. Can be 'missionplanner', 'mavproxy' or 'qgcs'.
        sysid: MAVLink System ID
        compid: MAVLink component ID

    Returns:
        None

    """
    if format_type == "qgcs":
        if sysid == -1:
            # if unspecified, default to 1
            sysid = int(params["SYSID_THISMAV"]) if "SYSID_THISMAV" in params else 1
        if compid == -1:
            compid = 1  # if unspecified, default to 1
        if sysid < 0:
            msg = f"Invalid system ID parameter {sysid} must not be negative"
            raise SystemExit(msg)
        if sysid > MAVLINK_SYSID_MAX - 1:
            msg = f"Invalid system ID parameter {sysid} must be smaller than {MAVLINK_SYSID_MAX}"
            raise SystemExit(msg)
        if compid < 0:
            msg = f"Invalid component ID parameter {compid} must not be negative"
            raise SystemExit(msg)
        if compid > MAVLINK_COMPID_MAX - 1:
            msg = f"Invalid component ID parameter {compid} must be smaller than {MAVLINK_COMPID_MAX}"
            raise SystemExit(msg)
        # see https://dev.qgroundcontrol.com/master/en/file_formats/parameters.html
        print("""
# # Vehicle-Id Component-Id Name Value Type
""")  # noqa: T201

    for param_name, param_value in params.items():
        if format_type == "missionplanner":
            param_value_conv: Union[float, str] = param_value
            # preserve non-floating point strings, if present
            with contextlib.suppress(ValueError):
                param_value_conv = format(param_value, ".6f").rstrip("0").rstrip(".")
            print(f"{param_name},{param_value_conv}")  # noqa: T201
        elif format_type == "mavproxy":
            print(f"{param_name:<15} {param_value:.6f}")  # noqa: T201
        elif format_type == "qgcs":
            print(f"{sysid} {compid} {param_name:<15} {param_value:.6f} {MAV_PARAM_TYPE_REAL32}")  # noqa: T201


def main() -> None:
    args = parse_arguments()
    parameter_values = extract_parameter_values(args.bin_file, args.type)
    parameter_values = sort_params(parameter_values, args.sort)
    output_params(parameter_values, args.format, args.sysid, args.compid)


if __name__ == "__main__":
    main()
