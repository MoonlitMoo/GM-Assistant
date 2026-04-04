require "test_helper"

class CampaignFlowsTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
    sign_in(@user)
  end

  test "creating a campaign creates its root folder" do
    assert_difference("Campaign.count", 1) do
      assert_difference("Folder.where(is_root: true).count", 1) do
        post campaigns_path, params: {
          campaign: {
            name: "The Southern Wilds",
            description: "A windswept campaign"
          }
        }
      end
    end

    campaign = Campaign.order(:created_at).last

    assert_redirected_to campaign_path(campaign)
    assert_not_nil campaign.root_folder
    assert_equal campaign.id, campaign.root_folder.campaign_id
    assert_predicate campaign.root_folder, :is_root?
    assert_equal "Root", campaign.root_folder.name

    follow_redirect!
    assert_response :success
    assert_includes response.body, "The Southern Wilds"
    assert_includes response.body, "No folders at the top level yet."
  end

  test "creating a child folder keeps it inside the same campaign" do
    campaign = create(:campaign, user: @user)
    parent = campaign.root_folder

    assert_difference("Folder.count", 1) do
      post folder_folders_path(parent), params: {
        folder: {
          name: "NPCs"
        }
      }
    end

    folder = Folder.order(:created_at).last

    assert_redirected_to folder_path(parent)
    assert_equal campaign.id, folder.campaign_id
    assert_equal parent.id, folder.parent_id
    assert_equal "NPCs", folder.name

    follow_redirect!
    assert_response :success
    assert_includes response.body, "NPCs"
  end

  test "creating an album nests it under the chosen folder" do
    campaign = create(:campaign, user: @user)
    folder = create(:folder, campaign: campaign, parent: campaign.root_folder, name: "Locations")

    assert_difference("Album.count", 1) do
      post folder_albums_path(folder), params: {
        album: {
          name: "Harbour Sketches",
          description: "Reference art for the port"
        }
      }
    end

    album = Album.order(:created_at).last

    assert_redirected_to album_path(album)
    assert_equal campaign.id, album.campaign_id
    assert_equal folder.id, album.folder_id
    assert_equal "Harbour Sketches", album.name

    follow_redirect!
    assert_response :success
    assert_includes response.body, "Harbour Sketches"
    assert_includes response.body, "Locations"
  end

  test "uploading an image attaches the file to the album" do
    album = create(:album, campaign: create(:campaign, user: @user))

    assert_difference("Image.count", 1) do
      post album_images_path(album), params: {
        image: {
          title: "Old lighthouse",
          notes: "A moody coastal reference",
          file: uploaded_test_image
        }
      }
    end

    image = Image.order(:created_at).last

    assert_redirected_to album_path(album)
    assert_equal album.id, image.album_id
    assert_equal album.campaign_id, image.campaign_id
    assert_predicate image.file, :attached?
    assert_equal "test_image.jpg", image.file.filename.to_s
    assert_equal "image/jpeg", image.file.blob.content_type

    follow_redirect!
    assert_response :success
    assert_includes response.body, "Old lighthouse"
  end

  test "cross-campaign album association attempts are rejected" do
    campaign = create(:campaign, user: @user)
    other_campaign = create(:campaign, user: @user)
    folder = create(:folder, campaign: campaign, parent: campaign.root_folder)

    # The nested folder is the source of truth, so the forged campaign id is rejected.
    assert_difference("Album.count", 1) do
      post folder_albums_path(folder), params: {
        album: {
          name: "Secret Notes",
          campaign_id: other_campaign.id
        }
      }
    end

    album = Album.order(:created_at).last

    assert_redirected_to album_path(album)
    assert_equal campaign.id, album.campaign_id
    assert_equal folder.id, album.folder_id
    assert_not_equal other_campaign.id, album.campaign_id
  end

  private

  # This helper keeps the flow tests focussed on application behaviour.
  def uploaded_test_image
    Rack::Test::UploadedFile.new(
      Rails.root.join("test/fixtures/files/test_image.jpg"),
      "image/jpeg"
    )
  end
end
