require_relative "application_system_test_case"

class CrudTest < ApplicationSystemTestCase
  setup do
    @user = create(:user)
    sign_in_as(@user)
  end

  test "creates a campaign through the form and shows it in the index" do
    campaign_name = "Cook Strait Chronicle"

    visit campaigns_path
    click_link "New Campaign"

    fill_in "Name", with: campaign_name
    fill_in "Description", with: "Notes from a breezy harbour crossing."

    assert_difference("Campaign.count", 1) do
      click_button "Create Campaign"
    end

    campaign = Campaign.find_by!(name: campaign_name)

    assert_current_path campaign_path(campaign)

    click_link "Back to campaigns"

    assert_current_path campaigns_path
    assert_link campaign_name
  end

  test "submits a campaign form with ctrl enter" do
    campaign_name = "Kauri Coast Chronicle"

    visit new_campaign_path

    fill_in "Name", with: campaign_name
    description = find_field("Description")
    description.set("Notes from a windswept headland.")

    trigger_ctrl_enter(description)

    assert_selector ".record-title", text: campaign_name
    campaign = Campaign.find_by!(name: campaign_name)

    assert_current_path campaign_path(campaign)
    assert_text campaign_name
  end

  test "creates a folder beneath the root folder and shows it in the folder list" do
    campaign = create(:campaign, user: @user, name: "South Coast Survey")
    root_folder = campaign.root_folder
    folder_name = "Wharf Sketches"
    description = "Reference sketches for the old docks."

    visit folder_path(root_folder)

    within ".record-actions" do
      click_link "New Folder"
    end

    fill_in "Name", with: folder_name
    fill_in "Description", with: description

    assert_difference("Folder.count", 1) do
      click_button "Create Folder"
    end

    folder = Folder.find_by!(name: folder_name, parent: root_folder)

    assert_current_path folder_path(root_folder)
    assert_link folder.name
    assert_selector "#sidebar .tree-label", text: folder.name
    assert_equal description, folder.description
  end

  test "creates a top-level folder from the campaign dashboard and returns to the dashboard" do
    campaign = create(:campaign, user: @user, name: "South Coast Survey")
    root_folder = campaign.root_folder
    folder_name = "Wharf Sketches"

    visit campaign_path(campaign)
    click_link "+ New Folder"

    fill_in "Name", with: folder_name

    assert_difference("Folder.count", 1) do
      click_button "Create Folder"
    end

    folder = Folder.find_by!(name: folder_name, parent: root_folder)

    assert_current_path campaign_path(campaign)
    assert_link folder.name
    assert_selector "#sidebar .tree-label", text: folder.name
  end

  test "creates an album beneath a folder and shows it in the folder list" do
    campaign = create(:campaign, user: @user, name: "Northern Lights")
    folder = create(:folder, campaign: campaign, parent: campaign.root_folder, name: "Lantern Notes")
    album_name = "Harbour Evenings"

    visit folder_path(folder)

    within ".record-actions" do
      click_link "New Album"
    end

    fill_in "Name", with: album_name
    fill_in "Description", with: "A tidy set of waterfront references."

    assert_difference("Album.count", 1) do
      click_button "Create Album"
    end

    album = Album.find_by!(name: album_name, folder: folder)

    assert_current_path album_path(album)
    assert_selector "#sidebar .tree-label", text: album.name

    within "#breadcrumbs" do
      click_link folder.name
    end

    assert_current_path folder_path(folder)
    assert_link album.name
  end

  test "uploads an image to an album through the form and shows it in the album" do
    campaign = create(:campaign, user: @user, name: "Rainy Bay")
    folder = create(:folder, campaign: campaign, parent: campaign.root_folder, name: "Storm Files")
    album = create(:album, campaign: campaign, folder: folder, name: "Jetty Studies")
    image_title = "Breakwater at Dawn"

    visit album_path(album)
    click_link "Upload image", match: :first

    fill_in "Title", with: image_title
    fill_in "Description", with: "Soft light over the water."
    attach_file "Image File", test_image_path

    assert_difference("Image.count", 1) do
      click_button "Create Image"
    end

    image = Image.find_by!(title: image_title, album: album)

    assert_current_path album_path(album)
    assert_link image.title

    within ".image-card__title" do
      click_link image.title
    end

    assert_current_path Rails.application.routes.url_helpers.image_path(image)
    assert_text image.title
  end

  test "deletes a campaign and removes it from the index" do
    create(:campaign, user: @user, name: "Sheltered Inlet")
    doomed_campaign = create(:campaign, user: @user, name: "Fading Coast")

    visit campaigns_path

    within find(".campaign-card", text: doomed_campaign.name) do
      assert_difference("Campaign.count", -1) do
        accept_confirm do
          click_link "Delete"
        end
      end
    end

    assert_current_path campaigns_path
    assert_no_link doomed_campaign.name
    assert_link "Sheltered Inlet"
  end

  private

  def test_image_path
    Rails.root.join("test/fixtures/files/test_image.jpg").to_s
  end

  def trigger_ctrl_enter(element)
    page.execute_script(<<~JS, element)
      arguments[0].dispatchEvent(new KeyboardEvent("keydown", {
        key: "Enter",
        code: "Enter",
        ctrlKey: true,
        bubbles: true
      }))
    JS
  end
end
