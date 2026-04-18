require "test_helper"

class PlayerDisplayTest < ActiveSupport::TestCase
  test "is valid with a campaign and current image from the same campaign" do
    player_display = build(:player_display, :with_current_image)

    assert player_display.valid?
  end

  test "transition type enum values are valid" do
    assert build(:player_display, transition_type: :crossfade).valid?
    assert build(:player_display, transition_type: :instant).valid?
  end

  test "show title defaults to false" do
    assert_equal false, build(:player_display).show_title
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

  test "destroying a campaign destroys its player display" do
    campaign = create(:campaign)
    player_display = create(:player_display, :with_current_image, campaign: campaign)

    campaign.destroy

    assert_nil PlayerDisplay.find_by(id: player_display.id)
  end
end
