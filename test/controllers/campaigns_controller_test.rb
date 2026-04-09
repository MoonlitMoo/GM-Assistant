require "test_helper"

class CampaignsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
    sign_in(@user)
  end

  test "shows a campaign with breadcrumb context" do
    campaign = create(:campaign, user: @user, name: "North Reach", description: "A weathered coastal frontier.")
    root_folder = campaign.root_folder
    create(:folder, campaign: campaign, parent: root_folder, name: "Locations")
    album = create(:album, campaign: campaign, folder: root_folder, name: "Harbour Sketches")
    oldest_image = create(:image, campaign: campaign, album: album, title: "Old Lantern")
    oldest_image.update_columns(created_at: 6.days.ago)
    create(:presentation_event, campaign: campaign, image: oldest_image, image_title: oldest_image.title)

    5.times do |index|
      image = create(:image, campaign: campaign, album: album, title: "Recent Image #{index + 1}")
      image.update_columns(created_at: (5 - index).days.ago)
    end

    get campaign_path(campaign)

    assert_response :success
    assert_includes response.body, "North Reach"
    assert_includes response.body, "A weathered coastal frontier."
    assert_includes response.body, "Total albums"
    assert_includes response.body, "Total images"
    assert_includes response.body, "Recently shown"
    assert_includes response.body, "Recently Added"
    assert_includes response.body, "Locations"
    assert_includes response.body, "Harbour Sketches"
    assert_includes response.body, "Old Lantern"
    assert_includes response.body, "Recent Image 1"
    assert_includes response.body, "Recent Image 5"
    assert_no_match(/<div class="recent-list">.*Old Lantern/m, response.body)
    assert_no_match(%r{href="#{folder_path(root_folder)}"}, response.body)
    assert_includes response.body, new_folder_folder_path(root_folder, return_to: campaign_path(campaign))
    assert_includes response.body, new_folder_album_path(root_folder, return_to: campaign_path(campaign))
    assert_includes response.body, 'id="topbar-status"'
    assert_includes response.body, 'class="topbar-status-frame is-empty"'
    assert_includes response.body, player_campaign_path(campaign)
    assert_includes response.body, "Not showing"
    assert_match(
      /<nav aria-label="Breadcrumbs">\s*<span>North Reach<\/span>\s*<\/nav>/,
      response.body
    )
    assert_equal 1, response.body.scan("data-breadcrumbs-payload").size
  end

  test "shows dashboard create actions even when top-level sections are empty" do
    campaign = create(:campaign, user: @user, name: "North Reach")
    root_folder = campaign.root_folder

    get campaign_path(campaign)

    assert_response :success
    assert_includes response.body, "No folders at the top level yet."
    assert_includes response.body, "No albums at the top level yet."
    assert_includes response.body, new_folder_folder_path(root_folder, return_to: campaign_path(campaign))
    assert_includes response.body, new_folder_album_path(root_folder, return_to: campaign_path(campaign))
  end

  test "shows the campaign index" do
    first_campaign = create(:campaign, user: @user, name: "North Reach")
    second_campaign = create(:campaign, user: @user, name: "Southern Isles")

    get campaigns_path

    assert_response :success
    assert_includes response.body, "Campaigns"
    assert_includes response.body, "New Campaign"
    assert_includes response.body, "North Reach"
    assert_includes response.body, "Southern Isles"
    assert_includes response.body, edit_campaign_path(first_campaign)
    assert_match(%r{href="#{campaign_path(second_campaign)}"}, response.body)
    assert_includes response.body, 'data-turbo-confirm="Delete this campaign?"'
  end

  test "orders campaigns by recent activity" do
    older_campaign = create(:campaign, user: @user, name: "North Reach")
    newer_campaign = create(:campaign, user: @user, name: "Southern Isles")
    older_campaign.update_columns(updated_at: 3.days.ago)
    newer_campaign.update_columns(updated_at: 1.day.ago)

    get campaigns_path

    assert_response :success
    assert_operator response.body.index(newer_campaign.name), :<, response.body.index(older_campaign.name)
  end

  test "showing a campaign moves it to the top of recent activity" do
    older_campaign = create(:campaign, user: @user, name: "North Reach")
    newer_campaign = create(:campaign, user: @user, name: "Southern Isles")
    older_campaign.update_columns(updated_at: 3.days.ago)
    newer_campaign.update_columns(updated_at: 1.day.ago)

    get campaign_path(older_campaign)
    get campaigns_path

    assert_response :success
    assert_operator response.body.index(older_campaign.name), :<, response.body.index(newer_campaign.name)
  end

  test "shows the new campaign form" do
    get new_campaign_path

    assert_response :success
    assert_includes response.body, "New Campaign"
    assert_includes response.body, "Create Campaign"
    assert_match(%r{href="#{campaigns_path}"[^>]*>Cancel<}, response.body)
  end

  test "shows the edit campaign form" do
    campaign = create(:campaign, user: @user, name: "North Reach")

    get edit_campaign_path(campaign)

    assert_response :success
    assert_includes response.body, "Edit Campaign"
    assert_includes response.body, "Save Campaign"
    assert_match(%r{href="#{campaign_path(campaign.id)}"[^>]*>Cancel<}, response.body)
  end

  test "shows the edit campaign form with the supplied return path" do
    campaign = create(:campaign, user: @user, name: "North Reach")

    get edit_campaign_path(campaign, return_to: campaigns_path)

    assert_response :success
    assert_match(%r{href="#{campaigns_path}"[^>]*>Cancel<}, response.body)
    assert_match(%r{name="return_to"[^>]*value="#{campaigns_path}"}, response.body)
  end

  test "returns the campaign tree as nested json" do
    campaign = create(:campaign, user: @user, name: "North Reach")
    root_folder = campaign.root_folder
    child_folder = create(:folder, campaign: campaign, parent: root_folder, name: "Locations")
    nested_folder = create(:folder, campaign: campaign, parent: child_folder, name: "Harbour")
    root_album = create(:album, campaign: campaign, folder: root_folder, name: "Campaign Notes")
    child_album = create(:album, campaign: campaign, folder: child_folder, name: "Harbour Sketches")
    nested_album = create(:album, campaign: campaign, folder: nested_folder, name: "Secret Routes")
    create(:image, campaign: campaign, album: root_album, title: "Root Image")
    create_list(:image, 2, campaign: campaign, album: child_album)
    create(:image, campaign: campaign, album: nested_album, title: "Nested Image")

    get tree_campaign_path(campaign)

    assert_response :success
    payload = JSON.parse(response.body)

    assert_equal root_folder.id, payload["id"]
    assert_equal campaign.id, payload["campaignId"]
    assert_equal root_folder.name, payload["name"]
    assert_equal folder_path(root_folder), payload["url"]
    assert_equal edit_folder_path(root_folder), payload["edit_url"]
    assert_equal new_folder_path(parent_id: root_folder.id), payload["new_subfolder_url"]
    assert_equal new_album_path(folder_id: root_folder.id), payload["new_album_url"]
    assert_equal 1, payload["child_folder_count"]
    assert_equal 1, payload["album_count"]
    assert_equal 1, payload["image_count"]
    assert_equal new_folder_path(parent_id: root_folder.id), payload["new_root_folder_url"]

    root_album_payload = payload.fetch("albums").find { |album| album["id"] == root_album.id }
    assert_equal root_album.name, root_album_payload["name"]
    assert_equal album_path(root_album), root_album_payload["url"]
    assert_equal edit_album_path(root_album), root_album_payload["edit_url"]
    assert_equal 1, root_album_payload["image_count"]

    child_payload = payload.fetch("folders").find { |folder| folder["id"] == child_folder.id }
    assert_equal child_folder.name, child_payload["name"]
    assert_equal folder_path(child_folder), child_payload["url"]
    assert_equal edit_folder_path(child_folder), child_payload["edit_url"]
    assert_equal new_folder_path(parent_id: child_folder.id), child_payload["new_subfolder_url"]
    assert_equal new_album_path(folder_id: child_folder.id), child_payload["new_album_url"]
    assert_equal 1, child_payload["child_folder_count"]
    assert_equal 1, child_payload["album_count"]
    assert_equal 2, child_payload["image_count"]

    child_album_payload = child_payload.fetch("albums").find { |album| album["id"] == child_album.id }
    assert_equal child_album.name, child_album_payload["name"]
    assert_equal album_path(child_album), child_album_payload["url"]
    assert_equal edit_album_path(child_album), child_album_payload["edit_url"]
    assert_equal 2, child_album_payload["image_count"]

    nested_payload = child_payload.fetch("folders").find { |folder| folder["id"] == nested_folder.id }
    assert_equal nested_folder.name, nested_payload["name"]
    assert_equal folder_path(nested_folder), nested_payload["url"]
    assert_equal 0, nested_payload["child_folder_count"]
    assert_equal 1, nested_payload["album_count"]
    assert_equal 1, nested_payload["image_count"]
  end

  test "re-renders the new campaign form when creation is invalid" do
    assert_no_difference("Campaign.count") do
      post campaigns_path, params: {
        campaign: {
          name: nil,
          description: "Missing a name"
        }
      }
    end

    assert_response :unprocessable_entity
    assert_includes response.body, "New Campaign"
    assert_includes html_response_body, "Name can't be blank"
  end

  test "updates a campaign" do
    campaign = create(:campaign, user: @user, name: "Old Name", description: "Old notes")

    patch campaign_path(campaign), params: {
      campaign: {
        name: "New Name",
        description: "Fresh notes"
      }
    }

    campaign.reload
    assert_redirected_to campaign_path(campaign)
    assert_equal "New Name", campaign.name
    assert_equal "Fresh notes", campaign.description
  end

  test "re-renders the edit campaign form when the update is invalid" do
    campaign = create(:campaign, user: @user)

    patch campaign_path(campaign), params: {
      campaign: {
        name: nil
      }
    }

    assert_response :unprocessable_entity
    assert_includes response.body, "Edit Campaign"
    assert_includes html_response_body, "Name can't be blank"
  end

  test "destroys a campaign" do
    campaign = create(:campaign, user: @user)

    assert_difference("Campaign.count", -1) do
      delete campaign_path(campaign)
    end

    assert_redirected_to campaigns_path
    assert_nil Campaign.find_by(id: campaign.id)
  end
end
