import React from "react"

export { csrfToken, inferredNodeType } from "../lib/tree_utils"

export function storageKeyFor(campaignId) {
  return `campaign-tree:${campaignId}:expanded`
}

export function loadExpandedState(campaignId) {
  try {
    return JSON.parse(sessionStorage.getItem(storageKeyFor(campaignId)) || "{}")
  } catch {
    return {}
  }
}

export function saveExpandedState(campaignId, expanded) {
  sessionStorage.setItem(storageKeyFor(campaignId), JSON.stringify(expanded))
}

export function readBreadcrumbUrls() {
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

export function currentTreeContext() {
  return {
    path: window.location.pathname,
    fullPath: `${window.location.pathname}${window.location.search}`,
    breadcrumbUrls: readBreadcrumbUrls()
  }
}

export function treeIsEmpty(folder) {
  return folder.folders.length === 0 && folder.albums.length === 0
}

export function findExpandedPath(folder, targetUrl) {
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

export function requiredExpandedState(folder, context) {
  const candidateUrls = [context.path, ...[...context.breadcrumbUrls].reverse()]

  for (const url of candidateUrls) {
    const expandedPath = findExpandedPath(folder, url)
    if (expandedPath !== null) {
      return Object.fromEntries(expandedPath.map((folderId) => [folderId, true]))
    }
  }

  return {}
}

export function expandedStatesMatch(left, right) {
  const leftEntries = Object.entries(left)
  const rightEntries = Object.entries(right)

  if (leftEntries.length !== rightEntries.length) return false

  return leftEntries.every(([key, value]) => right[key] === value)
}

export function statusMessage(title, body, modifier = "") {
  return React.createElement(
    "div",
    { className: `tree-status ${modifier}`.trim() },
    React.createElement("p", { className: "tree-status__title" }, title),
    body ? React.createElement("p", { className: "tree-status__body" }, body) : null
  )
}

export function renamePayloadFor(nodeType, name) {
  if (nodeType === "folder") return { folder: { name } }
  return { album: { name } }
}

export function renameErrorMessage(responseBody, fallbackMessage) {
  if (Array.isArray(responseBody?.errors) && responseBody.errors.length > 0) {
    return responseBody.errors.join(", ")
  }

  return fallbackMessage
}
