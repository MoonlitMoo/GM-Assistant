require "test_helper"

class ImagesControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
    sign_in(@user)
  end

  test "shows an image" do
    campaign = create(:campaign, user: @user, name: "Shoreline Atlas")
    campaign.root_folder.update!(name: "Deep Vault")
    parent_folder = create(:folder, campaign: campaign, parent: campaign.root_folder, name: "Cliffside Sketches")
    folder = create(:folder, campaign: campaign, parent: parent_folder, name: "Sea Caves")
    album = create(:album, campaign: campaign, folder: folder, name: "Tidewall Studies")
    image = create(:image, campaign: campaign, album: album, title: "Beacon Cliffs", notes: "Windy and bright")
    create(:player_display, campaign: campaign, current_image: image)

    get image_path(image)

    assert_response :success
    assert_includes response.body, "Beacon Cliffs"
    assert_includes response.body, "Windy and bright"
    assert_includes response.body, "Presenting"
    assert_includes response.body, "Clear display"
    assert_includes response.body, "Edit image"
    assert_includes response.body, "Delete image"
    assert_match(%r{data-controller="player-display"}, response.body)
    assert_match(%r{#{present_campaign_player_display_path(campaign)}}, response.body)
    assert_match(%r{#{clear_campaign_player_display_path(campaign)}}, response.body)
    assert_match(
      /Shoreline Atlas<\/a>\s*&rsaquo;\s*<a[^>]*>Cliffside Sketches<\/a>\s*&rsaquo;\s*<a[^>]*>Sea Caves<\/a>\s*&rsaquo;\s*<a[^>]*>Tidewall Studies<\/a>\s*&rsaquo;\s*<span>Beacon Cliffs<\/span>/,
      response.body
    )
    assert_no_match(/Deep Vault/, response.body)
  end

  test "shows an image inside the content frame for turbo frame requests" do
    image = create(:image, campaign: create(:campaign, user: @user), title: "Beacon Cliffs")

    get image_path(image), headers: { "Turbo-Frame" => "content-body" }

    assert_response :success
    assert_match(/<turbo-frame[^>]*id="content-body"/, response.body)
    assert_includes response.body, 'data-turbo-action="advance"'
    assert_includes response.body, "Beacon Cliffs"
  end

  test "shows the new image form" do
    album = create(:album, campaign: create(:campaign, user: @user), name: "Weathered Maps")
    @user.default_show_title = true
    @user.save!

    get new_album_image_path(album)

    assert_response :success
    assert_includes response.body, "New Image"
    assert_includes response.body, "Description"
    assert_includes response.body, "Weathered Maps"
    assert_match(/name="image\[show_title\]".*checked="checked"/, response.body)
  end

  test "re-renders the new image form when creation is invalid" do
    album = create(:album, campaign: create(:campaign, user: @user), name: "Clues")

    assert_no_difference("Image.count") do
      post album_images_path(album), params: {
        image: {
          title: nil,
          notes: "Needs a title",
          file: uploaded_test_image
        }
      }
    end

    assert_response :unprocessable_entity
    assert_includes response.body, "New Image"
    assert_includes html_response_body, "Title can't be blank"
  end

  test "updates an image" do
    image = create(:image, campaign: create(:campaign, user: @user), title: "Old Title", notes: "Old notes")

    patch image_path(image), params: {
      image: {
        title: "New Title",
        notes: "Fresh notes"
      }
    }

    assert_redirected_to image_path(image)
    image.reload
    assert_equal "New Title", image.title
    assert_equal "Fresh notes", image.notes
  end

  test "updates an image via json" do
    image = create(:image, campaign: create(:campaign, user: @user), title: "Old Title", show_title: false)

    patch image_path(image), params: {
      image: {
        title: "New Title",
        show_title: true
      }
    }, as: :json

    assert_response :ok
    assert_equal "application/json", response.media_type
    image.reload

    payload = JSON.parse(response.body)
    assert_equal image.id, payload["id"]
    assert_equal "New Title", payload["title"]
    assert_equal true, payload["show_title"]
    assert_equal image_path(image), payload["url"]
    assert_equal edit_image_path(image), payload["edit_url"]
    assert_equal image_path(image), payload["delete_url"]
    assert_match(%r{rails/active_storage/representations}, payload["preview_url"])
  end

  test "re-renders the edit image form when the update is invalid" do
    image = create(:image, campaign: create(:campaign, user: @user))

    patch image_path(image), params: {
      image: {
        title: nil
      }
    }

    assert_response :unprocessable_entity
    assert_includes response.body, "Edit Image"
    assert_includes html_response_body, "Title can't be blank"
  end

  test "returns json errors when an image update is invalid" do
    image = create(:image, campaign: create(:campaign, user: @user))

    patch image_path(image), params: {
      image: {
        title: nil
      }
    }, as: :json

    assert_response :unprocessable_entity
    assert_equal "application/json", response.media_type
    assert_equal [ "Title can't be blank" ], JSON.parse(response.body)["errors"]
  end

  test "shows the current attachment filename when editing an image" do
    image = create(:image, campaign: create(:campaign, user: @user), title: "Beacon Cliffs")

    get edit_image_path(image)

    assert_response :success
    assert_includes response.body, "Current file:"
    assert_includes response.body, image.file.filename.to_s
  end

  test "shows the edit image form with the image as the default cancel path" do
    image = create(:image, campaign: create(:campaign, user: @user), title: "Beacon Cliffs")

    get edit_image_path(image)

    assert_response :success
    assert_match(%r{href="#{image_path(image)}"[^>]*>Cancel<}, response.body)
  end

  test "destroys an image and returns to its album" do
    image = create(:image, campaign: create(:campaign, user: @user))

    assert_difference("Image.count", -1) do
      delete image_path(image)
    end

    assert_redirected_to album_path(image.album)
    assert_nil Image.find_by(id: image.id)
  end

  test "destroys an image in a root album and still returns to its album" do
    campaign = create(:campaign, user: @user)
    album = create(:album, campaign: campaign, folder: campaign.root_folder, name: "Weathered Maps")
    image = create(:image, campaign: campaign, album: album, title: "Beacon Cliffs")

    assert_difference("Image.count", -1) do
      delete image_path(image)
    end

    assert_redirected_to album_path(album)
    assert_nil Image.find_by(id: image.id)
  end

  test "destroys an image via json and returns a redirect url for its album" do
    image = create(:image, campaign: create(:campaign, user: @user))

    assert_difference("Image.count", -1) do
      delete image_path(image), as: :json
    end

    assert_response :ok
    assert_equal "application/json", response.media_type
    assert_equal album_path(image.album), JSON.parse(response.body)["redirect_url"]
    assert_nil Image.find_by(id: image.id)
  end

  private

  # Keep the upload setup tidy across the request examples.
  def uploaded_test_image
    Rack::Test::UploadedFile.new(
      Rails.root.join("test/fixtures/files/test_image.jpg"),
      "image/jpeg"
    )
  end
end
