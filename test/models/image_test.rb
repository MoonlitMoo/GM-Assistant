require "test_helper"

class ImageTest < ActiveSupport::TestCase
  test "is valid with a title, campaign, album, and file" do
    image = build(:image)

    assert image.valid?
  end

  test "is invalid without a title" do
    image = build(:image, title: nil)

    assert_not image.valid?
    assert_includes image.errors[:title], "can't be blank"
  end

  test "is invalid without a campaign" do
    image = build(:image, campaign: nil)

    assert_not image.valid?
    assert_includes image.errors[:campaign], "must exist"
  end

  test "is invalid without an album" do
    image = build(:image, album: nil)

    assert_not image.valid?
    assert_includes image.errors[:album], "must exist"
  end

  test "is invalid without a file on create" do
    image = build(:image, file: nil)

    assert_not image.valid?
    assert_includes image.errors[:file], "can't be blank"
  end

  test "is valid without notes" do
    image = build(:image, notes: nil)

    assert image.valid?
  end

  test "is valid without a position" do
    image = build(:image, position: nil)

    assert image.valid?
  end

  test "thumbnail representation can be processed" do
    image = create(:image)

    representation = image.file.representation(resize_to_fill: [ 480, 360 ])

    assert_nothing_raised do
      representation.processed
    end
  end

  test "is invalid when album belongs to another campaign" do
    image = build(:image, campaign: create(:campaign), album: create(:album))

    assert_not image.valid?
    assert_includes image.errors[:album_id], "must belong to same campaign"
  end
end
