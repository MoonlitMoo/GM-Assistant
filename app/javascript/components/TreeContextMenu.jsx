import React, { useEffect, useLayoutEffect, useRef, useState } from "react"
import { createPortal } from "react-dom"
import usePortalDismiss from "../hooks/usePortalDismiss"
import { inferredNodeType } from "../lib/tree_utils"

const MENU_VIEWPORT_PADDING = 12

function visitInContentFrame(url) {
  if (!url) return

  if (window.Turbo?.visit) {
    window.Turbo.visit(url, { frame: "content-body" })
    return
  }

  window.location.assign(url)
}

export default function TreeContextMenu({ x, y, node, onClose, onRename, onDelete, newRootFolderUrl }) {
  const menuRef = useRef(null)
  const [position, setPosition] = useState({ x, y })

  useEffect(() => {
    setPosition({ x, y })
  }, [x, y])

  usePortalDismiss({ containerRef: menuRef, onClose })

  useEffect(() => {
    function handlePointerDown(event) {
      if (!menuRef.current) return
      if (menuRef.current.contains(event.target)) return
      onClose()
    }

    document.addEventListener("pointerdown", handlePointerDown)

    return () => {
      document.removeEventListener("pointerdown", handlePointerDown)
    }
  }, [onClose])

  useLayoutEffect(() => {
    if (!menuRef.current) return

    const rect = menuRef.current.getBoundingClientRect()
    const nextPosition = {
      x: Math.max(MENU_VIEWPORT_PADDING, Math.min(x, window.innerWidth - rect.width - MENU_VIEWPORT_PADDING)),
      y: Math.max(MENU_VIEWPORT_PADDING, Math.min(y, window.innerHeight - rect.height - MENU_VIEWPORT_PADDING))
    }

    setPosition((currentPosition) => {
      if (currentPosition.x === nextPosition.x && currentPosition.y === nextPosition.y) {
        return currentPosition
      }

      return nextPosition
    })
  }, [x, y, node, newRootFolderUrl])

  function handleVisit(url) {
    onClose()
    visitInContentFrame(url)
  }

  function handleRename() {
    onClose()
    onRename(node)
  }

  function handleDelete() {
    onClose()
    onDelete(node)
  }

  const nodeType = inferredNodeType(node)
  let items = []

  if (!node) {
    items = [
      {
        label: "New Folder",
        onSelect: () => handleVisit(newRootFolderUrl),
        disabled: !newRootFolderUrl
      }
    ]
  } else if (nodeType === "folder") {
    items = [
      { label: "New Subfolder", onSelect: () => handleVisit(node.new_subfolder_url) },
      { label: "New Album", onSelect: () => handleVisit(node.new_album_url) },
      { label: "Rename", onSelect: handleRename },
      { label: "Edit", onSelect: () => handleVisit(node.edit_url) },
      { label: "Delete", onSelect: handleDelete, danger: true }
    ]
  } else if (nodeType === "album") {
    items = [
      { label: "Rename", onSelect: handleRename },
      { label: "Edit", onSelect: () => handleVisit(node.edit_url) },
      { label: "Delete", onSelect: handleDelete, danger: true }
    ]
  }

  if (typeof document === "undefined" || !document.body || items.length === 0) {
    return null
  }

  return createPortal(
    <div
      ref={menuRef}
      className="tree-context-menu"
      role="menu"
      tabIndex={-1}
      aria-label={node ? `${node.name} menu` : "Campaign tree menu"}
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`
      }}
    >
      <ul className="tree-context-menu__list">
        {items.map((item) => (
          <li key={item.label} className="tree-context-menu__item">
            <button
              type="button"
              role="menuitem"
              disabled={item.disabled}
              className={`tree-context-menu__button ${item.danger ? "tree-context-menu__button--danger" : ""}`.trim()}
              onClick={item.onSelect}
            >
              {item.label}
            </button>
          </li>
        ))}
      </ul>
    </div>,
    document.body
  )
}
