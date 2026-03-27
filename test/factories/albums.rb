FactoryBot.define do
  factory :album do
    sequence(:name) { |n| "Album #{n}" }
    campaign

    folder do
      campaign&.persisted? ? campaign.root_folder : association(:folder, campaign: campaign)
    end
  end
end
