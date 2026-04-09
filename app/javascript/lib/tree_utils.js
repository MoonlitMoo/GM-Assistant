export function inferredNodeType(node) {
  if (!node) return null
  if (node.type) return node.type
  if (Array.isArray(node.folders) && Array.isArray(node.albums)) return "folder"
  return "album"
}

export function csrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.content || ""
}
