# Copyright 2014-present PlatformIO <contact@platformio.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
from os import getcwd, makedirs
from os.path import getsize, isdir, isfile, join

from platformio import util, exception
from platformio.commands.boards import cli as cmd_boards
from platformio.commands.init import cli as cmd_init


def validate_pioproject(pioproject_dir):
    pioconf_path = join(pioproject_dir, "platformio.ini")
    assert isfile(pioconf_path) and getsize(pioconf_path) > 0
    assert isdir(join(pioproject_dir, "src")) and isdir(
        join(pioproject_dir, "lib"))


def test_init_default(clirunner, validate_cliresult):
    with clirunner.isolated_filesystem():
        result = clirunner.invoke(cmd_init)
        validate_cliresult(result)
        validate_pioproject(getcwd())


def test_init_ext_folder(clirunner, validate_cliresult):
    with clirunner.isolated_filesystem():
        ext_folder_name = "ext_folder"
        makedirs(ext_folder_name)
        result = clirunner.invoke(cmd_init, ["-d", ext_folder_name])
        validate_cliresult(result)
        validate_pioproject(join(getcwd(), ext_folder_name))


def test_init_duplicated_boards(clirunner, validate_cliresult, tmpdir):
    with tmpdir.as_cwd():
        for _ in range(2):
            result = clirunner.invoke(cmd_init, ["-b", "uno", "-b", "uno"])
            validate_cliresult(result)
            validate_pioproject(str(tmpdir))
        config = util.load_project_config()
        assert set(config.sections()) == set(["env:uno"])


def test_init_ide_without_board(clirunner, validate_cliresult, tmpdir):
    with tmpdir.as_cwd():
        result = clirunner.invoke(cmd_init, ["--ide", "atom"])
        assert result.exit_code == -1
        assert isinstance(result.exception, exception.BoardNotDefined)


def test_init_ide_atom(clirunner, validate_cliresult, tmpdir):
    with tmpdir.as_cwd():
        result = clirunner.invoke(
            cmd_init, ["--ide", "atom", "-b", "uno", "-b", "teensy31"])
        validate_cliresult(result)
        validate_pioproject(str(tmpdir))
        assert all([tmpdir.join(f).check()
                    for f in (".clang_complete", ".gcc-flags.json")])
        assert "arduinoavr" in tmpdir.join(".clang_complete").read()

        # switch to NodeMCU
        result = clirunner.invoke(
            cmd_init, ["--ide", "atom", "-b", "nodemcuv2", "-b", "uno"])
        validate_cliresult(result)
        validate_pioproject(str(tmpdir))
        assert "arduinoespressif" in tmpdir.join(".clang_complete").read()

        # switch to the first board
        result = clirunner.invoke(cmd_init, ["--ide", "atom"])
        validate_cliresult(result)
        validate_pioproject(str(tmpdir))
        assert "arduinoavr" in tmpdir.join(".clang_complete").read()


def test_init_ide_eclipse(clirunner, validate_cliresult):
    with clirunner.isolated_filesystem():
        result = clirunner.invoke(cmd_init, ["-b", "uno", "--ide", "eclipse"])
        validate_cliresult(result)
        validate_pioproject(getcwd())
        assert all([isfile(f) for f in (".cproject", ".project")])


def test_init_special_board(clirunner, validate_cliresult):
    with clirunner.isolated_filesystem():
        result = clirunner.invoke(cmd_init, ["-b", "uno"])
        validate_cliresult(result)
        validate_pioproject(getcwd())

        result = clirunner.invoke(cmd_boards, ["Arduino Uno", "--json-output"])
        validate_cliresult(result)
        boards = json.loads(result.output)

        config = util.load_project_config()
        expected_result = [
            ("platform", str(boards[0]['platform'])),
            ("framework", str(boards[0]['frameworks'][0])), ("board", "uno")
        ]

        assert config.has_section("env:uno")
        assert len(
            set(expected_result).symmetric_difference(
                set(config.items("env:uno")))) == 0


def test_init_enable_auto_uploading(clirunner, validate_cliresult):
    with clirunner.isolated_filesystem():
        result = clirunner.invoke(cmd_init,
                                  ["-b", "uno", "--enable-auto-uploading"])
        validate_cliresult(result)
        validate_pioproject(getcwd())
        config = util.load_project_config()
        expected_result = [
            ("platform", "atmelavr"), ("framework", "arduino"),
            ("board", "uno"), ("targets", "upload")
        ]
        assert config.has_section("env:uno")
        assert len(
            set(expected_result).symmetric_difference(
                set(config.items("env:uno")))) == 0


def test_init_incorrect_board(clirunner):
    result = clirunner.invoke(cmd_init, ["-b", "missed_board"])
    assert result.exit_code == 2
    assert 'Error: Invalid value for "-b" / "--board' in result.output
    assert isinstance(result.exception, SystemExit)
