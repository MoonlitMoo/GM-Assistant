class Image < ApplicationRecord
  belongs_to :campaign
  belongs_to :album

  has_one_attached :file

  validates :name, presence: true
end
