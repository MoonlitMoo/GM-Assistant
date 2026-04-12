class User < ApplicationRecord
  # Let Devise keep using the existing auth columns.
  alias_attribute :email, :email_address

  # Include default devise modules. Others available are:
  # :confirmable, :lockable, :timeoutable, :trackable and :omniauthable
  devise :database_authenticatable, :registerable,
         :recoverable, :rememberable, :validatable
  DEFAULT_TRANSITION = "crossfade"
  DEFAULT_SHOW_TITLE = false
  DEFAULT_CROSSFADE_DURATION = 400
  DEFAULT_DASHBOARD_RECENT_COUNT = 5
  DEFAULT_GM_HISTORY_COUNT = 3
  DEFAULT_IMAGE_FIT = "contain"
  CROSSFADE_DURATIONS = [ 200, 400, 600, 800, 1000 ].freeze
  DASHBOARD_RECENT_COUNTS = [ 3, 5, 8, 10 ].freeze
  GM_HISTORY_COUNTS = [ 2, 3, 5, 8 ].freeze
  IMAGE_FITS = %w[contain cover].freeze
  BOOLEAN_TYPE = ActiveModel::Type::Boolean.new
  INTEGER_TYPE = ActiveModel::Type::Integer.new

  serialize :preferences, coder: JSON

  has_many :campaigns, dependent: :destroy

  normalizes :email_address, with: ->(e) { e.strip.downcase }

  validates :default_transition, inclusion: { in: PlayerDisplay.transition_types.keys }
  validates :crossfade_duration, inclusion: { in: CROSSFADE_DURATIONS }
  validates :dashboard_recent_count, inclusion: { in: DASHBOARD_RECENT_COUNTS }
  validates :gm_history_count, inclusion: { in: GM_HISTORY_COUNTS }
  validates :image_fit, inclusion: { in: IMAGE_FITS }

  def preferences
    super || {}
  end

  def encrypted_password
    self[:password_digest]
  end

  def encrypted_password=(value)
    self[:password_digest] = value
  end

  # Devise internally uses a helper named `password_digest(password)`, which
  # collides with the legacy column reader. Support both call patterns.
  def password_digest(raw_password = nil)
    return self[:password_digest] if raw_password.nil?

    Devise::Encryptor.digest(self.class, raw_password)
  end

  def encrypted_password_before_last_save
    attribute_before_last_save("password_digest")
  end

  def encrypted_password_in_database
    attribute_in_database("password_digest")
  end

  def saved_change_to_encrypted_password?
    saved_change_to_password_digest?
  end

  def will_save_change_to_encrypted_password?
    will_save_change_to_password_digest?
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

  def crossfade_duration
    INTEGER_TYPE.cast(preferences.fetch("crossfade_duration", DEFAULT_CROSSFADE_DURATION))
  end

  def crossfade_duration=(value)
    self.preferences = preferences.merge("crossfade_duration" => INTEGER_TYPE.cast(value))
  end

  def dashboard_recent_count
    INTEGER_TYPE.cast(preferences.fetch("dashboard_recent_count", DEFAULT_DASHBOARD_RECENT_COUNT))
  end

  def dashboard_recent_count=(value)
    self.preferences = preferences.merge("dashboard_recent_count" => INTEGER_TYPE.cast(value))
  end

  def gm_history_count
    INTEGER_TYPE.cast(preferences.fetch("gm_history_count", DEFAULT_GM_HISTORY_COUNT))
  end

  def gm_history_count=(value)
    self.preferences = preferences.merge("gm_history_count" => INTEGER_TYPE.cast(value))
  end

  def image_fit
    preferences.fetch("image_fit", DEFAULT_IMAGE_FIT)
  end

  def image_fit=(value)
    self.preferences = preferences.merge("image_fit" => value)
  end
end
