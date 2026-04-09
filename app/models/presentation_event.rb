class PresentationEvent < ApplicationRecord
  belongs_to :campaign
  belongs_to :image, optional: true

  enum :event_type, { presented: 0, cleared: 1 }

  validates :campaign, presence: true
  validates :event_type, presence: true

  def self.recent_for_panel(campaign, excluding_image: nil, limit: 3)
    scope = campaign.presentation_events
                    .presented
                    .where.not(image_id: nil)
                    .order(created_at: :desc)
    scope = scope.where.not(image_id: excluding_image.id) if excluding_image

    ranked_scope = scope.select(
      "presentation_events.*",
      "ROW_NUMBER() OVER (PARTITION BY image_id ORDER BY created_at DESC, id DESC) AS presentation_rank"
    )

    from("(#{ranked_scope.to_sql}) presentation_events")
      .where("presentation_rank = 1")
      .order(created_at: :desc, id: :desc)
      .limit(limit)
  end
end
