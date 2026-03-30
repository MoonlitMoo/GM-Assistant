require "test_helper"

class PlayerDisplaysControllerTest < ActionDispatch::IntegrationTest
  include ActionCable::TestHelper

  test "present creates the campaign player display, broadcasts the image, and returns json" do
    image = create(:image)
    expected_payload = {
      "image_url" => rails_blob_url(image.file, host: "www.example.com"),
      "image_id" => image.id
    }

    assert_difference("PlayerDisplay.count", 1) do
      assert_broadcast_on("player_display_#{image.campaign_id}", expected_payload) do
        patch present_campaign_player_display_path(image.campaign),
              params: { current_image_id: image.id },
              as: :json
      end
    end

    assert_response :success
    assert_equal expected_payload, JSON.parse(response.body)

    player_display = image.campaign.reload.player_display
    assert_not_nil player_display
    assert_equal image.id, player_display.current_image_id
  end

  test "present rejects images from another campaign" do
    campaign = create(:campaign)
    image = create(:image)

    assert_no_difference("PlayerDisplay.count") do
      assert_broadcasts("player_display_#{campaign.id}", 0) do
        patch present_campaign_player_display_path(campaign),
              params: { current_image_id: image.id },
              as: :json
      end
    end

    assert_response :unprocessable_entity
    assert_includes JSON.parse(response.body).fetch("errors"), "Current image must belong to same campaign"
  end

  test "clear clears the current image, broadcasts the change, and returns json" do
    player_display = create(:player_display, :with_current_image)

    assert_broadcast_on("player_display_#{player_display.campaign_id}", { "cleared" => true }) do
      patch clear_campaign_player_display_path(player_display.campaign), as: :json
    end

    assert_response :success
    assert_equal({ "cleared" => true }, JSON.parse(response.body))
    assert_nil player_display.reload.current_image
  end
end
