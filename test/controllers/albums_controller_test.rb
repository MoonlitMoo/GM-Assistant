require "test_helper"

class AlbumsControllerTest < ActionDispatch::IntegrationTest
  test "shows the new album form" do
    folder = create(:folder, name: "Landmarks")

    get new_folder_album_path(folder)

    assert_response :success
    assert_includes response.body, "New Album"
    assert_includes response.body, "Landmarks"
  end

  test "re-renders the new album form when creation is invalid" do
    folder = create(:folder)

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

  test "shows the edit album form" do
    album = create(:album, name: "Gallery")

    get edit_album_path(album)

    assert_response :success
    assert_includes response.body, "Edit Album"
    assert_includes response.body, "Gallery"
  end

  test "updates an album" do
    album = create(:album, name: "Old Gallery", description: "Old notes")

    patch album_path(album), params: {
      album: {
        name: "New Gallery",
        description: "Fresh notes"
      }
    }

    assert_redirected_to album_path(album)
    album.reload
    assert_equal "New Gallery", album.name
    assert_equal "Fresh notes", album.description
  end

  test "re-renders the edit album form when the update is invalid" do
    album = create(:album)

    patch album_path(album), params: {
      album: {
        name: nil
      }
    }

    assert_response :unprocessable_entity
    assert_includes response.body, "Edit Album"
    assert_includes html_response_body, "Name can't be blank"
  end

  test "destroys an album and returns to its folder" do
    album = create(:album)

    assert_difference("Album.count", -1) do
      delete album_path(album)
    end

    assert_redirected_to folder_path(album.folder)
    assert_nil Album.find_by(id: album.id)
  end
end
