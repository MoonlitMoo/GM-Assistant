require "test_helper"

class AlbumsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
    sign_in(@user)
  end

  test "shows an album with breadcrumb context, actions, and thumbnail grid" do
    campaign = create(:campaign, user: @user, name: "Shattered Coast")
    campaign.root_folder.update!(name: "Archive Root")
    parent_folder = create(:folder, campaign: campaign, parent: campaign.root_folder, name: "Harbour")
    folder = create(:folder, campaign: campaign, parent: parent_folder, name: "Tide Charts")
    album = create(:album, campaign: campaign, folder: folder, name: "Storm Sketches")
    first_image = create(:image, campaign: campaign, album: album, title: "Anchor Watch", position: 1)
    second_image = create(:image, campaign: campaign, album: album, title: "Breakwater", position: 2)
    create(:player_display, campaign: campaign, current_image: first_image)

    get album_path(album)

    assert_response :success
    assert_includes response.body, "Storm Sketches"
    assert_includes response.body, "Upload image"
    assert_includes response.body, "Edit album"
    assert_includes response.body, "Delete album"
    assert_includes response.body, first_image.title
    assert_includes response.body, second_image.title
    assert_includes response.body, "Presenting"
    assert_match(%r{href="#{image_path(first_image)}"}, response.body)
    assert_match(%r{href="#{image_path(second_image)}"}, response.body)
    assert_match(%r{data-controller="player-display"}, response.body)
    assert_match(%r{#{present_campaign_player_display_path(campaign)}}, response.body)
    assert_match(%r{data-player-display-image-id="#{first_image.id}"}, response.body)
    assert_match(%r{data-player-display-image-id="#{second_image.id}"}, response.body)
    assert_match(%r{rails/active_storage/representations}, response.body)
    assert_operator response.body.index(first_image.title), :<, response.body.index(second_image.title)
    assert_match(
      /Shattered Coast<\/a>\s*&rsaquo;\s*<a[^>]*>Harbour<\/a>\s*&rsaquo;\s*<a[^>]*>Tide Charts<\/a>\s*&rsaquo;\s*<span>Storm Sketches<\/span>/,
      response.body
    )
    assert_no_match(/Archive Root/, response.body)
  end

  test "shows an album inside the content frame for turbo frame requests" do
    album = create(:album, campaign: create(:campaign, user: @user), name: "Storm Sketches")

    get album_path(album), headers: { "Turbo-Frame" => "content-body" }

    assert_response :success
    assert_match(/<turbo-frame[^>]*id="content-body"/, response.body)
    assert_includes response.body, 'data-turbo-action="advance"'
    assert_includes response.body, "Storm Sketches"
    assert_includes response.body, "Upload image"
  end

  test "shows the new album form" do
    folder = create(:folder, campaign: create(:campaign, user: @user), name: "Landmarks")

    get new_folder_album_path(folder)

    assert_response :success
    assert_includes response.body, "New Album"
    assert_includes response.body, "Landmarks"
  end

  test "shows the new album form from the top-level helper with folder_id" do
    folder = create(:folder, campaign: create(:campaign, user: @user), name: "Landmarks")

    get new_album_path(folder_id: folder.id)

    assert_response :success
    assert_includes response.body, "New Album"
    assert_includes response.body, "Landmarks"
  end

  test "re-renders the new album form when creation is invalid" do
    folder = create(:folder, campaign: create(:campaign, user: @user))

    assert_no_difference("Album.count") do
      post folder_albums_path(folder), params: {
        album: {
          name: nil,
          description: "No title yet"
        }
      }
    end

    assert_response :unprocessable_entity
    assert_includes response.body, "New Album"
    assert_includes html_response_body, "Name can't be blank"
  end

  test "creates an album and redirects to the created album even when return_to is supplied" do
    campaign = create(:campaign, user: @user, name: "Shattered Coast")
    folder = create(:folder, campaign: campaign, parent: campaign.root_folder, name: "Harbour")

    assert_difference("Album.count", 1) do
      post folder_albums_path(folder), params: {
        album: {
          name: "Storm Sketches"
        },
        return_to: campaign_path(campaign)
      }
    end

    album = Album.find_by!(name: "Storm Sketches", folder: folder)
    assert_redirected_to album_path(album)
  end

  test "re-renders the new album form when creation is invalid and preserves return_to" do
    campaign = create(:campaign, user: @user, name: "Shattered Coast")
    folder = create(:folder, campaign: campaign, parent: campaign.root_folder, name: "Harbour")

    assert_no_difference("Album.count") do
      post folder_albums_path(folder), params: {
        album: {
          name: nil
        },
        return_to: campaign_path(campaign)
      }
    end

    assert_response :unprocessable_entity
    assert_includes response.body, "New Album"
    assert_match(%r{href="#{campaign_path(campaign)}"[^>]*>Cancel<}, response.body)
    assert_match(%r{name="return_to"[^>]*value="#{campaign_path(campaign)}"}, response.body)
  end

  test "shows the edit album form" do
    album = create(:album, campaign: create(:campaign, user: @user), name: "Gallery")

    get edit_album_path(album)

    assert_response :success
    assert_includes response.body, "Edit Album"
    assert_includes response.body, "Gallery"
    assert_match(%r{href="#{album_path(album.id)}"[^>]*>Cancel<}, response.body)
  end

  test "updates an album" do
    album = create(:album, campaign: create(:campaign, user: @user), name: "Old Gallery", description: "Old notes")

    patch album_path(album), params: {
      album: {
        name: "New Gallery",
        description: "Fresh notes"
      }
    }

    album.reload
    assert_redirected_to album_path(album)
    assert_equal "New Gallery", album.name
    assert_equal "Fresh notes", album.description
  end

  test "updates an album via json" do
    album = create(:album, campaign: create(:campaign, user: @user), name: "Old Gallery")

    patch album_path(album), params: {
      album: {
        name: "New Gallery"
      }
    }, as: :json

    assert_response :ok
    assert_equal "application/json", response.media_type
    album.reload

    payload = JSON.parse(response.body)
    assert_equal album.id, payload["id"]
    assert_equal "New Gallery", payload["name"]
    assert_equal album_path(album), payload["url"]
  end

  test "updating an album moves its campaign to the top of recent activity" do
    campaign = create(:campaign, user: @user, name: "Shattered Coast")
    other_campaign = create(:campaign, user: @user, name: "Moonwake Atlas")
    album = create(:album, campaign: campaign, name: "Storm Sketches")
    campaign.update_columns(updated_at: 3.days.ago)
    other_campaign.update_columns(updated_at: 1.day.ago)

    patch album_path(album), params: {
      album: {
        name: "Storm Sketches Revised"
      }
    }

    album.reload
    assert_redirected_to album_path(album)

    get campaigns_path

    assert_response :success
    assert_operator response.body.index(campaign.name), :<, response.body.index(other_campaign.name)
  end

  test "re-renders the edit album form when the update is invalid" do
    album = create(:album, campaign: create(:campaign, user: @user))

    patch album_path(album), params: {
      album: {
        name: nil
      }
    }

    assert_response :unprocessable_entity
    assert_includes response.body, "Edit Album"
    assert_includes html_response_body, "Name can't be blank"
  end

  test "returns json errors when an album update is invalid" do
    album = create(:album, campaign: create(:campaign, user: @user))

    patch album_path(album), params: {
      album: {
        name: nil
      }
    }, as: :json

    assert_response :unprocessable_entity
    assert_equal "application/json", response.media_type
    assert_equal [ "Name can't be blank" ], JSON.parse(response.body)["errors"]
  end

  test "destroys an album and returns to its folder" do
    campaign = create(:campaign, user: @user)
    folder = create(:folder, campaign: campaign, parent: campaign.root_folder, name: "Harbour")
    album = create(:album, campaign: campaign, folder: folder, name: "Storm Sketches")

    assert_difference("Album.count", -1) do
      delete album_path(album)
    end

    assert_redirected_to folder_path(folder)
    assert_nil Album.find_by(id: album.id)
  end

  test "destroys a top-level album and returns to the campaign" do
    campaign = create(:campaign, user: @user)
    album = create(:album, campaign: campaign, folder: campaign.root_folder, name: "Storm Sketches")

    assert_difference("Album.count", -1) do
      delete album_path(album)
    end

    assert_redirected_to campaign_path(campaign)
    assert_nil Album.find_by(id: album.id)
  end

  test "destroys a top-level album via json and returns a redirect url for the campaign" do
    campaign = create(:campaign, user: @user)
    album = create(:album, campaign: campaign, folder: campaign.root_folder, name: "Storm Sketches")

    assert_difference("Album.count", -1) do
      delete album_path(album), as: :json
    end

    assert_response :ok
    assert_equal "application/json", response.media_type
    assert_equal campaign_path(campaign), JSON.parse(response.body)["redirect_url"]
    assert_nil Album.find_by(id: album.id)
  end
end
