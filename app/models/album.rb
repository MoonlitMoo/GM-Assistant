class Album < ApplicationRecord
  belongs_to :campaign
  belongs_to :folder

  has_many :images, -> { order(position: :asc) }, dependent: :destroy

  validates :name, presence: true
end
