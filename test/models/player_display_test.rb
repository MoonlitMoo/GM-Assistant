require "test_helper"

class PlayerDisplayTest < ActiveSupport::TestCase
  test "is valid with a campaign and current image from the same campaign" do
    player_display = build(:player_display, :with_current_image)

    assert player_display.valid?
  end

  test "is valid without a current image" do
    player_display = build(:player_display)

    assert player_display.valid?
  end

  test "is invalid without a campaign" do
    player_display = build(:player_display, campaign: nil)

    assert_not player_display.valid?
    assert_includes player_display.errors[:campaign], "must exist"
  end

  test "is invalid when the campaign already has a player display" do
    campaign = create(:campaign)
    create(:player_display, campaign: campaign)
    player_display = build(:player_display, campaign: campaign)

    assert_not player_display.valid?
    assert_includes player_display.errors[:campaign_id], "has already been taken"
  end

  test "is invalid when current image belongs to another campaign" do
    player_display = build(:player_display, campaign: create(:campaign), current_image: create(:image))

    assert_not player_display.valid?
    assert_includes player_display.errors[:current_image_id], "must belong to same campaign"
  end
end
