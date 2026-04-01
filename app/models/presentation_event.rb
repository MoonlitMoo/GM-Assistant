class PresentationEvent < ApplicationRecord
  belongs_to :campaign
  belongs_to :image, optional: true

  enum :event_type, { presented: 0, cleared: 1 }

  validates :campaign, presence: true
  validates :event_type, presence: true

  scope :recent_presentations, -> { presented.order(created_at: :desc).limit(3) }
end
