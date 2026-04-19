import { Controller } from "@hotwired/stimulus"
import { csrfToken } from "../lib/tree_utils"

export default class extends Controller {
  static targets = ["modal", "card", "title", "name", "body", "error", "confirm"]

  connect() {
    this.boundOpenFromEvent = this.openFromEvent.bind(this)
    this.boundBeforeCache = this.beforeCache.bind(this)
    this.defaultConfirmLabel = this.confirmTarget.textContent
    this.currentRequest = null
    this.isDeleting = false

    document.addEventListener("record-delete:open", this.boundOpenFromEvent)
    document.addEventListener("turbo:before-cache", this.boundBeforeCache)
  }

  disconnect() {
    document.removeEventListener("record-delete:open", this.boundOpenFromEvent)
    document.removeEventListener("turbo:before-cache", this.boundBeforeCache)
  }

  openFromButton(event) {
    event.preventDefault()
    this.lastFocusedElement = event.currentTarget

    this.open({
      title: event.currentTarget.dataset.recordDeleteTitle,
      name: event.currentTarget.dataset.recordDeleteName,
      descriptionLines: this.parseDescriptionLines(event.currentTarget.dataset.recordDeleteDescriptionLines),
      deleteUrl: event.currentTarget.dataset.recordDeleteUrl,
      successMode: event.currentTarget.dataset.recordDeleteSuccessMode || "redirect"
    })
  }

  openFromEvent(event) {
    this.lastFocusedElement = null
    this.open(event.detail)
  }

  open(payload) {
    if (!payload?.deleteUrl) return

    if (this.modalTarget.open) {
      this.resetModal({ closeDialog: true, emitClosedEvent: false, restoreFocus: false })
    }

    this.currentRequest = {
      requestId: payload.requestId || null,
      deleteUrl: payload.deleteUrl,
      successMode: payload.successMode || "redirect"
    }

    this.renderPayload(payload)
    this.clearError()
    this.modalTarget.showModal()
    this.cardTarget.focus()
  }

  close(event) {
    event?.preventDefault()
    if (this.isDeleting) return
    if (!this.modalTarget.open) return

    this.resetModal({ closeDialog: true, emitClosedEvent: true, restoreFocus: true })
  }

  backdropClose(event) {
    if (event.target !== this.modalTarget) return
    this.close()
  }

  handleCancel(event) {
    event.preventDefault()
    this.close()
  }

  async confirmDelete() {
    if (!this.currentRequest?.deleteUrl) return
    if (this.confirmTarget.disabled) return

    this.isDeleting = true
    this.confirmTarget.disabled = true
    this.confirmTarget.textContent = "Deleting..."
    this.clearError()

    try {
      const response = await fetch(this.currentRequest.deleteUrl, {
        method: "DELETE",
        headers: {
          "Accept": "application/json",
          "X-CSRF-Token": csrfToken(),
          "X-Requested-With": "XMLHttpRequest"
        },
        credentials: "same-origin"
      })

      const { json: responseBody, text: responseText } = await this.parseResponse(response)

      if (!response.ok) {
        this.showError(this.errorMessage(responseBody, responseText))
        return
      }

      this.handleSuccessfulDelete(responseBody)
    } catch {
      this.showError("Couldn’t delete this item. Please check your connection and try again.")
    } finally {
      this.isDeleting = false
      this.confirmTarget.disabled = false
      this.confirmTarget.textContent = this.defaultConfirmLabel
    }
  }

  showError(message) {
    if (!this.hasErrorTarget) return

    this.errorTarget.textContent = message
    this.errorTarget.hidden = false
  }

  clearError() {
    if (!this.hasErrorTarget) return

    this.errorTarget.hidden = true
    this.errorTarget.textContent = ""
  }

  beforeCache() {
    this.resetModal({ closeDialog: true, emitClosedEvent: false, restoreFocus: false })
  }

  renderPayload(payload) {
    this.titleTarget.textContent = payload.title || "Delete Item"

    const name = payload.name || ""
    this.nameTarget.textContent = name
    this.nameTarget.hidden = name.length === 0

    this.bodyTarget.replaceChildren()

    for (const line of payload.descriptionLines || []) {
      const paragraph = document.createElement("p")
      paragraph.className = "tree-delete-modal__line"
      paragraph.textContent = line
      this.bodyTarget.append(paragraph)
    }
  }

  handleSuccessfulDelete(responseBody) {
    const request = this.currentRequest
    if (!request) return

    if (request.successMode === "redirect") {
      const redirectUrl = responseBody?.redirect_url
      if (!redirectUrl) {
        this.showError("Couldn’t determine where to go after deleting this item.")
        return
      }

      this.resetModal({ closeDialog: true, emitClosedEvent: false, restoreFocus: false })

      if (window.Turbo?.visit) {
        window.Turbo.visit(redirectUrl, { frame: "content-body" })
      } else {
        window.location.assign(redirectUrl)
      }

      return
    }

    this.resetModal({ closeDialog: true, emitClosedEvent: false, restoreFocus: false })

    document.dispatchEvent(new CustomEvent("record-delete:success", {
      detail: {
        requestId: request.requestId,
        responseBody
      }
    }))
  }

  async parseResponse(response) {
    const text = await response.text()

    if (!text) {
      return { json: null, text: "" }
    }

    try {
      return {
        json: JSON.parse(text),
        text
      }
    } catch {
      return { json: null, text }
    }
  }

  errorMessage(responseBody, responseText) {
    if (Array.isArray(responseBody?.errors) && responseBody.errors.length > 0) {
      return responseBody.errors.join(", ")
    }

    if (responseText?.trim()) {
      return responseText.trim()
    }

    return "Couldn’t delete this item. Please try again."
  }

  parseDescriptionLines(value) {
    if (!value) return []

    try {
      const lines = JSON.parse(value)
      return Array.isArray(lines) ? lines : []
    } catch {
      return []
    }
  }

  resetModal({ closeDialog, emitClosedEvent, restoreFocus }) {
    const requestId = this.currentRequest?.requestId || null

    if (closeDialog && this.modalTarget.open) {
      this.modalTarget.close()
    }

    this.currentRequest = null
    this.isDeleting = false
    this.confirmTarget.disabled = false
    this.confirmTarget.textContent = this.defaultConfirmLabel
    this.clearError()
    this.bodyTarget.replaceChildren()
    this.nameTarget.textContent = ""
    this.nameTarget.hidden = true

    if (emitClosedEvent && requestId) {
      document.dispatchEvent(new CustomEvent("record-delete:closed", {
        detail: { requestId }
      }))
    }

    if (restoreFocus && this.lastFocusedElement?.isConnected) {
      this.lastFocusedElement.focus()
    }

    this.lastFocusedElement = null
  }
}
