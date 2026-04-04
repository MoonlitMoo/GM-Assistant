FactoryBot.define do
  factory :campaign do
    user { Current.user || association(:user) }
    sequence(:name) { |n| "Campaign #{n}" }
  end
end
