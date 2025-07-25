#!/usr/bin/env python3
"""
Download all motor diagram SVG files from ArduPilot documentation.

This file is autogenerated by the .github/instructions/update_motor_diagrams.md AI instructions file.

This file is part of ArduPilot methodic configurator. https://github.com/ArduPilot/MethodicConfigurator

SPDX-FileCopyrightText: 2024-2025 Amilcar do Carmo Lucas <amilcar.lucas@iav.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""

import urllib.request
from pathlib import Path
from urllib.parse import urlparse

# ruff: noqa: T201

# List of all motor diagram SVG files from the ArduPilot documentation at
# https://ardupilot.org/copter/docs/connect-escs-and-motors.html
motor_diagrams = [
    # QUAD FRAMES
    "m_01_00_quad_plus.svg",
    "m_01_01_quad_x.svg",
    "m_01_02_quad_v.svg",
    "m_01_03_quad_h.svg",
    "m_01_04_quad_v_tail.svg",
    "m_01_05_quad_a_tail.svg",
    "m_01_06_quad_plus_rev.svg",
    "m_01_12_quad_x_bf.svg",
    "m_01_13_quad_x_dji.svg",
    "m_01_14_quad_x_cw.svg",
    "m_01_16_quad_plus_nyt.svg",
    "m_01_17_quad_x_nyt.svg",
    "m_01_18_quad_x_bf_rev.svg",
    "m_01_19_quad_y4a.svg",
    # HEXA FRAMES
    "m_02_00_hexa_plus.svg",
    "m_02_01_hexa_x.svg",
    "m_02_03_hexa_h.svg",
    "m_02_13_hexa_x_dji.svg",
    "m_02_14_hexa_x_cw.svg",
    # OCTO FRAMES
    "m_03_00_octo_plus.svg",
    "m_03_01_octo_x.svg",
    "m_03_02_octo_v.svg",
    "m_03_03_octo_h.svg",
    "m_03_13_octo_x_dji.svg",
    "m_03_14_octo_x_cw.svg",
    "m_03_15_octo_i.svg",
    # OCTO QUAD FRAMES
    "m_04_00_octo_quad_plus.svg",
    "m_04_01_octo_quad_x.svg",
    "m_04_02_octo_quad_v.svg",
    "m_04_03_octo_quad_h.svg",
    "m_04_12_octo_quad_x_bf.svg",
    "m_04_14_octo_quad_x_cw.svg",
    "m_04_18_octo_quad_x_bf_rev.svg",
    # Y6 FRAMES
    "m_05_00_y6_a.svg",
    "m_05_10_y6_b.svg",
    "m_05_11_y6_f.svg",
    # TRICOPTER FRAMES
    "m_07_00_tricopter.svg",
    "m_07_06_tricopter_pitch_rev.svg",
    # BICOPTER FRAMES
    "m_10_00_bicopter.svg",
    # DODECAHEXA FRAMES
    "m_12_00_dodecahexa_plus.svg",
    "m_12_01_dodecahexa_x.svg",
    # DECA FRAMES
    "m_14_00_deca_plus.svg",
    "m_14_01_deca_x_and_cw_x.svg",
]


def download_motor_diagrams() -> None:
    """Download all motor diagram SVG files."""
    base_url = "https://ardupilot.org/copter/_images/"
    images_dir = Path("ardupilot_methodic_configurator/images")

    # Create images directory if it doesn't exist
    images_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    failed = 0

    for filename in motor_diagrams:
        try:
            url = base_url + filename
            output_path = images_dir / filename

            # Validate URL scheme for security
            parsed_url = urlparse(url)
            if parsed_url.scheme not in ("http", "https"):
                print(f"Invalid URL scheme for {filename}: {parsed_url.scheme}")
                failed += 1
                continue

            print(f"Downloading {filename}...")
            urllib.request.urlretrieve(url, output_path)  # noqa: S310
            downloaded += 1

        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"Failed to download {filename}: {e}")
            failed += 1

    print(f"\nDownload complete: {downloaded} succeeded, {failed} failed")


if __name__ == "__main__":
    download_motor_diagrams()
