import json
import pytest

from ui.library_items import (
    Image,
    Node,
    Leaf,
    validate_library_string,
    create_tree_from_dict,
    export_tree_to_dict,
)


# ---------- Fixtures ----------

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
                },
            },
            "Session 2": {}
        },
    }


@pytest.fixture()
def library_text(library_dict):
    return json.dumps(library_dict)


# ---------- Schema validation tests ----------

def test_validate_fails_extra_key(library_dict):
    library_dict["extra"] = 1
    with pytest.raises(ValueError):
        validate_library_string(library_dict)


def test_validate_fails_missing_version(library_dict):
    del library_dict["version"]
    with pytest.raises(ValueError):
        validate_library_string(library_dict)


def test_validate_fails_invalid_image_missing_label(library_dict):
    library_dict["tree"]["Session 1"]["NPCs"]["images"][0].pop("label")
    with pytest.raises(ValueError):
        validate_library_string(library_dict)


def test_validate_accepts_valid_dict(library_dict):
    # Should not raise
    validate_library_string(library_dict)


# ---------- Tree build / export tests ----------

def test_create_tree_builds_structure(library_dict):
    # Should not raise and should build a root with children
    root = create_tree_from_dict(library_dict)
    # If no exception, basic build passed. We’ll do structural checks via export.


def test_export_roundtrip_is_valid(library_dict):
    # Build → Export → Validate
    root = create_tree_from_dict(library_dict)  # build the tree (constructs internal objects)
    exported = export_tree_to_dict(root)

    # Validate the exported dict against the schema (export already validates, but double-check)
    validate_library_string(exported)

    # Spot-check key structure
    assert exported["version"] == "v1"
    assert "tree" in exported
    assert "Session 1" in exported["tree"]
    assert "NPCs" in exported["tree"]["Session 1"]
    assert "Locations" in exported["tree"]["Session 1"]
    assert "images" in exported["tree"]["Session 1"]["NPCs"]
    assert "images" in exported["tree"]["Session 1"]["Locations"]


def test_node_children_iter_and_mutation():
    root = Node("root")
    a = Node("A", parent=root)
    b = Leaf("B", parent=root)

    root.add_child(a)
    root.add_child(b)
    # No duplicates
    root.add_child(a)

    labels = [child.label for child in root]
    assert labels == ["A", "B"]

    root.remove_child(a)
    labels_after = [child.label for child in root]
    assert labels_after == ["B"]


def test_leaf_items_iter_and_mutation():
    album = Leaf("Album", parent=Node("parent"))
    img1 = Image(label="L1", path="p1")
    img2 = Image(label="L2", path="p2")

    album.add_item(img1)
    album.add_item(img2)
    # No duplicates
    album.add_item(img1)

    labels = [img.label for img in album]
    assert labels == ["L1", "L2"]

    album.remove_item(img1)
    labels_after = [img.label for img in album]
    assert labels_after == ["L2"]
