class Campaign < ApplicationRecord
  has_one :root_folder, -> { where(is_root: true) }, class_name: "Folder", dependent: :destroy
  has_many :folders, dependent: :destroy
  has_many :albums, dependent: :destroy
  has_many :images, dependent: :destroy

  validates :name, presence: true
  validates :root_folder, presence: true
end
