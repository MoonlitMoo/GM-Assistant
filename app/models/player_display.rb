class PlayerDisplay < ApplicationRecord
  belongs_to :campaign
  belongs_to :current_image, class_name: "Image", optional: true

  validates :campaign_id, uniqueness: true

  validate :current_image_belongs_to_same_campaign

  private
  def current_image_belongs_to_same_campaign
    return if current_image.nil?
    return if campaign.blank?
    return if current_image.campaign_id == campaign_id
    errors.add(:current_image_id, "must belong to same campaign")
  end
end
