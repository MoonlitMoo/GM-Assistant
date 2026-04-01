require_relative "application_system_test_case"

class NavigationTest < ApplicationSystemTestCase
  setup do
    @campaign = create(:campaign, name: "Te Whanga")
    @root_folder = @campaign.root_folder
    @folder = create(:folder, campaign: @campaign, parent: @root_folder, name: "Field Notes")
    @album = create(:album, campaign: @campaign, folder: @folder, name: "Harbour Sketches")
    @image = create(:image, campaign: @campaign, album: @album, title: "Beacon Cliffs")
  end

  test "campaign index page loads and lists a campaign" do
    visit campaigns_path

    assert_text "Campaigns"
    assert_link @campaign.name
  end

  test "navigates from the campaign index to the campaign dashboard" do
    visit campaigns_path

    click_link @campaign.name

    assert_current_path campaign_path(@campaign)
    assert_text "Recently Added"
    assert_text @folder.name
    assert_text @album.name
  end

  test "navigates from the campaign dashboard to a top-level folder" do
    visit campaign_path(@campaign)

    click_link @folder.name

    assert_current_path folder_path(@folder)
    assert_text @folder.name
  end

  test "navigates from a folder to an album" do
    visit folder_path(@folder)

    click_link @album.name

    assert_current_path album_path(@album)
    assert_text @album.name
  end

  test "navigates from an album to an image" do
    visit album_path(@album)

    within ".image-card__title" do
      click_link @image.title
    end

    assert_current_path Rails.application.routes.url_helpers.image_path(@image)
    assert_text @image.title
  end

  test "canceling an invalid campaign edit returns to the campaign index" do
    visit campaigns_path

    within find(".campaign-card", text: @campaign.name) do
      click_link "Edit campaign"
    end

    fill_in "Name", with: ""
    click_button "Save Campaign"

    assert_selector ".form-errors", text: "Name can't be blank"

    click_link "Cancel"

    assert_current_path campaigns_path
    assert_link @campaign.name
  end

  test "canceling image edit returns to the image page" do
    visit edit_image_path(@image)
    click_link "Cancel"

    assert_current_path route_helpers.image_path(@image)
    assert_text @image.title
  end

  test "navigates from the sidebar tree and refreshes breadcrumbs" do
    visit folder_path(@root_folder)

    find("#sidebar .tree-label", text: @folder.name).click

    assert_current_path folder_path(@folder)

    within "#breadcrumbs" do
      assert_text @campaign.name
      assert_text @folder.name
      assert_no_text @root_folder.name
    end
  end

  test "persists expanded sidebar folders across campaign page visits" do
    visit folder_path(@root_folder)

    within "#sidebar" do
      assert_selector ".tree-folder .tree-label", text: @folder.name
      assert_no_selector ".tree-album .tree-label", text: @album.name

      find(".tree-folder", text: @folder.name).find(".tree-toggle").click

      assert_selector ".tree-album .tree-label", text: @album.name
      assert_selector ".tree-album i", text: @album.name
    end

    storage_key = "campaign-tree:#{@campaign.id}:expanded"
    expanded_state = page.evaluate_script("JSON.parse(sessionStorage.getItem('#{storage_key}'))")
    assert_equal({ @folder.id.to_s => true }, expanded_state)

    visit album_path(@album)

    within "#sidebar" do
      assert_selector ".tree-album .tree-label", text: @album.name
    end
  end
end
