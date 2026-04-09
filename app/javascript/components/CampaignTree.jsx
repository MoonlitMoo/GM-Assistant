import React, { useEffect, useRef, useState } from "react"
import DeleteConfirmModal from "./DeleteConfirmModal"
import TreeContextMenu from "./TreeContextMenu"
import { csrfToken, inferredNodeType } from "../lib/tree_utils"

function storageKeyFor(campaignId) {
  return `campaign-tree:${campaignId}:expanded`
}

function loadExpandedState(campaignId) {
  try {
    return JSON.parse(sessionStorage.getItem(storageKeyFor(campaignId)) || "{}")
  } catch {
    return {}
  }
}

function saveExpandedState(campaignId, expanded) {
  sessionStorage.setItem(storageKeyFor(campaignId), JSON.stringify(expanded))
}

function readBreadcrumbUrls() {
  const payloadElement =
    document.querySelector("turbo-frame#content-body [data-breadcrumbs-payload]") ||
    document.querySelector("[data-breadcrumbs-payload]")

  if (!payloadElement) return []

  try {
    return JSON.parse(payloadElement.dataset.breadcrumbsPayload || "[]")
      .map(([, url]) => url)
      .filter(Boolean)
  } catch {
    return []
  }
}

function currentTreeContext() {
  return {
    path: window.location.pathname,
    fullPath: `${window.location.pathname}${window.location.search}`,
    breadcrumbUrls: readBreadcrumbUrls()
  }
}

function treeIsEmpty(folder) {
  return folder.folders.length === 0 && folder.albums.length === 0
}

function findExpandedPath(folder, targetUrl) {
  if (!targetUrl) return null
  if (folder.url === targetUrl) return []

  for (const childFolder of folder.folders) {
    if (childFolder.url === targetUrl) return [childFolder.id]

    const descendantPath = findExpandedPath(childFolder, targetUrl)
    if (descendantPath !== null) {
      return [childFolder.id, ...descendantPath]
    }
  }

  for (const album of folder.albums) {
    if (album.url === targetUrl) return []
  }

  return null
}

function requiredExpandedState(folder, context) {
  const candidateUrls = [context.path, ...[...context.breadcrumbUrls].reverse()]

  for (const url of candidateUrls) {
    const expandedPath = findExpandedPath(folder, url)
    if (expandedPath !== null) {
      return Object.fromEntries(expandedPath.map((folderId) => [folderId, true]))
    }
  }

  return {}
}

function expandedStatesMatch(left, right) {
  const leftEntries = Object.entries(left)
  const rightEntries = Object.entries(right)

  if (leftEntries.length !== rightEntries.length) return false

  return leftEntries.every(([key, value]) => right[key] === value)
}

function statusMessage(title, body, modifier = "") {
  return (
    <div className={`tree-status ${modifier}`.trim()}>
      <p className="tree-status__title">{title}</p>
      {body ? <p className="tree-status__body">{body}</p> : null}
    </div>
  )
}

function renamePayloadFor(nodeType, name) {
  if (nodeType === "folder") return { folder: { name } }
  return { album: { name } }
}

function renameErrorMessage(responseBody, fallbackMessage) {
  if (Array.isArray(responseBody?.errors) && responseBody.errors.length > 0) {
    return responseBody.errors.join(", ")
  }

  return fallbackMessage
}

export default function CampaignTree({ treeUrl }) {
  const suppressRenameBlurRef = useRef(false)
  const [treeData, setTreeData] = useState(null)
  const [expanded, setExpanded] = useState({})
  const [currentContext, setCurrentContext] = useState(currentTreeContext)
  const [hasLoaded, setHasLoaded] = useState(false)
  const [loadError, setLoadError] = useState(false)
  const [contextMenu, setContextMenu] = useState(null)
  const [deletingNode, setDeletingNode] = useState(null)
  const [renamingNodeId, setRenamingNodeId] = useState(null)
  const [renamingNodeType, setRenamingNodeType] = useState(null)
  const [renameValue, setRenameValue] = useState("")
  const [renameError, setRenameError] = useState(null)
  const [isRenamingSubmitting, setIsRenamingSubmitting] = useState(false)

  useEffect(() => {
    let cancelled = false
    let activeController = null

    async function loadTree() {
      try {
        activeController?.abort()
        activeController = new AbortController()

        const response = await fetch(treeUrl, {
          headers: { Accept: "application/json" },
          cache: "no-store",
          signal: activeController.signal
        })
        if (!response.ok) throw new Error(`Tree request failed with ${response.status}`)

        const data = await response.json()
        if (cancelled) return

        setTreeData(data)
        setExpanded(loadExpandedState(data.campaignId))
        setLoadError(false)
        setHasLoaded(true)
      } catch {
        if (activeController?.signal.aborted || cancelled) return

        if (cancelled) return

        setLoadError(true)
        setHasLoaded(true)
      }
    }

    function refreshTree() {
      setContextMenu(null)
      loadTree()
    }

    loadTree()
    document.addEventListener("tree:refresh", refreshTree)

    return () => {
      cancelled = true
      activeController?.abort()
      document.removeEventListener("tree:refresh", refreshTree)
    }
  }, [treeUrl])

  useEffect(() => {
    function syncCurrentContext(event) {
      if (event?.target?.id && event.target.id !== "content-body") return
      setCurrentContext(currentTreeContext())
    }

    document.addEventListener("turbo:frame-load", syncCurrentContext)
    document.addEventListener("turbo:load", syncCurrentContext)
    window.addEventListener("popstate", syncCurrentContext)

    return () => {
      document.removeEventListener("turbo:frame-load", syncCurrentContext)
      document.removeEventListener("turbo:load", syncCurrentContext)
      window.removeEventListener("popstate", syncCurrentContext)
    }
  }, [])

  useEffect(() => {
    if (!treeData) return

    const requiredExpanded = requiredExpandedState(treeData, currentContext)
    if (Object.keys(requiredExpanded).length === 0) return

    setExpanded((currentExpanded) => {
      const nextExpanded = {
        ...currentExpanded,
        ...requiredExpanded
      }

      if (expandedStatesMatch(currentExpanded, nextExpanded)) return currentExpanded

      saveExpandedState(treeData.campaignId, nextExpanded)
      return nextExpanded
    })
  }, [treeData, currentContext])

  function toggleFolder(folderId) {
    if (!treeData) return

    setExpanded((currentExpanded) => {
      const nextExpanded = {
        ...currentExpanded,
        [folderId]: !currentExpanded[folderId]
      }

      saveExpandedState(treeData.campaignId, nextExpanded)
      return nextExpanded
    })
  }

  function navigateTo(url) {
    setContextMenu(null)
    window.Turbo.visit(url, { frame: "content-body" })
  }

  function dispatchTreeRefresh() {
    document.dispatchEvent(new CustomEvent("tree:refresh"))
  }

  function pageDependsOnNode(node) {
    if (!node?.url) return false

    return currentContext.path === node.url || currentContext.breadcrumbUrls.includes(node.url)
  }

  function refreshCurrentViewForRenamedNode(node, responseBody) {
    if (!pageDependsOnNode(node)) return

    const refreshUrl = currentContext.path === node.url
      ? (responseBody?.url || node.url)
      : (currentContext.fullPath || currentContext.path)

    window.Turbo.visit(refreshUrl, { frame: "content-body" })
  }

  function beginRename(node, nodeType) {
    suppressRenameBlurRef.current = false
    setContextMenu(null)
    setRenameError(null)
    setRenamingNodeId(node.id)
    setRenamingNodeType(nodeType)
    setRenameValue(node.name)
    setIsRenamingSubmitting(false)
  }

  function clearRenameState() {
    setRenamingNodeId(null)
    setRenamingNodeType(null)
    setRenameValue("")
    setIsRenamingSubmitting(false)
  }

  async function submitRename(node, nodeType) {
    if (isRenamingSubmitting) return

    setRenameError(null)
    setContextMenu(null)
    setIsRenamingSubmitting(true)

    try {
      const response = await fetch(node.url, {
        method: "PATCH",
        headers: {
          "Accept": "application/json",
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfToken(),
          "X-Requested-With": "XMLHttpRequest"
        },
        credentials: "same-origin",
        body: JSON.stringify(renamePayloadFor(nodeType, renameValue))
      })

      const responseBody = await response.json().catch(() => null)

      if (!response.ok) {
        setRenameError({
          nodeId: node.id,
          nodeType,
          message: renameErrorMessage(responseBody, "Couldn’t rename this item.")
        })
        clearRenameState()
        return
      }

      dispatchTreeRefresh()
      refreshCurrentViewForRenamedNode(node, responseBody)
      clearRenameState()
    } catch {
      setRenameError({
        nodeId: node.id,
        nodeType,
        message: "Couldn’t rename this item."
      })
      clearRenameState()
    }
  }

  function cancelRename() {
    setRenameError(null)
    clearRenameState()
  }

  function handleNodeContextMenu(event, node) {
    event.preventDefault()
    event.stopPropagation()
    setContextMenu({
      x: event.clientX,
      y: event.clientY,
      node
    })
  }

  function handleTreeBackgroundContextMenu(event) {
    if (event.target.closest(".tree-item")) return

    event.preventDefault()
    setContextMenu({
      x: event.clientX,
      y: event.clientY,
      node: null
    })
  }

  function handleContextMenuRename(node) {
    beginRename(node, inferredNodeType(node))
    setContextMenu(null)
  }

  function handleContextMenuDelete(node) {
    setDeletingNode(node)
    setContextMenu(null)
  }

  function renderTreeLabel(node, nodeType, isCurrent) {
    const isRenaming = renamingNodeId === node.id && renamingNodeType === nodeType
    const inlineError = renameError?.nodeId === node.id && renameError?.nodeType === nodeType ? renameError.message : null
    const labelClasses = `tree-label ${isCurrent ? "is-current" : ""}`.trim()

    return (
      <div className="tree-row__content">
        {isRenaming ? (
          <input
            type="text"
            className={`tree-rename-input ${nodeType === "album" ? "tree-rename-input--album" : ""}`.trim()}
            value={renameValue}
            autoFocus
            disabled={isRenamingSubmitting}
            onChange={(event) => setRenameValue(event.currentTarget.value)}
            onBlur={() => {
              if (suppressRenameBlurRef.current) {
                suppressRenameBlurRef.current = false
                return
              }

              submitRename(node, nodeType)
            }}
            onFocus={(event) => event.currentTarget.select()}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault()
                submitRename(node, nodeType)
              } else if (event.key === "Escape") {
                event.preventDefault()
                suppressRenameBlurRef.current = true
                cancelRename()
              }
            }}
          />
        ) : (
          <button
            type="button"
            className={labelClasses}
            aria-current={isCurrent ? "page" : undefined}
            onClick={() => navigateTo(node.url)}
            onKeyDown={(event) => {
              if (event.key === "F2") {
                event.preventDefault()
                beginRename(node, nodeType)
              }
            }}
          >
            {nodeType === "album" ? <i>{node.name}</i> : node.name}
          </button>
        )}

        {inlineError ? <p className="tree-inline-error">{inlineError}</p> : null}
      </div>
    )
  }

  function renderFolderEntries(folder) {
    return (
      <>
        {folder.folders.map((childFolder) => {
          const hasChildren = childFolder.folders.length > 0 || childFolder.albums.length > 0
          const isExpanded = !!expanded[childFolder.id]
          const isCurrent = currentContext.path === childFolder.url

          return (
            <li
              className="tree-folder tree-item"
              key={`folder-${childFolder.id}`}
              onContextMenu={(event) => handleNodeContextMenu(event, childFolder)}
            >
              <div className="tree-row">
                {hasChildren ? (
                  <button
                    type="button"
                    className="tree-toggle"
                    aria-expanded={isExpanded}
                    aria-label={`${isExpanded ? "Collapse" : "Expand"} ${childFolder.name}`}
                    onClick={() => toggleFolder(childFolder.id)}
                  >
                    {isExpanded ? "▾" : "▸"}
                  </button>
                ) : (
                  <span className="tree-spacer" aria-hidden="true" />
                )}

                {renderTreeLabel(childFolder, "folder", isCurrent)}
              </div>

              {hasChildren && isExpanded ? (
                <ul className="tree-list">
                  {renderFolderEntries(childFolder)}
                </ul>
              ) : null}
            </li>
          )
        })}

        {folder.albums.map((album) => {
          const isCurrent = currentContext.path === album.url

          return (
            <li
              className="tree-album tree-item"
              key={`album-${album.id}`}
              onContextMenu={(event) => handleNodeContextMenu(event, album)}
            >
              <div className="tree-row">
                <span className="tree-spacer" aria-hidden="true" />
                {renderTreeLabel(album, "album", isCurrent)}
              </div>
            </li>
          )
        })}
      </>
    )
  }

  if (!hasLoaded && treeData === null) {
    return statusMessage("Loading campaign tree…", "Gathering folders and albums for this campaign.")
  }

  if (loadError && treeData === null) {
    return (
      <div className="tree-surface" onContextMenu={handleTreeBackgroundContextMenu}>
        {statusMessage("Couldn’t load the tree", "Refresh the page and try again.", "tree-status--error")}
      </div>
    )
  }

  const overlays = (
    <>
      {contextMenu && (
        <TreeContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          node={contextMenu.node}
          newRootFolderUrl={treeData?.new_root_folder_url ?? null}
          onClose={() => setContextMenu(null)}
          onRename={handleContextMenuRename}
          onDelete={handleContextMenuDelete}
        />
      )}

      {deletingNode && (
        <DeleteConfirmModal
          node={deletingNode}
          onClose={() => setDeletingNode(null)}
          onDeleted={() => {
            dispatchTreeRefresh()
            setDeletingNode(null)
          }}
        />
      )}
    </>
  )

  const content = !treeData || treeIsEmpty(treeData)
    ? statusMessage(
        "Campaign library is empty",
        "Create a folder or album to start organizing this campaign.",
        "tree-status--empty"
      )
    : (
        <nav className="tree-nav" aria-label="Campaign tree">
          <ul className="tree-list tree-list--root">
            {renderFolderEntries(treeData)}
          </ul>
        </nav>
      )

  return (
    <div className="tree-surface" onContextMenu={handleTreeBackgroundContextMenu}>
      {content}
      {overlays}
    </div>
  )
}
