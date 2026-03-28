import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["container"]
  static values = { url: String }

  connect() {
    this.expanded = {}
    this.refreshTree = this.fetchTree.bind(this)
    document.addEventListener("tree:refresh", this.refreshTree)
    this.fetchTree()
  }

  disconnect() {
    document.removeEventListener("tree:refresh", this.refreshTree)
  }

  fetchTree() {
    fetch(this.urlValue)
      .then(r => r.json())
      .then(data => {
        this.treeData = data
        this.campaignId = data.campaignId
        this.expanded = this.loadExpandedState()
        this.render()
      })
  }

  render() {
    this.containerTarget.innerHTML = ""
    const ul = this.buildFolderContents(this.treeData)
    this.containerTarget.appendChild(ul)
  }

  buildFolderContents(folder) {
    const ul = document.createElement("ul")

    folder.folders.forEach(child => {
      ul.appendChild(this.buildFolderNode(child))
    })

    folder.albums.forEach(album => {
      ul.appendChild(this.buildAlbumNode(album))
    })

    return ul
  }

  buildFolderNode(folder) {
    const li = document.createElement("li")
    li.classList.add("tree-folder")

    const toggle = document.createElement("span")
    toggle.classList.add("tree-toggle")
    toggle.textContent = this.expanded[folder.id] ? "▾" : "▸"

    const label = document.createElement("span")
    label.classList.add("tree-label")
    label.textContent = folder.name
    label.addEventListener("click", () => this.navigateTo(folder.url))

    toggle.addEventListener("click", () => {
      if (this.expanded[folder.id]) {
        delete this.expanded[folder.id]
      } else {
        this.expanded[folder.id] = true
      }

      this.saveExpandedState()
      this.render()
    })

    li.appendChild(toggle)
    li.appendChild(label)

    if (this.expanded[folder.id]) {
      li.appendChild(this.buildFolderContents(folder))
    }

    return li
  }

  buildAlbumNode(album) {
    const li = document.createElement("li")
    li.classList.add("tree-album")

    const label = document.createElement("span")
    label.classList.add("tree-label")
    label.textContent = album.name
    label.addEventListener("click", () => this.navigateTo(album.url))

    li.appendChild(label)
    return li
  }

  navigateTo(url) {
    Turbo.visit(url, { frame: "content-body" })
  }

  loadExpandedState() {
    if (!this.storageKey) return {}

    try {
      return JSON.parse(sessionStorage.getItem(this.storageKey) || "{}")
    } catch {
      return {}
    }
  }

  saveExpandedState() {
    if (!this.storageKey) return

    sessionStorage.setItem(this.storageKey, JSON.stringify(this.expanded))
  }

  get storageKey() {
    return this.campaignId ? `campaign-tree:${this.campaignId}:expanded` : null
  }
}
