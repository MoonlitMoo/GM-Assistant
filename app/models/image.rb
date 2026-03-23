class Image < ApplicationRecord
  belongs_to :campaign
  belongs_to :album

  validates :name, presence: true
end
