import React, { useMemo, useRef, useState } from "react"
import { createPortal } from "react-dom"
import usePortalDismiss from "../hooks/usePortalDismiss"
import { csrfToken, inferredNodeType } from "../lib/tree_utils"

function pluralize(count, noun) {
  return `${count} ${noun}${count === 1 ? "" : "s"}`
}

export default function DeleteConfirmModal({ node, onClose, onDeleted }) {
  const cardRef = useRef(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [errorMessage, setErrorMessage] = useState("")

  const nodeType = inferredNodeType(node)
  const counts = useMemo(() => ({
    childFolderCount: Number(node?.child_folder_count || 0),
    albumCount: Number(node?.album_count || 0),
    imageCount: Number(node?.image_count || 0)
  }), [node])

  usePortalDismiss({
    containerRef: cardRef,
    enabled: !!node,
    onClose,
    isDismissDisabled: isDeleting
  })

  if (!node || typeof document === "undefined" || !document.body) {
    return null
  }

  async function handleDelete() {
    if (!node.url || isDeleting) return

    setIsDeleting(true)
    setErrorMessage("")

    try {
      const response = await fetch(node.url, {
        method: "DELETE",
        headers: {
          "Accept": "application/json",
          "X-CSRF-Token": csrfToken(),
          "X-Requested-With": "XMLHttpRequest"
        },
        credentials: "same-origin"
      })

      if (!response.ok) {
        const responseText = (await response.text()).trim()
        setErrorMessage(responseText || "Couldn’t delete this item. Please try again.")
        return
      }

      onDeleted()
    } catch {
      setErrorMessage("Couldn’t delete this item. Please check your connection and try again.")
    } finally {
      setIsDeleting(false)
    }
  }

  function handleOverlayClick(event) {
    if (event.target !== event.currentTarget || isDeleting) return
    onClose()
  }

  const title = nodeType === "folder" ? "Delete Folder" : "Delete Album"
  const description = nodeType === "folder"
    ? [
        pluralize(counts.childFolderCount, "subfolder"),
        pluralize(counts.albumCount, "album"),
        pluralize(counts.imageCount, "image"),
        "This cannot be undone."
      ]
    : [
        `${pluralize(counts.imageCount, "image")} will be deleted.`,
        "This cannot be undone."
      ]

  return createPortal(
    <div
      className="tree-delete-modal"
      role="presentation"
      onClick={handleOverlayClick}
    >
      <div
        ref={cardRef}
        className="tree-delete-modal__card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="tree-delete-modal-title"
        tabIndex={-1}
      >
        <p className="tree-delete-modal__kicker">Archive Warning</p>
        <h2 id="tree-delete-modal-title" className="tree-delete-modal__title">{title}</h2>
        <p className="tree-delete-modal__name">{node.name}</p>

        <div className="tree-delete-modal__body">
          {description.map((line) => (
            <p key={line} className="tree-delete-modal__line">{line}</p>
          ))}
        </div>

        {errorMessage ? (
          <p className="tree-delete-modal__error" role="alert">{errorMessage}</p>
        ) : null}

        <div className="tree-delete-modal__actions">
          <button
            type="button"
            className="fantasy-button"
            onClick={onClose}
            disabled={isDeleting}
          >
            Cancel
          </button>
          <button
            type="button"
            className="fantasy-button fantasy-button--danger tree-delete-modal__delete"
            onClick={handleDelete}
            disabled={isDeleting}
          >
            {isDeleting ? "Deleting..." : "Delete"}
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}
