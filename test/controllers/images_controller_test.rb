require "test_helper"

class ImagesControllerTest < ActionDispatch::IntegrationTest
  test "shows an image" do
    image = create(:image, title: "Beacon Cliffs", notes: "Windy and bright")

    get image_path(image)

    assert_response :success
    assert_includes response.body, "Beacon Cliffs"
    assert_includes response.body, image.album.name
  end

  test "shows an image inside the content frame for turbo frame requests" do
    image = create(:image, title: "Beacon Cliffs")

    get image_path(image), headers: { "Turbo-Frame" => "content-body" }

    assert_response :success
    assert_match(/<turbo-frame[^>]*id="content-body"/, response.body)
    assert_includes response.body, 'data-turbo-action="advance"'
    assert_includes response.body, "Beacon Cliffs"
  end

  test "shows the new image form" do
    album = create(:album, name: "Weathered Maps")

    get new_album_image_path(album)

    assert_response :success
    assert_includes response.body, "Upload Image"
    assert_includes response.body, "Weathered Maps"
  end

  test "re-renders the new image form when creation is invalid" do
    album = create(:album, name: "Clues")

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
    assert_includes response.body, "Upload Image"
    assert_includes html_response_body, "Title can't be blank"
  end

  test "updates an image" do
    image = create(:image, title: "Old Title", notes: "Old notes")

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

  test "re-renders the edit image form when the update is invalid" do
    image = create(:image)

    patch image_path(image), params: {
      image: {
        title: nil
      }
    }

    assert_response :unprocessable_entity
    assert_includes response.body, "Edit Image"
    assert_includes html_response_body, "Title can't be blank"
  end

  test "destroys an image and returns to its album" do
    image = create(:image)

    assert_difference("Image.count", -1) do
      delete image_path(image)
    end

    assert_redirected_to album_path(image.album)
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
