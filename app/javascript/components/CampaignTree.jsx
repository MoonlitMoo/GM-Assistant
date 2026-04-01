import React, { useEffect, useState } from "react"

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

export default function CampaignTree({ treeUrl }) {
  const [treeData, setTreeData] = useState(null)
  const [expanded, setExpanded] = useState({})
  const [currentContext, setCurrentContext] = useState(currentTreeContext)
  const [hasLoaded, setHasLoaded] = useState(false)
  const [loadError, setLoadError] = useState(false)

  useEffect(() => {
    let cancelled = false
    let activeController = null

    async function loadTree() {
      try {
        activeController?.abort()
        activeController = new AbortController()

        const response = await fetch(treeUrl, { signal: activeController.signal })
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
    window.Turbo.visit(url, { frame: "content-body" })
  }

  function renderFolderEntries(folder) {
    return (
      <>
        {folder.folders.map((childFolder) => {
          const hasChildren = childFolder.folders.length > 0 || childFolder.albums.length > 0
          const isExpanded = !!expanded[childFolder.id]
          const isCurrent = currentContext.path === childFolder.url

          return (
            <li className="tree-folder tree-item" key={`folder-${childFolder.id}`}>
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

                <button
                  type="button"
                  className={`tree-label ${isCurrent ? "is-current" : ""}`.trim()}
                  aria-current={isCurrent ? "page" : undefined}
                  onClick={() => navigateTo(childFolder.url)}
                >
                  {childFolder.name}
                </button>
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
            <li className="tree-album tree-item" key={`album-${album.id}`}>
              <div className="tree-row">
                <span className="tree-spacer" aria-hidden="true" />
                <button
                  type="button"
                  className={`tree-label ${isCurrent ? "is-current" : ""}`.trim()}
                  aria-current={isCurrent ? "page" : undefined}
                  onClick={() => navigateTo(album.url)}
                >
                  <i>{album.name}</i>
                </button>
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
    return statusMessage("Couldn’t load the tree", "Refresh the page and try again.", "tree-status--error")
  }

  if (!treeData || treeIsEmpty(treeData)) {
    return statusMessage(
      "Campaign library is empty",
      "Create a folder or album to start organizing this campaign.",
      "tree-status--empty"
    )
  }

  return (
    <nav className="tree-nav" aria-label="Campaign tree">
      <ul className="tree-list tree-list--root">
        {renderFolderEntries(treeData)}
      </ul>
    </nav>
  )
}
