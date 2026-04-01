require "test_helper"

class PlayerDisplaysControllerTest < ActionDispatch::IntegrationTest
  include ActionCable::TestHelper

  test "present with a valid image sets current image id and returns json" do
    image = create(:image, show_title: false)
    player_display = create(:player_display, campaign: image.campaign, transition_type: :instant)
    expected_payload = {
      "image_url" => rails_blob_url(image.file, host: "www.example.com"),
      "image_id" => image.id,
      "image_title" => image.title,
      "show_title" => false,
      "transition_type" => "instant"
    }

    assert_no_difference("PresentationEvent.count") do
      assert_no_difference("PlayerDisplay.count") do
        assert_broadcast_on("player_display_#{image.campaign_id}", expected_payload) do
          patch present_campaign_player_display_path(image.campaign),
                params: { current_image_id: image.id },
                as: :json
        end
      end
    end

    assert_response :success
    assert_equal expected_payload, JSON.parse(response.body)
    assert_equal image.id, player_display.reload.current_image_id
    assert_equal false, player_display.show_title
  end

  test "present sets player display show title from image show title" do
    image = create(:image, show_title: false)
    player_display = create(:player_display, campaign: image.campaign, show_title: true)

    patch present_campaign_player_display_path(image.campaign),
          params: { current_image_id: image.id },
          as: :json

    assert_response :success
    assert_equal false, player_display.reload.show_title
  end

  test "present changing the image creates a presentation event for the previously shown image" do
    previous_image = create(:image)
    next_image = create(:image, campaign: previous_image.campaign)
    create(:player_display, campaign: previous_image.campaign, current_image: previous_image)

    assert_difference("PresentationEvent.count", 1) do
      patch present_campaign_player_display_path(previous_image.campaign),
            params: { current_image_id: next_image.id },
            as: :json
    end

    assert_response :success

    presentation_event = PresentationEvent.order(:created_at).last
    assert_equal previous_image.campaign, presentation_event.campaign
    assert_equal previous_image, presentation_event.image
    assert_equal "presented", presentation_event.event_type
    assert_equal previous_image.title, presentation_event.image_title
  end

  test "present lazily creates the player display if one does not exist" do
    image = create(:image)

    assert_nil image.campaign.player_display

    assert_no_difference("PresentationEvent.count") do
      assert_difference("PlayerDisplay.count", 1) do
        patch present_campaign_player_display_path(image.campaign),
              params: { current_image_id: image.id },
              as: :json
      end
    end

    assert_response :success

    player_display = image.campaign.reload.player_display
    assert_not_nil player_display
    assert_equal image.id, player_display.current_image_id
  end

  test "presenting the same image is ignored and does not create a presentation event" do
    player_display = create(:player_display, :with_current_image)
    image = player_display.current_image
    expected_payload = {
      "image_url" => rails_blob_url(image.file, host: "www.example.com"),
      "image_id" => image.id,
      "image_title" => image.title,
      "show_title" => false,
      "transition_type" => "crossfade"
    }

    assert_no_difference("PresentationEvent.count") do
      assert_broadcasts("player_display_#{player_display.campaign_id}", 0) do
        patch present_campaign_player_display_path(player_display.campaign),
              params: { current_image_id: image.id },
              as: :json
      end
    end

    assert_response :success
    assert_equal expected_payload, JSON.parse(response.body)
    assert_equal image.id, player_display.reload.current_image_id
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

    assert_no_difference("PresentationEvent.count") do
      assert_no_difference("PlayerDisplay.count") do
        assert_broadcasts("player_display_#{campaign.id}", 0) do
          patch present_campaign_player_display_path(campaign),
                params: { current_image_id: image.id },
                as: :json
        end
      end
    end

    assert_response :unprocessable_entity
    assert_includes JSON.parse(response.body).fetch("errors"), "Current image must belong to same campaign"
  end

  test "clear clears the current image, broadcasts the change, and returns json" do
    player_display = create(:player_display, :with_current_image)
    previous_image = player_display.current_image

    assert_difference("PresentationEvent.count", 2) do
      assert_broadcast_on("player_display_#{player_display.campaign_id}", { "cleared" => true }) do
        patch clear_campaign_player_display_path(player_display.campaign), as: :json
      end
    end

    assert_response :success
    assert_equal({ "cleared" => true }, JSON.parse(response.body))
    assert_nil player_display.reload.current_image

    presented_event = PresentationEvent.presented.order(:created_at).last
    cleared_event = PresentationEvent.cleared.order(:created_at).last

    assert_equal player_display.campaign, presented_event.campaign
    assert_equal previous_image, presented_event.image
    assert_equal previous_image.title, presented_event.image_title

    assert_equal player_display.campaign, cleared_event.campaign
    assert_nil cleared_event.image
    assert_nil cleared_event.image_title
  end

  test "clear creates a presentation event with event type cleared" do
    player_display = create(:player_display, :with_current_image)

    assert_difference("PresentationEvent.count", 2) do
      patch clear_campaign_player_display_path(player_display.campaign), as: :json
    end

    assert_response :success

    presentation_event = PresentationEvent.cleared.order(:created_at).last
    assert_equal player_display.campaign, presentation_event.campaign
    assert_equal "cleared", presentation_event.event_type
    assert_nil presentation_event.image
    assert_nil presentation_event.image_title
  end

  test "toggle title flips show title and returns turbo stream" do
    player_display = create(:player_display, :with_current_image, show_title: true)

    assert_broadcast_on("player_display_#{player_display.campaign_id}", { "show_title" => false }) do
      patch toggle_title_campaign_path(player_display.campaign),
            headers: { "Accept" => Mime[:turbo_stream].to_s }
    end

    assert_response :success
    assert_equal Mime[:turbo_stream].to_s, response.media_type
    assert_equal false, player_display.reload.show_title
    assert_includes response.body, 'target="gm-panel-header"'
    assert_includes response.body, 'target="gm-status"'
  end

  test "update transition updates transition type and returns turbo stream" do
    player_display = create(:player_display, :with_current_image, transition_type: :crossfade)

    patch update_transition_campaign_path(player_display.campaign),
          params: { transition_type: "instant" },
          headers: { "Accept" => Mime[:turbo_stream].to_s }

    assert_response :success
    assert_equal Mime[:turbo_stream].to_s, response.media_type
    assert_equal "instant", player_display.reload.transition_type
    assert_includes response.body, 'target="gm-status"'
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

    assert_difference("PresentationEvent.count", 1) do
      assert_no_difference("PlayerDisplay.count") do
        assert_broadcast_on("player_display_#{campaign.id}", { "cleared" => true }) do
          patch clear_campaign_player_display_path(campaign), as: :json
        end
      end
    end

    assert_response :success
    assert_equal({ "cleared" => true }, JSON.parse(response.body))
    assert_nil campaign.reload.player_display

    presentation_event = PresentationEvent.order(:created_at).last
    assert_equal campaign, presentation_event.campaign
    assert_equal "cleared", presentation_event.event_type
  end

  test "player show returns 200 for a valid campaign" do
    campaign = create(:campaign)

    get player_campaign_path(campaign)

    assert_response :success
    assert_includes response.body, 'id="player-screen"'
    assert_includes response.body, %(data-campaign-id="#{campaign.id}")
    assert_includes response.body, 'data-show-title="false"'
    assert_includes response.body, 'data-transition-type="crossfade"'
  end
end
