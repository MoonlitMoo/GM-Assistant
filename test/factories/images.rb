FactoryBot.define do
  factory :image do
    sequence(:title) { |n| "Image #{n}" }
    campaign
    album { association(:album, campaign: campaign) }
    file { Rack::Test::UploadedFile.new(Rails.root.join("test/fixtures/files/test_image.jpg"), "image/jpeg") }
  end
end
