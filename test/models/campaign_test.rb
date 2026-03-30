require "test_helper"

class CampaignTest < ActiveSupport::TestCase
  test "is valid with a name" do
    campaign = build(:campaign)
    assert campaign.valid?
  end

  test "is invalid without a name" do
    campaign = build(:campaign, name: nil)
    assert_not campaign.valid?
    assert_includes campaign.errors[:name], "can't be blank"
  end

  test "creates a root folder after creation" do
    campaign = create(:campaign)
    assert_not_nil campaign.root_folder
  end

  test "root folder is marked as root" do
    campaign = create(:campaign)
    assert campaign.root_folder.is_root?
  end

  test "root folder belongs to the campaign" do
    campaign = create(:campaign)
    assert_equal campaign.id, campaign.root_folder.campaign_id
  end

  test "destroying a campaign destroys its root folder" do
    campaign = create(:campaign)
    folder_id = campaign.root_folder.id
    campaign.destroy
    assert_nil Folder.find_by(id: folder_id)
  end

  test "destroying a campaign destroys its player display" do
    campaign = create(:campaign)
    player_display = create(:player_display, :with_current_image, campaign: campaign)

    campaign.destroy

    assert_nil PlayerDisplay.find_by(id: player_display.id)
  end
end
