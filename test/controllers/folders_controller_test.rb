require "test_helper"

class FoldersControllerTest < ActionDispatch::IntegrationTest
  test "shows a folder with breadcrumb context and omits the root folder" do
    campaign = create(:campaign, name: "Moonwake Atlas")
    campaign.root_folder.update!(name: "Archive Root")
    parent = create(:folder, campaign: campaign, parent: campaign.root_folder, name: "Districts")
    folder = create(:folder, campaign: campaign, parent: parent, name: "Villagers", description: "A ledger of ward residents.")
    create(:folder, campaign: campaign, parent: folder, name: "Market Square")
    create(:album, campaign: campaign, folder: folder, name: "Faces of the Ward", description: "Reference portraits")

    get folder_path(folder)

    assert_response :success
    assert_includes response.body, "Villagers"
    assert_includes response.body, "New Folder"
    assert_includes response.body, "New Album"
    assert_includes response.body, "Market Square"
    assert_includes response.body, "Faces of the Ward"
    assert_includes response.body, "A ledger of ward residents."
    assert_includes response.body, new_folder_folder_path(folder)
    assert_includes response.body, new_folder_album_path(folder)
    assert_match(
      /Moonwake Atlas<\/a>\s*&rsaquo;\s*<a[^>]*>Districts<\/a>\s*&rsaquo;\s*<span>Villagers<\/span>/,
      response.body
    )
    assert_no_match(/Archive Root/, response.body)
  end

  test "shows the root folder with only the campaign in breadcrumbs" do
    campaign = create(:campaign, name: "Moonwake Atlas")

    get folder_path(campaign.root_folder)

    assert_response :success
    breadcrumb_nav = response.body[/<nav aria-label="Breadcrumbs">.*?<\/nav>/m]

    assert_match(
      /<nav aria-label="Breadcrumbs">\s*<span>Moonwake Atlas<\/span>\s*<\/nav>/,
      breadcrumb_nav
    )
    assert_no_match(/>\s*Root\s*</, breadcrumb_nav)
  end

  test "showing a folder moves its campaign to the top of recent activity" do
    campaign = create(:campaign, name: "Moonwake Atlas")
    other_campaign = create(:campaign, name: "Shattered Coast")
    folder = create(:folder, campaign: campaign, parent: campaign.root_folder, name: "Villagers")
    campaign.update_columns(updated_at: 3.days.ago)
    other_campaign.update_columns(updated_at: 1.day.ago)

    get folder_path(folder)
    get campaigns_path

    assert_response :success
    assert_operator response.body.index(campaign.name), :<, response.body.index(other_campaign.name)
  end

  test "shows the new folder form" do
    campaign = create(:campaign)
    parent = campaign.root_folder

    get new_folder_folder_path(parent)

    assert_response :success
    assert_includes response.body, "New Folder"
    assert_includes response.body, "Description"
    assert_match(%r{href="#{folder_path(parent)}"[^>]*>Cancel<}, response.body)
  end

  test "re-renders the new folder form when creation is invalid" do
    campaign = create(:campaign)
    parent = campaign.root_folder

    assert_no_difference("Folder.count") do
      post folder_folders_path(parent), params: {
        folder: {
          name: nil
        }
      }
    end

    assert_response :unprocessable_entity
    assert_includes response.body, "New Folder"
    assert_includes html_response_body, "Name can't be blank"
  end

  test "shows the edit folder form" do
    folder = create(:folder, name: "Villagers")

    get edit_folder_path(folder)

    assert_response :success
    assert_includes response.body, "Edit Folder"
    assert_includes response.body, "Villagers"
    assert_match(%r{href="#{folder_path(folder)}"[^>]*>Cancel<}, response.body)
  end

  test "updates a folder" do
    folder = create(:folder, name: "Villagers")

    patch folder_path(folder), params: {
      folder: {
        name: "Villains",
        description: "New settlement notes"
      }
    }

    assert_redirected_to folder_path(folder)
    folder.reload
    assert_equal "Villains", folder.name
    assert_equal "New settlement notes", folder.description
  end

  test "re-renders the edit folder form when the update is invalid" do
    folder = create(:folder)

    patch folder_path(folder), params: {
      folder: {
        name: nil
      }
    }

    assert_response :unprocessable_entity
    assert_includes response.body, "Edit Folder"
    assert_includes html_response_body, "Name can't be blank"
  end

  test "destroys a folder and returns to its parent" do
    campaign = create(:campaign)
    parent = create(:folder, campaign: campaign, parent: campaign.root_folder, name: "Districts")
    folder = create(:folder, campaign: campaign, parent: parent, name: "Docks")

    assert_difference("Folder.count", -1) do
      delete folder_path(folder)
    end

    assert_redirected_to folder_path(parent)
    assert_nil Folder.find_by(id: folder.id)
  end
end
