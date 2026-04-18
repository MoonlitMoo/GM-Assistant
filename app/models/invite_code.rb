class InviteCode < ApplicationRecord
  belongs_to :used_by_user, class_name: "User", optional: true

  scope :unused, -> { where(used_at: nil) }

  validates :token, presence: true, uniqueness: true

  def use!(user)
    self.used_at = Time.current
    self.used_by_user = user
    save!
  end

  def self.generate!(count: 1)
    Array.new(count.to_i) do
      create!(token: SecureRandom.urlsafe_base64(12)).token
    end
  end
end
