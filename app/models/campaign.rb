class Campaign < ApplicationRecord
  has_one :root_folder, -> { where(is_root: true) }, class_name: "Folder", dependent: :destroy
  has_one :player_display, dependent: :destroy
  has_many :presentation_events, dependent: :destroy
  has_many :folders, dependent: :destroy
  has_many :albums, dependent: :destroy
  has_many :images, dependent: :destroy

  validates :name, presence: true

  after_create :create_root_folder!

  def create_root_folder!
    folders.create!(name: "Root", is_root: true, campaign: @campaign)
  end
end
