import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  submit(event) {
    if (event.defaultPrevented) return
    if (event.isComposing) return
    if (event.key !== "Enter") return
    if (!event.ctrlKey && !event.metaKey) return
    if (event.altKey) return

    const form = this.element
    if (!(form instanceof HTMLFormElement)) return

    event.preventDefault()

    const submitter = form.querySelector("input[type='submit']:not([disabled]), button[type='submit']:not([disabled])")
    form.requestSubmit(submitter || undefined)
  }
}
