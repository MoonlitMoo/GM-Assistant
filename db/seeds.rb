# This file should ensure the existence of records required to run the application in every environment (production,
# development, test). The code here should be idempotent so that it can be executed at any point in every environment.
# The data can then be loaded with the bin/rails db:seed command (or created alongside the database with db:setup).
#
# Example:
#
#   ["Action", "Comedy", "Drama", "Horror"].each do |genre_name|
#     MovieGenre.find_or_create_by!(name: genre_name)
#   end

gm = User.find_or_initialize_by(email_address: "gm@example.com")
gm.assign_attributes(
  password: "password",
  password_confirmation: "password"
)
gm.save!

# If legacy local data predates campaign ownership, attach it to the seeded GM user.
Campaign.where(user_id: nil).find_each do |campaign|
  campaign.update!(user: gm)
end

# Any future seeded campaigns should be created through `gm.campaigns` so ownership
# stays explicit, for example:
# gm.campaigns.find_or_create_by!(name: "Starter Campaign")
