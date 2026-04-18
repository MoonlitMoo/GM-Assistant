require "test_helper"

class PlayerDisplayChannelTest < ActionCable::Channel::TestCase
  test "subscribing with a valid campaign id creates a confirmed subscription" do
    campaign = create(:campaign)

    subscribe campaign_id: campaign.id

    assert subscription.confirmed?
  end

  test "subscribing streams from the campaign player display stream" do
    campaign = create(:campaign)

    subscribe campaign_id: campaign.id

    assert_has_stream "player_display_#{campaign.id}"
  end
end
