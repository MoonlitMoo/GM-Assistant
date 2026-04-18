FactoryBot.define do
  factory :folder do
    sequence(:name) { |n| "Folder #{n}" }
    campaign
    is_root { false }

    parent do
      if campaign&.persisted?
        campaign.root_folder
      else
        association(:folder, :root, campaign: campaign)
      end
    end

    trait :root do
      name { "Root" }
      is_root { true }
      parent { nil }
    end
  end
end
