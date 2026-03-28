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

export default function CampaignTree({ treeUrl }) {
  const [treeData, setTreeData] = useState(null)
  const [expanded, setExpanded] = useState({})

  useEffect(() => {
    let cancelled = false

    async function loadTree() {
      const response = await fetch(treeUrl)
      const data = await response.json()

      if (cancelled) return

      setTreeData(data)
      setExpanded(loadExpandedState(data.campaignId))
    }

    function refreshTree() {
      loadTree()
    }

    loadTree()
    document.addEventListener("tree:refresh", refreshTree)

    return () => {
      cancelled = true
      document.removeEventListener("tree:refresh", refreshTree)
    }
  }, [treeUrl])

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

  function renderFolder(folder) {
    return (
      <>
        {folder.folders.map((childFolder) => (
          <li className="tree-folder" key={`folder-${childFolder.id}`}>
            <span
              className="tree-toggle"
              onClick={() => toggleFolder(childFolder.id)}
            >
              {expanded[childFolder.id] ? "▾" : "▸"}
            </span>
            <span
              className="tree-label"
              onClick={() => navigateTo(childFolder.url)}
            >
              {childFolder.name}
            </span>

            {expanded[childFolder.id] ? <ul>{renderFolder(childFolder)}</ul> : null}
          </li>
        ))}

        {folder.albums.map((album) => (
          <li className="tree-album" key={`album-${album.id}`}>
            <span
              className="tree-label"
              onClick={() => navigateTo(album.url)}
            >
              <i>{album.name}</i>
            </span>
          </li>
        ))}
      </>
    )
  }

  if (treeData === null) {
    return <div>Loading...</div>
  }

  return <ul>{renderFolder(treeData)}</ul>
}
