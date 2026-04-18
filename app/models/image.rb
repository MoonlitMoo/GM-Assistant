class Image < ApplicationRecord
  belongs_to :campaign
  belongs_to :album

  has_one_attached :file
  has_many :presentation_events, dependent: :nullify

  validates :title, presence: true
  validates :file, presence: true, on: :create

  validate :album_belongs_to_same_campaign

  private
  def album_belongs_to_same_campaign
    return if album.nil?
    return if album.campaign_id == campaign_id
    errors.add(:album_id, "must belong to same campaign")
  end
end
