FactoryBot.define do
  factory :campaign do
    association :user
    sequence(:name) { |n| "Campaign #{n}" }
  end
end
