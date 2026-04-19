import React from "react"
import { createRoot } from "react-dom/client"

import AlbumImageGrid from "../components/AlbumImageGrid"
import CampaignTree from "../components/CampaignTree"
import PlayerScreen from "../components/PlayerScreen"

const roots = new WeakMap()

function mountRoot(id, render) {
  const element = document.getElementById(id)
  if (!element) return

  let root = roots.get(element)
  if (!root) {
    root = createRoot(element)
    roots.set(element, root)
  }

  root.render(render(element))
}

function mountCampaignTree() {
  mountRoot("campaign-tree", (element) => <CampaignTree treeUrl={element.dataset.treeUrl} />)
}

function mountPlayerScreen() {
  mountRoot("player-screen", (element) => (
    <PlayerScreen
      campaignId={element.dataset.campaignId}
      initialImageUrl={element.dataset.initialImage || element.dataset.imageUrl || null}
      initialImageTitle={element.dataset.imageTitle || ""}
      initialShowTitle={element.dataset.showTitle === "true"}
      initialTransitionType={element.dataset.transitionType || "crossfade"}
      initialCrossfadeDuration={element.dataset.crossfadeDuration || "400"}
      initialImageFit={element.dataset.imageFit || "contain"}
    />
  ))
}

function parseAlbumImagePayload(value) {
  try {
    const payload = JSON.parse(value || "[]")
    return Array.isArray(payload) ? payload : []
  } catch {
    return []
  }
}

function mountAlbumImageGrid() {
  mountRoot("album-image-grid", (element) => (
    <AlbumImageGrid
      campaignId={Number(element.dataset.campaignId || 0)}
      presentUrl={element.dataset.presentUrl || ""}
      uploadUrl={element.dataset.uploadUrl || ""}
      initialPresentingImageId={Number(element.dataset.initialPresentingImageId || 0)}
      initialImages={parseAlbumImagePayload(element.dataset.imagesPayload)}
    />
  ))
}

document.addEventListener("turbo:load", mountCampaignTree)
document.addEventListener("turbo:load", mountAlbumImageGrid)
document.addEventListener("turbo:load", mountPlayerScreen)
mountCampaignTree()
mountAlbumImageGrid()
mountPlayerScreen()
