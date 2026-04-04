require "bcrypt"

class AddUserToCampaigns < ActiveRecord::Migration[8.1]
  class MigrationCampaign < ApplicationRecord
    self.table_name = "campaigns"
  end

  class MigrationUser < ApplicationRecord
    self.table_name = "users"
  end

  def up
    add_reference :campaigns, :user, foreign_key: true, null: true

    backfill_campaign_owners!

    change_column_null :campaigns, :user_id, false
  end

  def down
    remove_reference :campaigns, :user, foreign_key: true
  end

  private

  def backfill_campaign_owners!
    return unless MigrationCampaign.exists?

    owner_id = MigrationUser.order(:id).pick(:id) || create_development_owner!

    if owner_id.nil?
      raise ActiveRecord::MigrationError,
            "Existing campaigns need a user before ownership can be backfilled."
    end

    MigrationCampaign.where(user_id: nil).update_all(user_id: owner_id)
  end

  def create_development_owner!
    return unless Rails.env.development? || Rails.env.test?

    MigrationUser.create!(
      email_address: "gm@example.com",
      password_digest: BCrypt::Password.create("password"),
      created_at: Time.current,
      updated_at: Time.current
    ).id
  end
end
