require "test_helper"

class AlbumTest < ActiveSupport::TestCase
  test "is valid with a name, campaign, and folder" do
    album = build(:album)

    assert album.valid?
  end

  test "is invalid without a name" do
    album = build(:album, name: nil)

    assert_not album.valid?
    assert_includes album.errors[:name], "can't be blank"
  end

  test "is invalid without a campaign" do
    album = build(:album, campaign: nil)

    assert_not album.valid?
    assert_includes album.errors[:campaign], "must exist"
  end

  test "is invalid without a folder" do
    album = build(:album, folder: nil)

    assert_not album.valid?
    assert_includes album.errors[:folder], "must exist"
  end

  test "destroying an album destroys its images" do
    album = create(:album)
    image = create(:image, campaign: album.campaign, album: album)

    album.destroy

    assert_nil Image.find_by(id: image.id)
  end

  test "images are ordered by position ascending" do
    album = create(:album)
    image_two = create(:image, campaign: album.campaign, album: album, position: 2)
    image_one = create(:image, campaign: album.campaign, album: album, position: 1)
    image_three = create(:image, campaign: album.campaign, album: album, position: 3)

    assert_equal [ image_one, image_two, image_three ], album.images.to_a
  end
end
