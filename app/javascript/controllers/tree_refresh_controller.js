import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  connect() {
    document.dispatchEvent(new CustomEvent("tree:refresh"))
    this.element.remove()
  }
}
