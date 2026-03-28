import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["container"]
  static values = { url: String }

  connect() {
    this.expanded = {}
    this.fetchTree()
  }

  fetchTree() {
    fetch(this.urlValue)
      .then(r => r.json())
      .then(data => {
        this.treeData = data
        this.render()
      })
  }

  render() {
    document.getElementById("tree-container").innerHTML = ""
    const ul = this.buildFolderContents(this.treeData)
    document.getElementById("tree-container").appendChild(ul)
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
      this.expanded[folder.id] = !this.expanded[folder.id]
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
}