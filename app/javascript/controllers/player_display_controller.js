import { Controller } from "@hotwired/stimulus"
import consumer from "../channels/consumer"

export default class extends Controller {
  static values = {
    campaignId: Number,
    clearUrl: String,
    presentUrl: String,
    presentingImageId: Number
  }

  connect() {
    this.syncButtons()
    this.subscribeToPlayerDisplay()
  }

  disconnect() {
    this.unsubscribeFromPlayerDisplay()
  }

  async present(event) {
    event.preventDefault()

    const button = event.currentTarget
    const imageId = Number(button.dataset.playerDisplayImageId)

    if (!imageId) return

    await this.submit(button, this.presentUrlValue, { current_image_id: imageId }, () => {
      this.presentingImageIdValue = imageId
    })
  }

  async clear(event) {
    event.preventDefault()

    if (!this.hasClearUrlValue) return

    await this.submit(event.currentTarget, this.clearUrlValue, {}, () => {
      this.presentingImageIdValue = 0
    })
  }

  async submit(button, url, payload, onSuccess) {
    const previouslyDisabled = button.disabled

    button.disabled = true
    button.classList.add("is-busy")

    try {
      const response = await fetch(url, {
        method: "PATCH",
        headers: {
          "Accept": "text/vnd.turbo-stream.html",
          "Content-Type": "application/json",
          "X-CSRF-Token": this.csrfToken,
          "X-Requested-With": "XMLHttpRequest"
        },
        credentials: "same-origin",
        body: JSON.stringify(payload)
      })

      const responseText = await response.text()

      if (!response.ok) {
        window.console.error("Player display update failed", responseText || response.statusText)
        return
      }

      if (responseText.trim().length > 0) {
        window.Turbo.renderStreamMessage(responseText)
      }

      onSuccess()
    } catch (error) {
      window.console.error("Player display update failed", error)
    } finally {
      button.disabled = previouslyDisabled
      button.classList.remove("is-busy")
      this.syncButtons()
    }
  }

  syncButtons() {
    const presentingImageId = this.presentingImageIdValue || 0
    const hasPresentedImage = presentingImageId > 0

    this.element.querySelectorAll("[data-player-display-image-id]").forEach((button) => {
      const imageId = Number(button.dataset.playerDisplayImageId)
      const isActive = hasPresentedImage && imageId === presentingImageId
      const activeLabel = button.dataset.playerDisplayActiveLabel || "Presenting"
      const inactiveLabel = button.dataset.playerDisplayInactiveLabel || "Present"

      button.textContent = isActive ? activeLabel : inactiveLabel
      button.classList.toggle("fantasy-button--active", isActive)
      button.classList.toggle("is-active", isActive)
      button.setAttribute("aria-pressed", isActive ? "true" : "false")
    })

    this.element.querySelectorAll("[data-player-display-clear]").forEach((button) => {
      button.disabled = !hasPresentedImage
      button.classList.toggle("fantasy-button--disabled", !hasPresentedImage)
    })
  }

  subscribeToPlayerDisplay() {
    if (!this.hasCampaignIdValue) return

    this.unsubscribeFromPlayerDisplay()

    this.subscription = consumer.subscriptions.create(
      { channel: "PlayerDisplayChannel", campaign_id: this.campaignIdValue },
      {
        received: (data) => {
          if (data.cleared) {
            this.presentingImageIdValue = 0
          } else {
            this.presentingImageIdValue = Number(data.image_id || 0)
          }

          this.syncButtons()
        }
      }
    )
  }

  unsubscribeFromPlayerDisplay() {
    if (!this.subscription) return

    this.subscription.unsubscribe()
    this.subscription = null
  }

  get csrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || ""
  }
}
