import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["breadcrumbs"]

  connect() {
    this.syncBreadcrumbs()
  }

  syncBreadcrumbs(event) {
    const frame = this.findFrame(event)
    if (!frame) return

    const items = this.parseBreadcrumbs(this.findBreadcrumbsPayload(frame))
    this.breadcrumbsTarget.replaceChildren()

    if (items.length === 0) return

    const nav = document.createElement("nav")
    nav.setAttribute("aria-label", "Breadcrumbs")

    items.forEach(([label, url], index) => {
      if (index < items.length - 1) {
        const link = document.createElement("a")
        link.href = url
        link.textContent = label
        nav.appendChild(link)
        nav.appendChild(document.createTextNode(" › "))
      } else {
        const current = document.createElement("span")
        current.textContent = label
        nav.appendChild(current)
      }
    })

    this.breadcrumbsTarget.appendChild(nav)
  }

  findFrame(event) {
    if (event?.target?.id === "content-body") {
      return event.target
    }

    return this.element.querySelector("turbo-frame#content-body")
  }

  parseBreadcrumbs(rawBreadcrumbs) {
    try {
      return JSON.parse(rawBreadcrumbs || "[]")
    } catch {
      return []
    }
  }

  findBreadcrumbsPayload(frame) {
    return frame.querySelector("[data-breadcrumbs-payload]")?.dataset.breadcrumbsPayload
  }
}
