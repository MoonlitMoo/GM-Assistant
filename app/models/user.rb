class User < ApplicationRecord
  DEFAULT_TRANSITION = "crossfade"
  DEFAULT_SHOW_TITLE = false
  BOOLEAN_TYPE = ActiveModel::Type::Boolean.new

  serialize :preferences, coder: JSON

  has_secure_password
  has_many :campaigns, dependent: :destroy
  has_many :sessions, dependent: :destroy

  normalizes :email_address, with: ->(e) { e.strip.downcase }

  validates :default_transition, inclusion: { in: PlayerDisplay.transition_types.keys }

  def preferences
    super || {}
  end

  def default_transition
    preferences.fetch("default_transition", DEFAULT_TRANSITION)
  end

  def default_transition=(value)
    self.preferences = preferences.merge("default_transition" => value)
  end

  def default_show_title
    BOOLEAN_TYPE.cast(preferences.fetch("default_show_title", DEFAULT_SHOW_TITLE))
  end

  def default_show_title=(value)
    self.preferences = preferences.merge("default_show_title" => BOOLEAN_TYPE.cast(value))
  end
end
