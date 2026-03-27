FactoryBot.define do
  factory :campaign do
    sequence(:name) { |n| "Campaign #{n}" }
  end
end
