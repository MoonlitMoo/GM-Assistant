import React, { useEffect, useLayoutEffect, useRef, useState } from "react"
import { createPortal } from "react-dom"

const MENU_VIEWPORT_PADDING = 12
const rootFolderUrlCache = new Map()

function inferredNodeType(node) {
  if (!node) return null
  if (node.type) return node.type
  if (Array.isArray(node.folders) && Array.isArray(node.albums)) return "folder"
  return "album"
}

async function loadNewRootFolderUrl(campaignId, signal) {
  if (!campaignId) return null

  const cachedUrl = rootFolderUrlCache.get(campaignId)
  if (cachedUrl) return cachedUrl

  const response = await fetch(`/campaigns/${encodeURIComponent(campaignId)}/tree`, {
    headers: { Accept: "application/json" },
    signal
  })

  if (!response.ok) throw new Error(`Tree request failed with ${response.status}`)

  const data = await response.json()
  const newRootFolderUrl = data.new_root_folder_url || null

  if (newRootFolderUrl) {
    rootFolderUrlCache.set(campaignId, newRootFolderUrl)
  }

  return newRootFolderUrl
}

function visitInContentFrame(url) {
  if (!url) return

  if (window.Turbo?.visit) {
    window.Turbo.visit(url, { frame: "content-body" })
    return
  }

  window.location.assign(url)
}

export default function TreeContextMenu({ x, y, node, onClose, onRename, onDelete, campaignId }) {
  const menuRef = useRef(null)
  const [position, setPosition] = useState({ x, y })
  const [newRootFolderUrl, setNewRootFolderUrl] = useState(() => rootFolderUrlCache.get(campaignId) || null)

  useEffect(() => {
    setPosition({ x, y })
  }, [x, y])

  useEffect(() => {
    if (node) return

    const cachedUrl = rootFolderUrlCache.get(campaignId) || null
    setNewRootFolderUrl(cachedUrl)

    if (cachedUrl || !campaignId) return

    const controller = new AbortController()

    loadNewRootFolderUrl(campaignId, controller.signal)
      .then((url) => {
        setNewRootFolderUrl(url)
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setNewRootFolderUrl(null)
        }
      })

    return () => {
      controller.abort()
    }
  }, [campaignId, node])

  useEffect(() => {
    function handlePointerDown(event) {
      if (!menuRef.current) return
      if (menuRef.current.contains(event.target)) return
      onClose()
    }

    function handleKeyDown(event) {
      if (event.key === "Escape") {
        onClose()
      }
    }

    document.addEventListener("pointerdown", handlePointerDown)
    document.addEventListener("keydown", handleKeyDown)

    return () => {
      document.removeEventListener("pointerdown", handlePointerDown)
      document.removeEventListener("keydown", handleKeyDown)
    }
  }, [onClose])

  useEffect(() => {
    menuRef.current?.focus()
  }, [])

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
