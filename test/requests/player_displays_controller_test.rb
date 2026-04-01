require "test_helper"

class PlayerDisplaysControllerTest < ActionDispatch::IntegrationTest
  include ActionCable::TestHelper

  test "present with a valid image sets current image id and returns json" do
    image = create(:image)
    player_display = create(:player_display, campaign: image.campaign)
    expected_payload = {
      "image_url" => rails_blob_url(image.file, host: "www.example.com"),
      "image_id" => image.id
    }

    assert_no_difference("PlayerDisplay.count") do
      assert_broadcast_on("player_display_#{image.campaign_id}", expected_payload) do
        patch present_campaign_player_display_path(image.campaign),
              params: { current_image_id: image.id },
              as: :json
      end
    end

    assert_response :success
    assert_equal expected_payload, JSON.parse(response.body)
    assert_equal image.id, player_display.reload.current_image_id
  end

  test "present lazily creates the player display if one does not exist" do
    image = create(:image)

    assert_nil image.campaign.player_display

    assert_difference("PlayerDisplay.count", 1) do
      patch present_campaign_player_display_path(image.campaign),
            params: { current_image_id: image.id },
            as: :json
    end

    assert_response :success

    player_display = image.campaign.reload.player_display
    assert_not_nil player_display
    assert_equal image.id, player_display.current_image_id
  end

  test "present turbo stream updates the topbar status" do
    image = create(:image)
    create(:player_display, campaign: image.campaign)

    patch present_campaign_player_display_path(image.campaign),
          params: { current_image_id: image.id },
          headers: { "Accept" => Mime[:turbo_stream].to_s }

    assert_response :success
    assert_equal Mime[:turbo_stream].to_s, response.media_type
    assert_includes response.body, 'target="topbar-status"'
    assert_includes response.body, image.title
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

  test "clear turbo stream clears the topbar status" do
    player_display = create(:player_display, :with_current_image)

    patch clear_campaign_player_display_path(player_display.campaign),
          headers: { "Accept" => Mime[:turbo_stream].to_s }

    assert_response :success
    assert_equal Mime[:turbo_stream].to_s, response.media_type
    assert_includes response.body, 'target="topbar-status"'
    assert_includes response.body, 'class="topbar-status-frame is-empty"'
  end

  test "clear when no player display exists does not crash" do
    campaign = create(:campaign)

    assert_no_difference("PlayerDisplay.count") do
      assert_broadcast_on("player_display_#{campaign.id}", { "cleared" => true }) do
        patch clear_campaign_player_display_path(campaign), as: :json
      end
    end

    assert_response :success
    assert_equal({ "cleared" => true }, JSON.parse(response.body))
    assert_nil campaign.reload.player_display
  end

  test "player show returns 200 for a valid campaign" do
    campaign = create(:campaign)

    get player_campaign_path(campaign)

    assert_response :success
    assert_includes response.body, 'id="player-screen"'
    assert_includes response.body, %(data-campaign-id="#{campaign.id}")
  end
end
