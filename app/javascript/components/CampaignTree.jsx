import React from "react"
import DeleteConfirmModal from "./DeleteConfirmModal"
import TreeContextMenu from "./TreeContextMenu"
import { statusMessage, treeIsEmpty } from "./treeUtils"
import useTreeState from "./useTreeState"

export default function CampaignTree({ treeUrl }) {
  const {
    suppressRenameBlurRef,
    treeData,
    expanded,
    currentContext,
    hasLoaded,
    loadError,
    contextMenu,
    deletingNode,
    renamingNodeId,
    renamingNodeType,
    renameValue,
    renameError,
    isRenamingSubmitting,
    setContextMenu,
    setDeletingNode,
    setRenameValue,
    toggleFolder,
    navigateTo,
    dispatchTreeRefresh,
    beginRename,
    submitRename,
    cancelRename,
    handleNodeContextMenu,
    handleTreeBackgroundContextMenu,
    handleContextMenuRename,
    handleContextMenuDelete
  } = useTreeState(treeUrl)

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
          newRootAlbumUrl={treeData?.new_root_album_url ?? null}
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
