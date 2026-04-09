class Folder < ApplicationRecord
  belongs_to :campaign
  belongs_to :parent, class_name: "Folder", optional: true

  has_many :child_folders, class_name: "Folder", foreign_key: :parent_id, dependent: :destroy
  has_many :albums, dependent: :destroy

  validates :name, presence: true
  # Make sure we don't mix folders in different campaigns
  validates :parent, presence: true, unless: :is_root?
  validate :folder_parent_from_same_campaign
  # Make sure that there is one root for the campaign and that it has no parent.
  validates :is_root, inclusion: { in: [ true, false ] }
  validates :is_root, uniqueness: { scope: :campaign_id }, if: :is_root?
  validate :root_folder_has_no_parent

  def ancestry
    lineage = []
    current = self

    while current.present?
      lineage.unshift(current) unless current.is_root?
      current = current.parent
    end

    lineage
  end

  def to_param
    "#{id}-#{name.squish.parameterize}"
  end

  private

  def folder_parent_from_same_campaign
    return if parent.blank?
    return if campaign.blank?
    return if parent.campaign_id == campaign_id
    errors.add(:parent_id, "must belong to same campaign.")
  end

  def root_folder_has_no_parent
    return unless is_root? && parent.present?
    errors.add(:parent_id, "must be nil for the root folder.")
  end
end
