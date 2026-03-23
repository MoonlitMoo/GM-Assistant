class Album < ApplicationRecord
  belongs_to :campaign
  belongs_to :folder

  has_many :images, dependent: :destroy

  validates :name, presence: true
end
