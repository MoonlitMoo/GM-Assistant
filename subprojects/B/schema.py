# schema.py
TREE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://example.com/image-tree.schema.json",
    "title": "Image Tree File",
    "type": "object",
    "properties": {
        "version": {
            "type": "string",
            "enum": ["v1"]
        },
        "tree": {
            "type": "object",
            "additionalProperties": { "$ref": "#/$defs/node" }
        }
    },
    "required": ["version", "tree"],
    "additionalProperties": False,

    "$defs": {
        "node": {
            "anyOf": [
                { "$ref": "#/$defs/folder" },
                { "$ref": "#/$defs/album" }
            ]
        },
        "folder": {
            "type": "object",
            "description": "A folder mapping names → nodes",
            "additionalProperties": { "$ref": "#/$defs/node" }
        },
        "album": {
            "type": "object",
            "description": "A leaf that contains images",
            "properties": {
                "images": {
                    "type": "array",
                    "items": { "$ref": "#/$defs/image" }
                }
            },
            "required": ["images"],
            "additionalProperties": False
        },
        "image": {
            "type": "object",
            "properties": {
                "path":  { "type": "string", "minLength": 1 },
                "label": { "type": "string", "minLength": 1 }
            },
            "required": ["path", "label"],
            "additionalProperties": False
        }
    }
}
