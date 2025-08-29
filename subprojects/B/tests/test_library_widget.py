import json

import pytest
from jsonschema.exceptions import ValidationError

from ui.library_widget import LibraryWidget

@pytest.fixture()
def library_dict():
    return {
        "version": "v1",
        "tree": {
            "Session 1": {
                "NPCs": {
                    "images": [
                        {"path": "images/npc1.png", "label": "Guard"}
                    ]
                },
                "Locations": {
                    "images": [
                        {"path": "images/town.png", "label": "Town Square"}
                    ]
                }
            }
        }
    }

@pytest.fixture()
def library_file(tmp_path, library_dict):
    file = tmp_path / "lib.json"
    with open(file, 'w') as f:
        f.write(json.dumps(library_dict))
    return file

def test_load_library(library_file):
    """ Check we can load a valid file. """
    LibraryWidget._load_library(None, library_file)

def test_load_library_fails_extra_key(library_dict, library_file):
    """Check we fail on an unexpected key at the root."""
    library_dict["extra"] = 1
    with open(library_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(library_dict))
    with pytest.raises(ValueError):
        LibraryWidget._load_library(None, library_file)


def test_load_library_fails_missing_version(library_dict, library_file):
    """Check we fail if 'version' is missing."""
    del library_dict["version"]
    with open(library_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(library_dict))
    with pytest.raises(ValueError):
        LibraryWidget._load_library(None, library_file)


def test_load_library_fails_invalid_image(library_dict, library_file):
    """Check we fail if image entry misses 'label'."""
    library_dict["tree"]["Session 1"]["NPCs"]["images"][0].pop("label")
    with open(library_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(library_dict))
    with pytest.raises(ValueError):
        LibraryWidget._load_library(None, library_file)


def test_load_library_success(library_dict, library_file):
    """Check a valid file loads successfully."""
    with open(library_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(library_dict))
    result = LibraryWidget._load_library(None, library_file)
    assert result["version"] == "v1"
    assert "tree" in result
