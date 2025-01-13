#!/usr/bin/python3

"""
Tests for the annotate_params.py script.

These are the unit tests for the python script that fetches online ArduPilot
parameter documentation (if not cached) and adds it to the specified file or
to all *.param and *.parm files in the specified directory.

Author: Amilcar do Carmo Lucas
"""

import contextlib
import os
import tempfile
import unittest
from unittest import mock
from unittest.mock import patch
from xml.etree import ElementTree as ET  # no parsing, just data-structure manipulation

import pytest
import requests  # type: ignore[import-untyped]
from defusedxml import ElementTree as DET  # noqa: N814, just parsing, no data-structure manipulation

from ardupilot_methodic_configurator.annotate_params import (
    BASE_URL,
    PARAM_DEFINITION_XML_FILE,
    arg_parser,
    create_doc_dict,
    format_columns,
    get_xml_data,
    get_xml_url,
    main,
    print_read_only_params,
    remove_prefix,
    split_into_lines,
    update_parameter_documentation,
)


@pytest.fixture
def mock_update() -> mock.Mock:
    with patch("ardupilot_methodic_configurator.annotate_params.update_parameter_documentation") as mock_fun:
        yield mock_fun


@pytest.fixture
def mock_get_xml_dir() -> mock.Mock:
    with patch("ardupilot_methodic_configurator.annotate_params.get_xml_dir") as mock_fun:
        yield mock_fun


@pytest.fixture
def mock_get_xml_url() -> mock.Mock:
    with patch("ardupilot_methodic_configurator.annotate_params.get_xml_url") as mock_fun:
        yield mock_fun


class TestParamDocsUpdate(unittest.TestCase):  # pylint: disable=missing-class-docstring, too-many-public-methods
    def setUp(self) -> None:
        # Create a temporary directory
        self.temp_dir = tempfile.mkdtemp()

        # Create a temporary file
        # pylint: disable=consider-using-with
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)  # noqa: SIM115
        # pylint: enable=consider-using-with

        # Create a dictionary of parameter documentation
        self.doc_dict = {
            "PARAM1": {
                "humanName": "Param 1",
                "documentation": ["Documentation for Param 1"],
                "fields": {"Field1": "Value1", "Field2": "Value2"},
                "values": {"Code1": "Value1", "Code2": "Value2"},
            },
            "PARAM2": {
                "humanName": "Param 2",
                "documentation": ["Documentation for Param 2"],
                "fields": {"Field3": "Value3", "Field4": "Value4"},
                "values": {"Code3": "Value3", "Code4": "Value4"},
            },
            "PARAM_1": {
                "humanName": "Param _ 1",
                "documentation": ["Documentation for Param_1"],
                "fields": {"Field_1": "Value_1", "Field_2": "Value_2"},
                "values": {"Code_1": "Value_1", "Code_2": "Value_2"},
            },
        }

    @patch("builtins.open", new_callable=mock.mock_open, read_data="<root></root>")
    @patch("os.path.isfile")
    @patch("ardupilot_methodic_configurator.annotate_params.Par.load_param_file_into_dict")
    def test_get_xml_data_local_file(self, mock_load_param, mock_isfile, mock_open_) -> None:
        # Mock the isfile function to return True
        mock_isfile.return_value = True

        # Mock the load_param_file_into_dict function to raise FileNotFoundError
        mock_load_param.side_effect = FileNotFoundError

        # Call the function with a local file
        result = get_xml_data("/path/to/local/file/", ".", "test.xml", "ArduCopter")

        # Check the result
        assert isinstance(result, ET.Element)

        # Assert that the file was opened correctly
        mock_open_.assert_called_once_with(os.path.join(".", "test.xml"), encoding="utf-8")

    @patch("requests.get")
    def test_get_xml_data_remote_file(self, mock_get) -> None:
        # Mock the response
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "<root></root>"

        # Remove the test.xml file if it exists
        with contextlib.suppress(FileNotFoundError):
            os.remove("test.xml")

        # Call the function with a remote file
        result = get_xml_data("http://example.com/", ".", "test.xml", "ArduCopter")

        # Check the result
        assert isinstance(result, ET.Element)

        # Assert that the requests.get function was called once
        mock_get.assert_called_once_with("http://example.com/test.xml", timeout=5)

    @patch("os.path.isfile")
    @patch("ardupilot_methodic_configurator.annotate_params.Par.load_param_file_into_dict")
    def test_get_xml_data_script_dir_file(self, mock_load_param, mock_isfile) -> None:
        # Mock the isfile function to return False for the current directory and True for the script directory
        def side_effect(_filename) -> bool:
            return True

        mock_isfile.side_effect = side_effect

        # Mock the load_param_file_into_dict function to raise FileNotFoundError
        mock_load_param.side_effect = FileNotFoundError

        # Mock the open function to return a dummy XML string
        mock_open = mock.mock_open(read_data="<root></root>")
        with patch("builtins.open", mock_open):
            # Call the function with a filename that exists in the script directory
            result = get_xml_data(BASE_URL, ".", PARAM_DEFINITION_XML_FILE, "ArduCopter")

        # Check the result
        assert isinstance(result, ET.Element)

        # Assert that the file was opened correctly
        mock_open.assert_called_once_with(os.path.join(".", PARAM_DEFINITION_XML_FILE), encoding="utf-8")

    def test_get_xml_data_no_requests_package(self) -> None:
        # Temporarily remove the requests module
        with patch.dict("sys.modules", {"requests": None}):
            # Remove the test.xml file if it exists
            with contextlib.suppress(FileNotFoundError):
                os.remove("test.xml")

            # Call the function with a remote file
            with pytest.raises(SystemExit):
                get_xml_data("http://example.com/", ".", "test.xml", "ArduCopter")

    @patch("requests.get")
    def test_get_xml_data_request_failure(self, mock_get) -> None:
        # Mock the response
        mock_get.side_effect = requests.exceptions.RequestException

        # Remove the test.xml file if it exists
        with contextlib.suppress(FileNotFoundError):
            os.remove("test.xml")

        # Call the function with a remote file
        with pytest.raises(SystemExit):
            get_xml_data("http://example.com/", ".", "test.xml", "ArduCopter")

    @patch("requests.get")
    def test_get_xml_data_valid_xml(self, mock_get) -> None:
        # Mock the response
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "<root></root>"

        # Call the function with a remote file
        result = get_xml_data("http://example.com/", ".", "test.xml", "ArduCopter")

        # Check the result
        assert isinstance(result, ET.Element)

    @patch("requests.get")
    def test_get_xml_data_invalid_xml(self, mock_get) -> None:
        # Mock the response
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "<root><invalid></root>"

        # Remove the test.xml file if it exists
        with contextlib.suppress(FileNotFoundError):
            os.remove("test.xml")

        # Call the function with a remote file
        with pytest.raises(ET.ParseError):
            get_xml_data("http://example.com/", ".", "test.xml", "ArduCopter")

    @patch("requests.get")
    @patch("os.path.isfile")
    def test_get_xml_data_missing_file(self, mock_isfile, mock_get) -> None:
        # Mock the isfile function to return False
        mock_isfile.return_value = False
        # Mock the requests.get call to raise FileNotFoundError
        mock_get.side_effect = FileNotFoundError

        # Remove the test.xml file if it exists
        with contextlib.suppress(FileNotFoundError):
            os.remove("test.xml")

        # Call the function with a local file
        with pytest.raises(FileNotFoundError):
            get_xml_data("/path/to/local/file/", ".", "test.xml", "ArduCopter")

    @patch("requests.get")
    def test_get_xml_data_network_issue(self, mock_get) -> None:
        # Mock the response
        mock_get.side_effect = requests.exceptions.ConnectionError

        # Call the function with a remote file
        with pytest.raises(SystemExit):
            get_xml_data("http://example.com/", ".", "test.xml", "ArduCopter")

    def test_remove_prefix(self) -> None:
        # Test case 1: Normal operation
        assert remove_prefix("prefix_test", "prefix_") == "test"

        # Test case 2: Prefix not present
        assert remove_prefix("test", "prefix_") == "test"

        # Test case 3: Empty string
        assert remove_prefix("", "prefix_") == ""

    def test_split_into_lines(self) -> None:
        # Test case 1: Normal operation
        string_to_split = "This is a test string. It should be split into several lines."
        maximum_line_length = 12
        expected_output = ["This is a", "test string.", "It should be", "split into", "several", "lines."]
        assert split_into_lines(string_to_split, maximum_line_length) == expected_output

        # Test case 2: String shorter than maximum line length
        string_to_split = "Short"
        maximum_line_length = 10
        expected_output = ["Short"]
        assert split_into_lines(string_to_split, maximum_line_length) == expected_output

        # Test case 3: Empty string
        string_to_split = ""
        maximum_line_length = 10
        expected_output = []
        assert split_into_lines(string_to_split, maximum_line_length) == expected_output

    def test_create_doc_dict(self) -> None:
        # Mock XML data
        xml_data = """
        <root>
            <param name="PARAM1" humanName="Param 1" documentation="Documentation for Param 1">
                <field name="Field1">Value1</field>
                <field name="Field2">Value2</field>
                <values>
                    <value code="Code1">Value1</value>
                    <value code="Code2">Value2</value>
                </values>
            </param>
            <param name="PARAM2" humanName="Param 2" documentation="Documentation for Param 2">
                <field name="Units">m/s</field>
                <field name="UnitText">meters per second</field>
                <values>
                    <value code="Code3">Value3</value>
                    <value code="Code4">Value4</value>
                </values>
            </param>
        </root>
        """
        root = DET.fromstring(xml_data)

        # Expected output
        expected_output = {
            "PARAM1": {
                "humanName": "Param 1",
                "documentation": ["Documentation for Param 1"],
                "fields": {"Field1": "Value1", "Field2": "Value2"},
                "values": {"Code1": "Value1", "Code2": "Value2"},
            },
            "PARAM2": {
                "humanName": "Param 2",
                "documentation": ["Documentation for Param 2"],
                "fields": {"Units": "m/s (meters per second)"},
                "values": {"Code3": "Value3", "Code4": "Value4"},
            },
        }

        # Call the function with the mock XML data
        result = create_doc_dict(root, "VehicleType")

        # Check the result
        assert result == expected_output

    def test_format_columns(self) -> None:
        # Define the input
        values = {
            "Key1": "Value1",
            "Key2": "Value2",
            "Key3": "Value3",
            "Key4": "Value4",
            "Key5": "Value5",
            "Key6": "Value6",
            "Key7": "Value7",
            "Key8": "Value8",
            "Key9": "Value9",
            "Key10": "Value10",
            "Key11": "Value11",
            "Key12": "Value12",
        }

        # Define the expected output
        expected_output = [
            "Key1: Value1                                         Key7: Value7",
            "Key2: Value2                                         Key8: Value8",
            "Key3: Value3                                         Key9: Value9",
            "Key4: Value4                                         Key10: Value10",
            "Key5: Value5                                         Key11: Value11",
            "Key6: Value6                                         Key12: Value12",
        ]

        # Call the function with the input
        result = format_columns(values)

        # Check the result
        assert result == expected_output

        assert not format_columns({})

    def test_update_parameter_documentation(self) -> None:
        # Write some initial content to the temporary file
        with open(self.temp_file.name, "w", encoding="utf-8") as file:
            file.write("PARAM1 100\n")

        # Call the function with the temporary file
        update_parameter_documentation(self.doc_dict, self.temp_file.name)

        # Read the updated content from the temporary file
        with open(self.temp_file.name, encoding="utf-8") as file:
            updated_content = file.read()

        # Check if the file has been updated correctly
        assert "Param 1" in updated_content
        assert "Documentation for Param 1" in updated_content
        assert "Field1: Value1" in updated_content
        assert "Field2: Value2" in updated_content
        assert "Code1: Value1" in updated_content
        assert "Code2: Value2" in updated_content

    def test_update_parameter_documentation_sorting_none(self) -> None:
        # Write some initial content to the temporary file
        # With stray leading and trailing whitespaces
        with open(self.temp_file.name, "w", encoding="utf-8") as file:
            file.write("PARAM2 100\n PARAM_1 100 \nPARAM3 3\nPARAM4 4\nPARAM5 5\nPARAM1 100\n")

        # Call the function with the temporary file
        update_parameter_documentation(self.doc_dict, self.temp_file.name)

        # Read the updated content from the temporary file
        with open(self.temp_file.name, encoding="utf-8") as file:
            updated_content = file.read()

        expected_content = """# Param 2
# Documentation for Param 2
# Field3: Value3
# Field4: Value4
# Code3: Value3
# Code4: Value4
PARAM2 100

# Param _ 1
# Documentation for Param_1
# Field_1: Value_1
# Field_2: Value_2
# Code_1: Value_1
# Code_2: Value_2
PARAM_1 100
PARAM3 3
PARAM4 4
PARAM5 5

# Param 1
# Documentation for Param 1
# Field1: Value1
# Field2: Value2
# Code1: Value1
# Code2: Value2
PARAM1 100
"""
        assert updated_content == expected_content

    def test_update_parameter_documentation_sorting_missionplanner(self) -> None:
        # Write some initial content to the temporary file
        with open(self.temp_file.name, "w", encoding="utf-8") as file:
            file.write("PARAM2 100 # ignore, me\nPARAM_1\t100\nPARAM1,100\n")

        # Call the function with the temporary file
        update_parameter_documentation(self.doc_dict, self.temp_file.name, "missionplanner")

        # Read the updated content from the temporary file
        with open(self.temp_file.name, encoding="utf-8") as file:
            updated_content = file.read()

        expected_content = """# Param _ 1
# Documentation for Param_1
# Field_1: Value_1
# Field_2: Value_2
# Code_1: Value_1
# Code_2: Value_2
PARAM_1\t100

# Param 1
# Documentation for Param 1
# Field1: Value1
# Field2: Value2
# Code1: Value1
# Code2: Value2
PARAM1,100

# Param 2
# Documentation for Param 2
# Field3: Value3
# Field4: Value4
# Code3: Value3
# Code4: Value4
PARAM2 100 # ignore, me
"""
        assert updated_content == expected_content

    def test_update_parameter_documentation_sorting_mavproxy(self) -> None:
        # Write some initial content to the temporary file
        with open(self.temp_file.name, "w", encoding="utf-8") as file:
            file.write("PARAM2 100\nPARAM_1\t100\nPARAM1,100\n")

        # Call the function with the temporary file
        update_parameter_documentation(self.doc_dict, self.temp_file.name, "mavproxy")

        # Read the updated content from the temporary file
        with open(self.temp_file.name, encoding="utf-8") as file:
            updated_content = file.read()

        expected_content = """# Param 1
# Documentation for Param 1
# Field1: Value1
# Field2: Value2
# Code1: Value1
# Code2: Value2
PARAM1,100

# Param 2
# Documentation for Param 2
# Field3: Value3
# Field4: Value4
# Code3: Value3
# Code4: Value4
PARAM2 100

# Param _ 1
# Documentation for Param_1
# Field_1: Value_1
# Field_2: Value_2
# Code_1: Value_1
# Code_2: Value_2
PARAM_1\t100
"""
        assert updated_content == expected_content

    def test_update_parameter_documentation_invalid_line_format(self) -> None:
        # Write some initial content to the temporary file with an invalid line format
        with open(self.temp_file.name, "w", encoding="utf-8") as file:
            file.write("%INVALID_LINE_FORMAT\n")

        # Call the function with the temporary file
        with pytest.raises(SystemExit) as cm:
            update_parameter_documentation(self.doc_dict, self.temp_file.name)

        # Check if the SystemExit exception contains the expected message
        assert cm.value.code == "Invalid line in input file"

    @patch("logging.Logger.info")
    def test_print_read_only_params(self, mock_info) -> None:
        # Mock XML data
        xml_data = """
        <root>
            <param name="PARAM1" humanName="Param 1" documentation="Documentation for Param 1">
                <field name="ReadOnly">True</field>
                <field name="Field1">Value1</field>
                <field name="Field2">Value2</field>
                <values>
                    <value code="Code1">Value1</value>
                    <value code="Code2">Value2</value>
                </values>
            </param>
            <param name="PARAM2" humanName="Param 2" documentation="Documentation for Param 2">
                <field name="Field3">Value3</field>
                <field name="Field4">Value4</field>
                <values>
                    <value code="Code3">Value3</value>
                    <value code="Code4">Value4</value>
                </values>
            </param>
        </root>
        """
        root = DET.fromstring(xml_data)
        doc_dict = create_doc_dict(root, "VehicleType")

        # Call the function with the mock XML data
        print_read_only_params(doc_dict)

        # Check if the parameter name was logged
        mock_info.assert_has_calls([mock.call("ReadOnly parameters:"), mock.call("PARAM1")])

    def test_update_parameter_documentation_invalid_target(self) -> None:
        with pytest.raises(ValueError, match="Target 'invalid_target' is neither a file nor a directory."):
            update_parameter_documentation(self.doc_dict, "invalid_target")

    def test_invalid_parameter_name(self) -> None:
        # Write some initial content to the temporary file
        with open(self.temp_file.name, "w", encoding="utf-8") as file:
            file.write("INVALID_$PARAM 100\n")

        # Call the function with the temporary file
        with pytest.raises(SystemExit):
            update_parameter_documentation(self.doc_dict, self.temp_file.name)

    def test_update_parameter_documentation_too_long_parameter_name(self) -> None:
        # Write some initial content to the temporary file
        with open(self.temp_file.name, "w", encoding="utf-8") as file:
            file.write("TOO_LONG_PARAMETER_NAME 100\n")

        # Call the function with the temporary file
        with pytest.raises(SystemExit):
            update_parameter_documentation(self.doc_dict, self.temp_file.name)

    @patch("logging.Logger.warning")
    def test_missing_parameter_documentation(self, mock_warning) -> None:
        # Write some initial content to the temporary file
        with open(self.temp_file.name, "w", encoding="utf-8") as file:
            file.write("MISSING_DOC_PARA 100\n")

        # Call the function with the temporary file
        update_parameter_documentation(self.doc_dict, self.temp_file.name)

        # Check if the warnings were logged
        mock_warning.assert_has_calls(
            [
                mock.call("Read file %s with %d parameters, but only %s of which got documented", self.temp_file.name, 1, 0),
                mock.call("No documentation found for: %s", "MISSING_DOC_PARA"),
            ]
        )

    def test_empty_parameter_file(self) -> None:
        # Call the function with the temporary file
        update_parameter_documentation(self.doc_dict, self.temp_file.name)

        # Read the updated content from the temporary file
        with open(self.temp_file.name, encoding="utf-8") as file:
            updated_content = file.read()

        # Check if the file is still empty
        assert updated_content == ""


class AnnotateParamsTest(unittest.TestCase):
    """Test annotate parameters."""

    def test_arg_parser_valid_arguments(self) -> None:
        test_args = ["annotate_params", "--vehicle-type", "ArduCopter", "--sort", "none", "parameters"]
        with patch("sys.argv", test_args):
            args = arg_parser()
            assert args.vehicle_type == "ArduCopter"
            assert args.sort == "none"
            assert args.target == "parameters"
            assert args.verbose is False
            assert args.max_line_length == 100

    def test_arg_parser_invalid_vehicle_type(self) -> None:
        test_args = ["annotate_params", "--vehicle-type", "InvalidType", "--sort", "none", "parameters"]
        with patch("sys.argv", test_args), pytest.raises(SystemExit):
            arg_parser()

    def test_arg_parser_invalid_sort_option(self) -> None:
        test_args = ["annotate_params", "--vehicle-type", "ArduCopter", "--sort", "invalid", "parameters"]
        with patch("sys.argv", test_args), pytest.raises(SystemExit):
            arg_parser()

    def test_arg_parser_invalid_line_length_option(self) -> None:
        test_args = ["annotate_params", "--vehicle-type", "ArduCopter", "--sort", "none", "-m", "invalid", "parameters"]
        with patch("sys.argv", test_args), pytest.raises(SystemExit):
            arg_parser()


class TestAnnotateParamsExceptionHandling(unittest.TestCase):
    """Test parameter exception handling."""

    @pytest.mark.usefixtures("mock_update", "mock_get_xml_dir", "mock_get_xml_url")
    @patch("builtins.open", new_callable=mock.mock_open)
    def test_main_ioerror(self, mock_file) -> None:
        with patch("ardupilot_methodic_configurator.annotate_params.arg_parser") as mock_arg_parser:
            mock_arg_parser.return_value = mock.Mock(
                vehicle_type="ArduCopter",
                firmware_version="4.0",
                target=".",
                sort="none",
                delete_documentation_annotations=False,
                verbose=False,
            )
            mock_file.side_effect = OSError("Mocked IO Error")

            with pytest.raises(SystemExit) as cm:
                main()

            assert cm.value.code in [1, 2]

    @pytest.mark.usefixtures("mock_update", "mock_get_xml_dir", "mock_get_xml_url")
    @patch("builtins.open", new_callable=mock.mock_open)
    def test_main_oserror(self, mock_file) -> None:
        with patch("ardupilot_methodic_configurator.annotate_params.arg_parser") as mock_arg_parser:
            mock_arg_parser.return_value = mock.Mock(
                vehicle_type="ArduCopter",
                firmware_version="4.0",
                target=".",
                sort="none",
                delete_documentation_annotations=False,
                verbose=False,
            )
            mock_file.side_effect = OSError("Mocked OS Error")

            with pytest.raises(SystemExit) as cm:
                main()

            assert cm.value.code in [1, 2]

    @patch("ardupilot_methodic_configurator.annotate_params.get_xml_url")
    def test_get_xml_url_exception(self, mock_get_xml_url_) -> None:
        mock_get_xml_url_.side_effect = ValueError("Mocked Value Error")
        with pytest.raises(ValueError, match="Vehicle type 'NonExistingVehicle' is not supported."):
            get_xml_url("NonExistingVehicle", "4.0")


if __name__ == "__main__":
    unittest.main()