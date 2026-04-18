import React, { useEffect, useRef, useState } from "react"

import consumer from "../channels/consumer"

function buildImage(url, title) {
  if (!url) return null

  return {
    url,
    title: title || ""
  }
}

function normalizeTransitionType(value) {
  return value === "instant" ? "instant" : "crossfade"
}

function normalizeCrossfadeDuration(value) {
  const duration = Number(value)
  return [200, 400, 600, 800, 1000].includes(duration) ? duration : 400
}

function normalizeImageFit(value) {
  return value === "cover" ? "cover" : "contain"
}

function hasOwnKey(payload, key) {
  return Object.prototype.hasOwnProperty.call(payload, key)
}

export default function PlayerScreen({
  campaignId,
  initialImageUrl,
  initialImageTitle,
  initialShowTitle,
  initialTransitionType,
  initialCrossfadeDuration,
  initialImageFit
}) {
  const [image, setImage] = useState(buildImage(initialImageUrl, initialImageTitle))
  const [showTitle, setShowTitle] = useState(initialShowTitle)
  const [transitionType, setTransitionType] = useState(normalizeTransitionType(initialTransitionType))
  const [crossfadeDuration, setCrossfadeDuration] = useState(normalizeCrossfadeDuration(initialCrossfadeDuration))
  const [imageFit, setImageFit] = useState(normalizeImageFit(initialImageFit))
  const [isTransitioning, setIsTransitioning] = useState(false)

  const imageRef = useRef(image)
  const transitionTypeRef = useRef(transitionType)
  const timeoutRef = useRef(null)

  useEffect(() => {
    imageRef.current = image
  }, [image])

  useEffect(() => {
    transitionTypeRef.current = transitionType
  }, [transitionType])

  useEffect(() => {
    clearPendingTransition()
    setImage(buildImage(initialImageUrl, initialImageTitle))
    setShowTitle(initialShowTitle)
    setTransitionType(normalizeTransitionType(initialTransitionType))
    setCrossfadeDuration(normalizeCrossfadeDuration(initialCrossfadeDuration))
    setImageFit(normalizeImageFit(initialImageFit))
    setIsTransitioning(false)
  }, [initialCrossfadeDuration, initialImageFit, initialImageTitle, initialImageUrl, initialShowTitle, initialTransitionType])

  useEffect(() => () => {
    clearPendingTransition()
  }, [])

  useEffect(() => {
    if (!campaignId) return undefined

    const subscription = consumer.subscriptions.create(
      { channel: "PlayerDisplayChannel", campaign_id: campaignId },
      {
        received(data) {
          if (data.cleared) {
            handleClear()
            return
          }

          if (hasOwnKey(data, "image_url")) {
            handlePresent(data)
            return
          }

          if (hasOwnKey(data, "show_title")) {
            setShowTitle(Boolean(data.show_title))
          }
        }
      }
    )

    return () => {
      subscription.unsubscribe()
    }
  }, [campaignId])

  function clearPendingTransition() {
    if (!timeoutRef.current) return

    window.clearTimeout(timeoutRef.current)
    timeoutRef.current = null
  }

  function finishTransition(afterUpdate) {
    clearPendingTransition()
    setIsTransitioning(true)

    timeoutRef.current = window.setTimeout(() => {
      afterUpdate()
      timeoutRef.current = null
      window.requestAnimationFrame(() => {
        setIsTransitioning(false)
      })
    }, crossfadeDuration)
  }

  function handlePresent(data) {
    const nextImage = buildImage(data.image_url, data.image_title)
    const nextShowTitle = Boolean(data.show_title)
    const nextTransitionType = normalizeTransitionType(data.transition_type)
    const nextImageFit = normalizeImageFit(data.image_fit)

    const applyUpdate = () => {
      setImage(nextImage)
      setShowTitle(nextShowTitle)
      setTransitionType(nextTransitionType)
      setImageFit(nextImageFit)
    }

    if (nextTransitionType === "crossfade") {
      if (imageRef.current) {
        finishTransition(applyUpdate)
      } else {
        clearPendingTransition()
        applyUpdate()
        setIsTransitioning(true)
        window.requestAnimationFrame(() => {
          setIsTransitioning(false)
        })
      }
      return
    }

    clearPendingTransition()
    setIsTransitioning(false)
    applyUpdate()
  }

  function handleClear() {
    if (transitionTypeRef.current === "crossfade" && imageRef.current) {
      finishTransition(() => {
        setImage(null)
      })
      return
    }

    clearPendingTransition()
    setIsTransitioning(false)
    setImage(null)
  }

  return (
    <div className="player-screen">
      {image ? (
        <img
          src={image.url}
          alt="Presented artwork"
          className={`player-screen__image player-image${isTransitioning ? " transitioning" : ""}`}
          style={{ objectFit: imageFit, transitionDuration: `${crossfadeDuration}ms` }}
        />
      ) : (
        <div className="player-screen__blank" />
      )}

      {image ? (
        <div className={`player-title-overlay${showTitle && !isTransitioning ? " is-visible" : ""}`}>
          {image.title}
        </div>
      ) : null}
    </div>
  )
}
