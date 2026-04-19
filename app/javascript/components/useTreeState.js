import { useEffect, useRef, useState } from "react"
import {
  csrfToken,
  currentTreeContext,
  expandedStatesMatch,
  inferredNodeType,
  loadExpandedState,
  renameErrorMessage,
  renamePayloadFor,
  requiredExpandedState,
  saveExpandedState
} from "./treeUtils"

export default function useTreeState(treeUrl) {
  const suppressRenameBlurRef = useRef(false)
  const pendingDeleteRef = useRef(null)
  const [treeData, setTreeData] = useState(null)
  const [expanded, setExpanded] = useState({})
  const [currentContext, setCurrentContext] = useState(currentTreeContext)
  const [hasLoaded, setHasLoaded] = useState(false)
  const [loadError, setLoadError] = useState(false)
  const [contextMenu, setContextMenu] = useState(null)
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

  function deleteRequestId() {
    if (window.crypto?.randomUUID) {
      return window.crypto.randomUUID()
    }

    return `delete-${Date.now()}-${Math.round(Math.random() * 1e6)}`
  }

  function deleteDescription(node, nodeType) {
    if (nodeType === "folder") {
      return [
        `${Number(node?.child_folder_count || 0)} subfolder${Number(node?.child_folder_count || 0) === 1 ? "" : "s"}`,
        `${Number(node?.album_count || 0)} album${Number(node?.album_count || 0) === 1 ? "" : "s"}`,
        `${Number(node?.image_count || 0)} image${Number(node?.image_count || 0) === 1 ? "" : "s"}`,
        "This cannot be undone."
      ]
    }

    return [
      `${Number(node?.image_count || 0)} image${Number(node?.image_count || 0) === 1 ? "" : "s"} will be deleted.`,
      "This cannot be undone."
    ]
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

  function redirectCurrentViewForDeletedNode(node, responseBody) {
    if (!pageDependsOnNode(node)) return

    const redirectUrl = responseBody?.redirect_url
    if (!redirectUrl) return

    window.Turbo.visit(redirectUrl, { frame: "content-body" })
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
    const nodeType = inferredNodeType(node)
    const requestId = deleteRequestId()

    pendingDeleteRef.current = { requestId, node }
    setContextMenu(null)

    document.dispatchEvent(new CustomEvent("record-delete:open", {
      detail: {
        requestId,
        title: nodeType === "folder" ? "Delete Folder" : "Delete Album",
        name: node.name,
        descriptionLines: deleteDescription(node, nodeType),
        deleteUrl: node.url,
        successMode: "event"
      }
    }))
  }

  useEffect(() => {
    function handleDeleteSuccess(event) {
      const pendingDelete = pendingDeleteRef.current
      if (!pendingDelete) return
      if (event.detail?.requestId !== pendingDelete.requestId) return

      pendingDeleteRef.current = null
      dispatchTreeRefresh()
      redirectCurrentViewForDeletedNode(pendingDelete.node, event.detail?.responseBody)
    }

    function handleDeleteClosed(event) {
      if (event.detail?.requestId !== pendingDeleteRef.current?.requestId) return

      pendingDeleteRef.current = null
    }

    document.addEventListener("record-delete:success", handleDeleteSuccess)
    document.addEventListener("record-delete:closed", handleDeleteClosed)

    return () => {
      document.removeEventListener("record-delete:success", handleDeleteSuccess)
      document.removeEventListener("record-delete:closed", handleDeleteClosed)
    }
  }, [currentContext])

  return {
    suppressRenameBlurRef,
    treeData,
    expanded,
    currentContext,
    hasLoaded,
    loadError,
    contextMenu,
    renamingNodeId,
    renamingNodeType,
    renameValue,
    renameError,
    isRenamingSubmitting,
    setContextMenu,
    setRenameValue,
    toggleFolder,
    navigateTo,
    beginRename,
    submitRename,
    cancelRename,
    handleNodeContextMenu,
    handleTreeBackgroundContextMenu,
    handleContextMenuRename,
    handleContextMenuDelete
  }
}
