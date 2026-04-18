require "test_helper"

class FolderTest < ActiveSupport::TestCase
  test "is valid with a name, campaign, and parent" do
    folder = build(:folder)

    assert folder.valid?
  end

  test "is invalid without a name" do
    folder = build(:folder, name: nil)

    assert_not folder.valid?
    assert_includes folder.errors[:name], "can't be blank"
  end

  test "is invalid without a campaign" do
    folder = build(:folder, campaign: nil)

    assert_not folder.valid?
    assert_includes folder.errors[:campaign], "must exist"
  end

  test "is invalid without a parent when it is not root" do
    folder = build(:folder, parent: nil)

    assert_not folder.valid?
    assert_includes folder.errors[:parent], "can't be blank"
  end

  test "is valid as a root folder without a parent" do
    folder = build(:folder, :root)

    assert folder.valid?
  end

  test "is invalid when is_root is nil" do
    folder = build(:folder, is_root: nil)

    assert_not folder.valid?
    assert_includes folder.errors[:is_root], "is not included in the list"
  end

  test "is invalid when parent belongs to another campaign" do
    folder = build(:folder, campaign: create(:campaign), parent: create(:folder))

    assert_not folder.valid?
    assert_includes folder.errors[:parent_id], "must belong to same campaign."
  end

  test "is invalid when a root folder has a parent" do
    campaign = build(:campaign)
    folder = build(:folder, :root, campaign: campaign, parent: build(:folder, campaign: campaign))

    assert_not folder.valid?
    assert_includes folder.errors[:parent_id], "must be nil for the root folder."
  end

  test "is invalid when the campaign already has a root folder" do
    campaign = create(:campaign)
    folder = build(:folder, :root, campaign: campaign)

    assert_not folder.valid?
    assert_includes folder.errors[:is_root], "has already been taken"
  end

  test "ancestry returns folders from the top-most ancestor through self without the root" do
    campaign = create(:campaign)
    district = create(:folder, campaign: campaign, parent: campaign.root_folder, name: "Districts")
    villagers = create(:folder, campaign: campaign, parent: district, name: "Villagers")
    market = create(:folder, campaign: campaign, parent: villagers, name: "Market Square")

    assert_equal [ district, villagers, market ], market.ancestry
  end

  test "ancestry is empty for the root folder" do
    campaign = create(:campaign)

    assert_equal [], campaign.root_folder.ancestry
  end

  test "destroying a folder destroys its child folders and albums" do
    folder = create(:folder)
    child_folder = create(:folder, campaign: folder.campaign, parent: folder)
    album = create(:album, campaign: folder.campaign, folder: folder)

    folder.destroy

    assert_nil Folder.find_by(id: child_folder.id)
    assert_nil Album.find_by(id: album.id)
  end
end
