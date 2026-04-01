FactoryBot.define do
  factory :presentation_event do
    campaign
    event_type { :presented }
    image { association(:image, campaign: campaign) }
    image_title { image.title }

    trait :cleared_event do
      event_type { :cleared }
      image { nil }
      image_title { nil }
    end
  end
end
