import React from "react"
import { createRoot } from "react-dom/client"

import CampaignTree from "../components/CampaignTree"
import PlayerScreen from "../components/PlayerScreen"

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

function mountPlayerScreen() {
  const element = document.getElementById("player-screen")
  if (!element) return

  let root = roots.get(element)
  if (!root) {
    root = createRoot(element)
    roots.set(element, root)
  }

  root.render(
    <PlayerScreen
      campaignId={element.dataset.campaignId}
      initialImageUrl={element.dataset.initialImage || element.dataset.imageUrl || null}
      initialImageTitle={element.dataset.imageTitle || ""}
      initialShowTitle={element.dataset.showTitle === "true"}
      initialTransitionType={element.dataset.transitionType || "crossfade"}
      initialCrossfadeDuration={element.dataset.crossfadeDuration || "400"}
      initialImageFit={element.dataset.imageFit || "contain"}
    />
  )
}

document.addEventListener("turbo:load", mountCampaignTree)
document.addEventListener("turbo:load", mountPlayerScreen)
mountCampaignTree()
mountPlayerScreen()
