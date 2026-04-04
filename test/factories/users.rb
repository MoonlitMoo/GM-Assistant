FactoryBot.define do
  factory :user do
    sequence(:email_address) { |n| "gm_#{n}@example.com" }
    password { "password" }
  end
end
