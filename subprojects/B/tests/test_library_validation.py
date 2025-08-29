import json

import pytest

from ui.library_widget import LibraryWidget

@pytest.fixture
def widget(qtbot, library_file):
    # Init the Qt widget under test
    w = LibraryWidget()
    qtbot.addWidget(w)  # ensures cleanup and proper event handling
    return w

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

def test_load_library_fails_extra_key(widget, library_dict):
    """Check we fail on an unexpected key at the root."""
    library_dict["extra"] = 1
    with pytest.raises(ValueError):
        widget._validate_library(library_dict)


def test_load_library_fails_missing_version(widget, library_dict):
    """Check we fail if 'version' is missing."""
    del library_dict["version"]
    with pytest.raises(ValueError):
        widget._validate_library(library_dict)


def test_load_library_fails_invalid_image(widget, library_dict):
    """Check we fail if image entry misses 'label'."""
    library_dict["tree"]["Session 1"]["NPCs"]["images"][0].pop("label")
    with pytest.raises(ValueError):
        widget._validate_library(library_dict)


def test_load_library_success(widget, library_file):
    """Check a valid file loads successfully."""
    result = widget._load_library(library_file)
    assert result["version"] == "v1"
    assert "tree" in result
