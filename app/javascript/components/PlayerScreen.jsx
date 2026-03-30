import React, { useEffect, useState } from "react"

import consumer from "../channels/consumer"

export default function PlayerScreen({ campaignId, initialImageUrl }) {
  const [imageUrl, setImageUrl] = useState(initialImageUrl)

  useEffect(() => {
    setImageUrl(initialImageUrl)
  }, [initialImageUrl])

  useEffect(() => {
    if (!campaignId) return undefined

    const subscription = consumer.subscriptions.create(
      { channel: "PlayerDisplayChannel", campaign_id: campaignId },
      {
        received(data) {
          if (data.cleared) {
            setImageUrl(null)
            return
          }

          setImageUrl(data.image_url || null)
        }
      }
    )

    return () => {
      subscription.unsubscribe()
    }
  }, [campaignId])

  return (
    <div className="player-screen">
      {imageUrl ? (
        <img
          src={imageUrl}
          alt="Presented artwork"
          className="player-screen__image"
        />
      ) : (
        <div className="player-screen__blank" />
      )}
    </div>
  )
}
