FactoryBot.define do
  factory :invite_code do
    sequence(:token) { |n| "invite-token-#{n}" }
    used_at { nil }
    used_by_user { nil }
  end
end
