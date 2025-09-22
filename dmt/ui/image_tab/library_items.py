from __future__ import annotations
from typing import Dict, Any
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidgetItem

# ---- Roles & column setup ----------------------------------------------------
COL_LABEL = 0  # single-column tree; label stored as text(0)

ROLE_KIND = Qt.ItemDataRole.UserRole + 1  # "Folder" | "Album" | "Image"
ROLE_ID = Qt.ItemDataRole.UserRole + 2  # DB id: int
ROLE_POS = Qt.ItemDataRole.UserRole + 3  # display position within parent: int
ROLE_PAYLOAD = Qt.ItemDataRole.UserRole + 4  # optional payload (dict)


# ---- Tree Items --------------------------------------------------------------
class FolderItem(QTreeWidgetItem):
    """ Folder — may contain FolderItem or AlbumItem. """

    def __init__(self, db_id: int, label: str, position: int):
        super().__init__([label])
        self.setData(COL_LABEL, ROLE_KIND, "Folder")
        self.setData(COL_LABEL, ROLE_ID, db_id)
        self.setData(COL_LABEL, ROLE_POS, position)
        self.setFlags(self.flags() | Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)

    @property
    def id(self) -> int:
        return int(self.data(COL_LABEL, ROLE_ID)) if self.data(COL_LABEL, ROLE_ID) else None

    @property
    def label(self) -> str:
        return self.text(COL_LABEL)

    @label.setter
    def label(self, v: str) -> None:
        self.setText(COL_LABEL, v)


class AlbumItem(QTreeWidgetItem):
    """ Album (Collection) — may contain ImageItem children. """

    def __init__(self, db_id: int, label: str, position: int):
        super().__init__([label])
        self.setData(COL_LABEL, ROLE_KIND, "Album")
        self.setData(COL_LABEL, ROLE_ID, db_id)
        self.setData(COL_LABEL, ROLE_POS, position)
        self.setFlags(self.flags() | Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)

    @property
    def id(self) -> int:
        return int(self.data(COL_LABEL, ROLE_ID))

    @property
    def label(self) -> str:
        return self.text(COL_LABEL)

    @label.setter
    def label(self, v: str) -> None:
        self.setText(COL_LABEL, v)


class ImageItem(QTreeWidgetItem):
    """ Image item. Stores {'id', 'caption'} payload; bytes live in DB. """

    def __init__(self, db_id: int, caption: str, position: int):
        super().__init__([caption or f"image:{db_id}"])
        self.setData(COL_LABEL, ROLE_KIND, "Image")
        self.setData(COL_LABEL, ROLE_ID, db_id)
        self.setData(COL_LABEL, ROLE_POS, position)
        self.setData(COL_LABEL, ROLE_PAYLOAD, {"id": db_id, "caption": caption})
        self.setFlags((self.flags() | Qt.ItemIsDragEnabled) & ~Qt.ItemIsDropEnabled)

    @property
    def id(self) -> int:
        return int(self.data(COL_LABEL, ROLE_ID))

    @property
    def label(self) -> str:
        return self.text(COL_LABEL)

    @property
    def caption(self) -> str:
        payload: Dict[str, Any] = self.data(COL_LABEL, ROLE_PAYLOAD) or {}
        return payload.get("caption", "")

    @caption.setter
    def caption(self, v: str) -> None:
        self.setText(COL_LABEL, v)
        payload: Dict[str, Any] = dict(self.data(COL_LABEL, ROLE_PAYLOAD) or {})
        payload["caption"] = v
        self.setData(COL_LABEL, ROLE_PAYLOAD, payload)
