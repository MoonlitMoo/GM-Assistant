require "test_helper"

class CampaignsControllerTest < ActionDispatch::IntegrationTest
  test "shows a campaign with breadcrumb context" do
    campaign = create(:campaign, name: "North Reach", description: "A weathered coastal frontier.")
    root_folder = campaign.root_folder
    create(:folder, campaign: campaign, parent: root_folder, name: "Locations")
    album = create(:album, campaign: campaign, folder: root_folder, name: "Harbour Sketches")
    oldest_image = create(:image, campaign: campaign, album: album, title: "Old Lantern")
    oldest_image.update_columns(created_at: 6.days.ago)

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
    assert_includes response.body, "Recently Added"
    assert_includes response.body, "Locations"
    assert_includes response.body, "Harbour Sketches"
    assert_includes response.body, "Recent Image 1"
    assert_includes response.body, "Recent Image 5"
    assert_no_match(/Old Lantern/, response.body)
    assert_no_match(%r{href="#{folder_path(root_folder)}"}, response.body)
    assert_match(
      /<nav aria-label="Breadcrumbs">\s*<span>North Reach<\/span>\s*<\/nav>/,
      response.body
    )
  end

  test "shows the campaign index" do
    first_campaign = create(:campaign, name: "North Reach")
    second_campaign = create(:campaign, name: "Southern Isles")

    get campaigns_path

    assert_response :success
    assert_includes response.body, "Campaigns"
    assert_includes response.body, "New Campaign"
    assert_includes response.body, "North Reach"
    assert_includes response.body, "Southern Isles"
    assert_match(%r{href="#{edit_campaign_path(first_campaign)}"}, response.body)
    assert_match(%r{href="#{campaign_path(second_campaign)}"}, response.body)
    assert_includes response.body, 'data-turbo-confirm="Delete this campaign?"'
  end

  test "shows the new campaign form" do
    get new_campaign_path

    assert_response :success
    assert_includes response.body, "New Campaign"
    assert_includes response.body, "Create Campaign"
    assert_match(%r{href="#{campaigns_path}"[^>]*>Cancel<}, response.body)
  end

  test "shows the edit campaign form" do
    campaign = create(:campaign, name: "North Reach")

    get edit_campaign_path(campaign)

    assert_response :success
    assert_includes response.body, "Edit Campaign"
    assert_includes response.body, "Save Campaign"
    assert_match(%r{href="#{campaign_path(campaign)}"[^>]*>Cancel<}, response.body)
  end

  test "returns the campaign tree as nested json" do
    campaign = create(:campaign, name: "North Reach")
    root_folder = campaign.root_folder
    child_folder = create(:folder, campaign: campaign, parent: root_folder, name: "Locations")
    create(:album, campaign: campaign, folder: child_folder, name: "Harbour Sketches")

    get tree_campaign_path(campaign)

    assert_response :success
    payload = JSON.parse(response.body)

    assert_equal root_folder.id, payload["id"]
    assert_equal campaign.id, payload["campaignId"]
    assert_equal root_folder.name, payload["name"]
    assert_equal folder_path(root_folder), payload["url"]

    child_payload = payload.fetch("folders").find { |folder| folder["id"] == child_folder.id }
    assert_equal child_folder.name, child_payload["name"]
    assert_equal folder_path(child_folder), child_payload["url"]
    assert_equal "Harbour Sketches", child_payload.dig("albums", 0, "name")
    assert_equal album_path(child_folder.albums.first), child_payload.dig("albums", 0, "url")
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
    campaign = create(:campaign, name: "Old Name", description: "Old notes")

    patch campaign_path(campaign), params: {
      campaign: {
        name: "New Name",
        description: "Fresh notes"
      }
    }

    assert_redirected_to campaign_path(campaign)
    campaign.reload
    assert_equal "New Name", campaign.name
    assert_equal "Fresh notes", campaign.description
  end

  test "re-renders the edit campaign form when the update is invalid" do
    campaign = create(:campaign)

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
    campaign = create(:campaign)

    assert_difference("Campaign.count", -1) do
      delete campaign_path(campaign)
    end

    assert_redirected_to campaigns_path
    assert_nil Campaign.find_by(id: campaign.id)
  end
end
