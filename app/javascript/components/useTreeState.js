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

  return {
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
  }
}
