import React, { startTransition, useEffect, useLayoutEffect, useRef, useState } from "react"
import { createPortal } from "react-dom"

import consumer from "../channels/consumer"
import usePortalDismiss from "../hooks/usePortalDismiss"
import { csrfToken } from "../lib/tree_utils"

const MENU_VIEWPORT_PADDING = 12

function hasOwnKey(payload, key) {
  return Object.prototype.hasOwnProperty.call(payload, key)
}

function normalizeImage(image) {
  return {
    id: Number(image?.id || 0),
    title: image?.title || "",
    showTitle: Boolean(hasOwnKey(image || {}, "showTitle") ? image.showTitle : image?.show_title),
    url: image?.url || "",
    editUrl: image?.editUrl || image?.edit_url || "",
    deleteUrl: image?.deleteUrl || image?.delete_url || "",
    previewUrl: image?.previewUrl || image?.preview_url || null
  }
}

function titleVisibilityLabel(image) {
  return image.showTitle ? "Title visible on player screen" : "Title hidden on player screen"
}

function visitInContentFrame(url) {
  if (!url) return

  if (window.Turbo?.visit) {
    window.Turbo.visit(url, { frame: "content-body" })
    return
  }

  window.location.assign(url)
}

function workflowUrl(url) {
  if (!url) return url

  const returnTo = `${window.location.pathname}${window.location.search}`
  const target = new URL(url, window.location.origin)
  target.searchParams.set("return_to", returnTo)

  return `${target.pathname}${target.search}${target.hash}`
}

function parseJsonResponse(text) {
  if (!text) return null

  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

function contextMenuLabel(image) {
  return image.showTitle ? "Hide Title" : "Show Title"
}

function ImageCardContextMenu({ x, y, image, isPresenting, isBusy, onClose, onRename, onToggleTitle, onPresent, onEdit, onDelete }) {
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
  }, [x, y, image])

  if (!image || typeof document === "undefined" || !document.body) {
    return null
  }

  const items = [
    { label: "Rename", onSelect: onRename, disabled: isBusy },
    { label: contextMenuLabel(image), onSelect: onToggleTitle, disabled: isBusy },
    { label: isPresenting ? "Presenting" : "Present", onSelect: onPresent, disabled: isBusy || isPresenting },
    { label: "Edit", onSelect: onEdit, disabled: isBusy },
    { label: "Delete", onSelect: onDelete, disabled: isBusy, danger: true }
  ]

  return createPortal(
    <div
      ref={menuRef}
      className="tree-context-menu"
      role="menu"
      tabIndex={-1}
      aria-label={`${image.title} menu`}
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

export default function AlbumImageGrid({ campaignId, presentUrl, uploadUrl, initialPresentingImageId, initialImages }) {
  const suppressRenameBlurRef = useRef(false)
  const pendingDeleteRef = useRef(null)
  const [images, setImages] = useState(initialImages.map(normalizeImage))
  const [presentingImageId, setPresentingImageId] = useState(initialPresentingImageId)
  const [contextMenu, setContextMenu] = useState(null)
  const [renamingImageId, setRenamingImageId] = useState(null)
  const [renameValue, setRenameValue] = useState("")
  const [actionError, setActionError] = useState(null)
  const [busyImageIds, setBusyImageIds] = useState({})

  useEffect(() => {
    setImages(initialImages.map(normalizeImage))
    setPresentingImageId(initialPresentingImageId)
    setContextMenu(null)
    setRenamingImageId(null)
    setRenameValue("")
    setActionError(null)
    setBusyImageIds({})
    pendingDeleteRef.current = null
  }, [initialImages, initialPresentingImageId])

  useEffect(() => {
    if (!campaignId) return undefined

    const subscription = consumer.subscriptions.create(
      { channel: "PlayerDisplayChannel", campaign_id: campaignId },
      {
        received: (data) => {
          if (data.cleared) {
            setPresentingImageId(0)
            return
          }

          if (hasOwnKey(data, "image_id")) {
            setPresentingImageId(Number(data.image_id || 0))
          }
        }
      }
    )

    return () => {
      subscription.unsubscribe()
    }
  }, [campaignId])

  useEffect(() => {
    function handleDeleteSuccess(event) {
      const pendingDelete = pendingDeleteRef.current
      if (!pendingDelete) return
      if (event.detail?.requestId !== pendingDelete.requestId) return

      pendingDeleteRef.current = null
      startTransition(() => {
        setImages((currentImages) => currentImages.filter((image) => image.id !== pendingDelete.imageId))
      })
      setPresentingImageId((currentId) => (currentId === pendingDelete.imageId ? 0 : currentId))
      setContextMenu(null)
      setActionError((currentError) => (currentError?.imageId === pendingDelete.imageId ? null : currentError))

      if (renamingImageId === pendingDelete.imageId) {
        setRenamingImageId(null)
        setRenameValue("")
      }
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
  }, [renamingImageId])

  function setImageBusy(imageId, isBusy) {
    setBusyImageIds((currentBusy) => {
      const nextBusy = { ...currentBusy }

      if (isBusy) {
        nextBusy[imageId] = true
      } else {
        delete nextBusy[imageId]
      }

      return nextBusy
    })
  }

  function clearImageError(imageId) {
    setActionError((currentError) => (currentError?.imageId === imageId ? null : currentError))
  }

  function showImageError(imageId, message) {
    setActionError({ imageId, message })
  }

  function updateImageState(imageId, nextAttributes) {
    startTransition(() => {
      setImages((currentImages) =>
        currentImages.map((image) => {
          if (image.id !== imageId) return image

          return {
            ...image,
            ...nextAttributes
          }
        })
      )
    })
  }

  async function patchImage(image, attributes, fallbackMessage) {
    setImageBusy(image.id, true)
    clearImageError(image.id)

    try {
      const response = await fetch(image.url, {
        method: "PATCH",
        headers: {
          "Accept": "application/json",
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfToken(),
          "X-Requested-With": "XMLHttpRequest"
        },
        credentials: "same-origin",
        body: JSON.stringify({ image: attributes })
      })

      const responseText = await response.text()
      const responseBody = parseJsonResponse(responseText)

      if (!response.ok) {
        const errorMessage = responseBody?.errors?.join(", ") || fallbackMessage
        showImageError(image.id, errorMessage)
        return false
      }

      updateImageState(image.id, normalizeImage(responseBody || {}))
      return true
    } catch {
      showImageError(image.id, fallbackMessage)
      return false
    } finally {
      setImageBusy(image.id, false)
    }
  }

  async function presentImage(image) {
    if (!presentUrl || !image?.id) return
    if (busyImageIds[image.id]) return

    const previousPresentingImageId = presentingImageId
    setImageBusy(image.id, true)
    clearImageError(image.id)
    setPresentingImageId(image.id)

    try {
      const response = await fetch(presentUrl, {
        method: "PATCH",
        headers: {
          "Accept": "text/vnd.turbo-stream.html",
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfToken(),
          "X-Requested-With": "XMLHttpRequest"
        },
        credentials: "same-origin",
        body: JSON.stringify({ current_image_id: image.id })
      })

      const responseText = await response.text()

      if (!response.ok) {
        setPresentingImageId(previousPresentingImageId)
        showImageError(image.id, "Couldn’t present this image.")
        return
      }

      if (responseText.trim().length > 0 && window.Turbo?.renderStreamMessage) {
        window.Turbo.renderStreamMessage(responseText)
      }
    } catch {
      setPresentingImageId(previousPresentingImageId)
      showImageError(image.id, "Couldn’t present this image.")
    } finally {
      setImageBusy(image.id, false)
    }
  }

  function beginRename(image) {
    suppressRenameBlurRef.current = false
    setContextMenu(null)
    clearImageError(image.id)
    setRenamingImageId(image.id)
    setRenameValue(image.title)
  }

  function cancelRename(imageId = renamingImageId) {
    suppressRenameBlurRef.current = false
    if (imageId) clearImageError(imageId)
    setRenamingImageId(null)
    setRenameValue("")
  }

  async function submitRename(image) {
    if (!image || busyImageIds[image.id]) return

    const nextTitle = renameValue.trim()
    if (nextTitle.length === 0) {
      showImageError(image.id, "Title can't be blank")
      return
    }

    if (nextTitle === image.title) {
      cancelRename(image.id)
      return
    }

    const renamed = await patchImage(image, { title: nextTitle }, "Couldn’t rename this image.")
    if (!renamed) return

    cancelRename(image.id)
  }

  async function toggleTitleVisibility(image) {
    if (!image || busyImageIds[image.id]) return

    setContextMenu(null)
    await patchImage(
      image,
      { show_title: !image.showTitle },
      "Couldn’t update title visibility."
    )
  }

  function editImage(image) {
    setContextMenu(null)
    visitInContentFrame(workflowUrl(image.editUrl))
  }

  function deleteImage(image) {
    if (!image?.deleteUrl) return

    const requestId = `album-image-delete-${Date.now()}-${Math.round(Math.random() * 1e6)}`

    pendingDeleteRef.current = { requestId, imageId: image.id }
    setContextMenu(null)

    document.dispatchEvent(new CustomEvent("record-delete:open", {
      detail: {
        requestId,
        title: "Delete Image",
        name: image.title,
        descriptionLines: [
          "This image will be removed from the archive.",
          "This cannot be undone."
        ],
        deleteUrl: image.deleteUrl,
        successMode: "event"
      }
    }))
  }

  function renderEmptyState() {
    return (
      <div className="album-empty-state">
        <p>This album is still waiting for its first illustration.</p>
        <a href={uploadUrl} className="fantasy-button fantasy-button--primary" data-turbo-frame="content-body">
          Upload image
        </a>
      </div>
    )
  }

  function renderImageCard(image) {
    const isPresenting = presentingImageId === image.id
    const isBusy = Boolean(busyImageIds[image.id])
    const isRenaming = renamingImageId === image.id
    const inlineError = actionError?.imageId === image.id ? actionError.message : null

    return (
      <article
        className="image-card"
        key={image.id}
        onContextMenu={(event) => {
          event.preventDefault()
          event.stopPropagation()
          setContextMenu({
            x: event.clientX,
            y: event.clientY,
            imageId: image.id
          })
        }}
      >
        <div className="image-card__thumb-shell">
          <a href={image.url} className="image-card__thumb-link" data-turbo-frame="content-body">
            <div className="image-card__thumbnail">
              {image.previewUrl ? (
                <img
                  src={image.previewUrl}
                  alt={image.title}
                  className="image-card__preview"
                  loading="lazy"
                  decoding="async"
                />
              ) : (
                <div className="image-card__placeholder">No preview available</div>
              )}
            </div>
          </a>

          <button
            type="button"
            className={`fantasy-button fantasy-button--primary image-card__present-button ${isPresenting ? "fantasy-button--active is-active" : ""}`.trim()}
            aria-label={`Present ${image.title}`}
            aria-pressed={isPresenting ? "true" : "false"}
            disabled={isBusy}
            onClick={() => presentImage(image)}
          >
            {isPresenting ? "Presenting" : "Present"}
          </button>
        </div>

        <div className="image-card__copy">
          {isRenaming ? (
            <input
              type="text"
              className="image-card__rename-input"
              value={renameValue}
              autoFocus
              disabled={isBusy}
              onChange={(event) => setRenameValue(event.currentTarget.value)}
              onFocus={(event) => event.currentTarget.select()}
              onBlur={() => {
                if (suppressRenameBlurRef.current) {
                  suppressRenameBlurRef.current = false
                  return
                }

                submitRename(image)
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault()
                  submitRename(image)
                } else if (event.key === "Escape") {
                  event.preventDefault()
                  suppressRenameBlurRef.current = true
                  cancelRename(image.id)
                }
              }}
            />
          ) : (
            <h3 className="image-card__title">
              <a href={image.url} className="card-title-link" data-turbo-frame="content-body">
                {image.title}
              </a>
            </h3>
          )}

          <p className="image-card__meta">{titleVisibilityLabel(image)}</p>
          {inlineError ? <p className="image-card__inline-error">{inlineError}</p> : null}
        </div>
      </article>
    )
  }

  const contextMenuImage = images.find((image) => image.id === contextMenu?.imageId) || null

  return (
    <>
      {images.length === 0 ? renderEmptyState() : <div className="album-grid">{images.map(renderImageCard)}</div>}

      {contextMenuImage ? (
        <ImageCardContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          image={contextMenuImage}
          isPresenting={presentingImageId === contextMenuImage.id}
          isBusy={Boolean(busyImageIds[contextMenuImage.id])}
          onClose={() => setContextMenu(null)}
          onRename={() => beginRename(contextMenuImage)}
          onToggleTitle={() => toggleTitleVisibility(contextMenuImage)}
          onPresent={() => {
            setContextMenu(null)
            presentImage(contextMenuImage)
          }}
          onEdit={() => editImage(contextMenuImage)}
          onDelete={() => deleteImage(contextMenuImage)}
        />
      ) : null}
    </>
  )
}
