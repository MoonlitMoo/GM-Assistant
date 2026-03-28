import React from "react"
import { createRoot } from "react-dom/client"

import CampaignTree from "../components/CampaignTree"

const roots = new WeakMap()

function mountCampaignTree() {
  const element = document.getElementById("campaign-tree")
  if (!element) return

  let root = roots.get(element)
  if (!root) {
    root = createRoot(element)
    roots.set(element, root)
  }

  root.render(<CampaignTree treeUrl={element.dataset.treeUrl} />)
}

document.addEventListener("turbo:load", mountCampaignTree)
mountCampaignTree()
