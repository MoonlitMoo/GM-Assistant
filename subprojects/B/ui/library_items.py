from typing import List

from jsonschema.validators import Draft202012Validator
from pydantic import BaseModel

from schema import TREE_SCHEMA


class Image(BaseModel):
    """ An image item in the library. """
    label: str
    path: str


class Node:
    """ Defines a node in the library tree, corresponding to a folder.
    Parents are nodes or None if root. Children are nodes or leaves.
    """

    def __init__(self, label: str, parent=None):
        self.label = label
        self.parent: Node = parent
        self.children: List[Node | Leaf] = []

    def add_child(self, child):
        if child not in self.children:
            child.parent = self
            self.children.append(child)

    def remove_child(self, child):
        if child in self.children:
            child.parent = None
            self.children.remove(child)

    def __iter__(self):
        return iter(self.children)


class Leaf:
    """ Defines a leaf in the library tree, corresponding to an album.
    Parents are a node, contains a list of image items.
    """

    def __init__(self, label: str, parent: Node):
        self.label = label
        self.parent = parent
        self._items: List[Image] = []

    def add_item(self, item: Image):
        """ Add image to the album, ensuring we don't duplicate somehow. """
        if item not in self._items:
            self._items.append(item)

    def remove_item(self, item: Image):
        """ Remove image from the album, making sure it is in there. """
        if item in self._items:
            self._items.remove(item)

    def __iter__(self):
        return iter(self._items)


def validate_library_string(data: dict):
    """ Validates the given dict to follow the library tree schema.

    Parameters
    ----------
    data : str or dict
        The json text of the library.

    Raises
    ------
    ValueError
        if invalid schema detected.
    """
    validator = Draft202012Validator(TREE_SCHEMA)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        lines = []
        for e in errors:
            loc = "/".join(map(str, e.path)) or "<root>"
            lines.append(f"- at {loc}: {e.message}")
        raise ValueError("Invalid image tree:\n" + "\n".join(lines))


def create_tree_from_dict(library: dict):
    """ Create a tree from a JSON file"""
    validate_library_string(library)

    root = Node("root")

    def add_node(parent: Node, label: str, node):
        # Album: object with 'images' array
        if isinstance(node, dict) and "images" in node and isinstance(node["images"], list):
            item = Leaf(label=label, parent=parent)
            parent.add_child(item)
            # Add images as children
            for i, img in enumerate(node["images"]):
                img_item = Image(**img)
                item.add_item(img_item)
            return item

        # Folder: object mapping names → nodes
        if isinstance(node, dict):
            item = Node(label=label, parent=parent)
            parent.add_child(item)
            for child_name, child_node in node.items():
                add_node(item, child_name, child_node)
            return item

    for name, node in library["tree"].items():
        add_node(root, name, library["tree"][name])

    return root


def export_tree_to_dict(root: Node):
    """ Iterates through the tree to build the final schema. """

    def export_leaf(leaf: Leaf):
        """ Returns the label: data for the leaf object. """
        img_list = []
        for img in leaf:
            img_list.append(img.model_dump())
        return leaf.label, {"images": img_list}

    def export_node(node: Node):
        """ Returns a dictionary of label: data for the node object. """
        children_dict = {}
        for child in node:
            if isinstance(child, Node):
                label, data = export_node(child)
            else:
                label, data = export_leaf(child)
            children_dict[label] = data
        return node.label, children_dict

    _, root_data = export_node(root)
    export_dict = {
        "version": "v1",
        "tree": root_data
    }

    validate_library_string(export_dict)
    return export_dict
