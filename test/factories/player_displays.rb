FactoryBot.define do
  factory :player_display do
    campaign
    current_image { nil }

    trait :with_current_image do
      current_image { association(:image, campaign: campaign) }
    end
  end
end
