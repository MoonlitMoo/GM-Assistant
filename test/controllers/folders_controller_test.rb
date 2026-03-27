require "test_helper"

class FoldersControllerTest < ActionDispatch::IntegrationTest
  test "shows the new folder form" do
    campaign = create(:campaign)
    parent = campaign.root_folder

    get new_folder_folder_path(parent)

    assert_response :success
    assert_includes response.body, "New Folder"
    assert_includes response.body, parent.name
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

  test "updates a folder" do
    folder = create(:folder, name: "Villagers")

    patch folder_path(folder), params: {
      folder: {
        name: "Villains"
      }
    }

    assert_redirected_to folder_path(folder)
    folder.reload
    assert_equal "Villains", folder.name
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
