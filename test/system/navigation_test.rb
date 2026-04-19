require_relative "application_system_test_case"

class NavigationTest < ApplicationSystemTestCase
  setup do
    @user = create(:user)
    @campaign = create(:campaign, user: @user, name: "Te Whanga")
    @root_folder = @campaign.root_folder
    @folder = create(:folder, campaign: @campaign, parent: @root_folder, name: "Field Notes")
    @album = create(:album, campaign: @campaign, folder: @folder, name: "Harbour Sketches")
    @image = create(:image, campaign: @campaign, album: @album, title: "Beacon Cliffs")
    sign_in_as(@user)
  end

  test "campaign index page loads and lists a campaign" do
    visit campaigns_path

    assert_text "Campaigns"
    assert_link @campaign.name
  end

  test "shows an explicit empty state in the sidebar when the campaign tree has no items" do
    empty_campaign = create(:campaign, user: @user, name: "Blank Atlas")

    visit campaign_path(empty_campaign)

    assert_link "+ New Folder", href: new_folder_folder_path(empty_campaign.root_folder, return_to: campaign_path(empty_campaign))
    assert_link "+ New Album", href: new_folder_album_path(empty_campaign.root_folder, return_to: campaign_path(empty_campaign))
    assert_text "No folders at the top level yet."
    assert_text "No albums at the top level yet."

    within "#campaign-tree" do
      assert_text(/Campaign library is empty/i)
      assert_text "Create a folder or album to start organizing this campaign."
    end
  end

  test "navigates from the campaign index to the campaign dashboard" do
    visit campaigns_path

    within find(".campaign-card", text: @campaign.name) do
      find(".campaign-card__title a", text: @campaign.name, exact_text: true).click
    end

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

  test "navigates from breadcrumbs without remounting the sidebar tree" do
    visit album_path(@album)

    page.execute_script("document.getElementById('campaign-tree').dataset.persistMarker = 'kept'")

    within "#breadcrumbs" do
      click_link @folder.name
    end

    assert_current_path folder_path(@folder)
    assert_equal "kept", page.evaluate_script("document.getElementById('campaign-tree').dataset.persistMarker")
  end

  test "expands the sidebar tree to the current nested folder" do
    nested_folder = create(:folder, campaign: @campaign, parent: @folder, name: "Signal Fires")
    nested_album = create(:album, campaign: @campaign, folder: nested_folder, name: "Watch Posts")

    visit folder_path(nested_folder)

    assert_selector "#sidebar .tree-folder .tree-label", text: @folder.name
    assert_selector "#sidebar .tree-folder .tree-label", text: nested_folder.name
    assert_selector "#sidebar .tree-album .tree-label", text: nested_album.name

    storage_key = "campaign-tree:#{@campaign.id}:expanded"
    expanded_state = page.evaluate_script("JSON.parse(sessionStorage.getItem('#{storage_key}'))")
    assert_equal({ @folder.id.to_s => true, nested_folder.id.to_s => true }, expanded_state)
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

  test "sidebar context menu opens on a folder node and can navigate to new subfolder form" do
    visit folder_path(@root_folder)

    find("#sidebar .tree-folder .tree-label", text: @folder.name).right_click

    within ".tree-context-menu" do
      assert_button "New Subfolder"
      assert_button "New Album"
      assert_button "Rename"
      assert_button "Edit"
      assert_button "Delete"
      click_button "New Subfolder"
    end

    assert_current_path new_folder_folder_path(@folder, return_to: folder_path(@root_folder))
    assert_text "New Folder"
  end

  test "sidebar root library context menu can navigate to a new root album form" do
    visit folder_path(@root_folder)

    tree_surface = find("#campaign-tree .tree-surface")
    page.execute_script(<<~JS, tree_surface)
      const rect = arguments[0].getBoundingClientRect()
      arguments[0].dispatchEvent(new MouseEvent("contextmenu", {
        bubbles: true,
        cancelable: true,
        clientX: rect.left + 24,
        clientY: rect.bottom - 24
      }))
    JS

    within ".tree-context-menu" do
      assert_button "New Folder"
      assert_button "New Album"
      click_button "New Album"
    end

    assert_current_path new_folder_album_path(@root_folder, return_to: folder_path(@root_folder))
    assert_text "New Album"
  end

  test "invalid subfolder creation from the sidebar can cancel back to the originating page" do
    visit folder_path(@root_folder)

    find("#sidebar .tree-folder .tree-label", text: @folder.name).right_click

    within ".tree-context-menu" do
      click_button "New Subfolder"
    end

    assert_current_path new_folder_folder_path(@folder, return_to: folder_path(@root_folder))

    click_button "Create Folder"

    assert_selector ".form-errors", text: "Name can't be blank"

    click_link "Cancel"

    assert_current_path folder_path(@root_folder)
  end

  test "sidebar root library surface fills the tree area above gm controls" do
    visit folder_path(@root_folder)

    assert_selector "#campaign-tree .tree-surface"
    assert_selector "#sidebar .tree-folder .tree-label", text: @folder.name

    dimensions = page.evaluate_script(<<~JS)
      (() => {
        const tree = document.getElementById("campaign-tree")?.getBoundingClientRect()
        const surface = document.querySelector("#campaign-tree .tree-surface")?.getBoundingClientRect()

        return {
          treeHeight: tree?.height || 0,
          surfaceHeight: surface?.height || 0
        }
      })()
    JS

    assert_operator dimensions["treeHeight"], :>, 0
    assert_operator dimensions["surfaceHeight"], :>=, dimensions["treeHeight"] - 1
  end

  test "sidebar context menu can rename a folder inline and refresh the tree" do
    nested_folder = create(:folder, campaign: @campaign, parent: @folder, name: "Signal Fires")

    visit folder_path(@root_folder)

    within "#sidebar" do
      find(".tree-folder", text: @folder.name).find(".tree-toggle").click
      find(".tree-folder .tree-label", text: nested_folder.name).right_click
    end

    within ".tree-context-menu" do
      click_button "Rename"
    end

    within "#sidebar" do
      input = find(".tree-rename-input", visible: true)
      input.set("Watch Posts")
      input.send_keys(:enter)
      assert_selector ".tree-folder .tree-label", text: "Watch Posts"
    end
  end

  test "sidebar rename updates the currently displayed folder page" do
    nested_folder = create(:folder, campaign: @campaign, parent: @folder, name: "Signal Fires")

    visit folder_path(nested_folder)

    within "#sidebar" do
      find(".tree-folder .tree-label", text: nested_folder.name).right_click
    end

    within ".tree-context-menu" do
      click_button "Rename"
    end

    within "#sidebar" do
      input = find(".tree-rename-input", visible: true)
      input.set("Watch Posts")
      input.send_keys(:enter)
    end

    nested_folder.reload

    assert_current_path folder_path(nested_folder)
    assert_selector ".record-title", text: "Watch Posts"

    within "#breadcrumbs" do
      assert_text "Watch Posts"
    end
  end

  test "sidebar context menu can delete a folder through the confirmation modal" do
    nested_folder = create(:folder, campaign: @campaign, parent: @folder, name: "Signal Fires")
    create(:folder, campaign: @campaign, parent: nested_folder, name: "Watchtower")
    nested_album = create(:album, campaign: @campaign, folder: nested_folder, name: "Lantern Studies")
    create(:image, campaign: @campaign, album: nested_album, title: "Signal Flame")

    visit folder_path(@root_folder)

    within "#sidebar" do
      find(".tree-folder", text: @folder.name).find(".tree-toggle").click
      find(".tree-folder .tree-label", text: nested_folder.name).right_click
    end

    within ".tree-context-menu" do
      click_button "Delete"
    end

    within ".tree-delete-modal" do
      assert_text "Delete Folder"
      assert_text "1 subfolder"
      assert_text "1 album"
      assert_text "1 image"
      assert_text "This cannot be undone."
      click_button "Cancel"
    end

    assert_no_selector ".tree-delete-modal"

    within "#sidebar" do
      find(".tree-folder .tree-label", text: nested_folder.name).right_click
    end

    within ".tree-context-menu" do
      click_button "Delete"
    end

    within ".tree-delete-modal" do
      click_button "Delete"
    end

    assert_nil Folder.find_by(id: nested_folder.id)

    within "#sidebar" do
      assert_no_selector ".tree-folder .tree-label", text: nested_folder.name, wait: 10
    end
  end

  test "sidebar delete redirects a selected top-level folder to the campaign page" do
    visit folder_path(@folder)

    within "#sidebar" do
      find(".tree-folder .tree-label", text: @folder.name).right_click
    end

    within ".tree-context-menu" do
      click_button "Delete"
    end

    within ".tree-delete-modal" do
      click_button "Delete"
    end

    assert_current_path campaign_path(@campaign)
    assert_no_selector ".record-title", text: @folder.name
  end

  test "folder show delete button uses the modal" do
    visit folder_path(@folder)

    click_button "Delete folder"

    within ".tree-delete-modal" do
      assert_text "Delete Folder"
      assert_text @folder.name
      assert_text "0 subfolders"
      assert_text "1 album"
      assert_text "1 image"
      click_button "Cancel"
    end

    assert_no_selector ".tree-delete-modal"
    assert_current_path folder_path(@folder)
  end

  test "tree and page deletes share the same modal instance" do
    visit folder_path(@folder)

    assert_equal 1, page.evaluate_script("document.querySelectorAll('[data-record-delete-modal-target=\"modal\"]').length")

    click_button "Delete folder"

    within ".tree-delete-modal" do
      click_button "Cancel"
    end

    within "#sidebar" do
      find(".tree-folder .tree-label", text: @folder.name).right_click
    end

    within ".tree-context-menu" do
      click_button "Delete"
    end

    assert_equal 1, page.evaluate_script("document.querySelectorAll('[data-record-delete-modal-target=\"modal\"]').length")

    within ".tree-delete-modal" do
      click_button "Cancel"
    end
  end

  test "album show delete button uses the modal and deletes the album" do
    visit album_path(@album)

    click_button "Delete album"

    within ".tree-delete-modal" do
      assert_text "Delete Album"
      assert_text @album.name
      assert_text "1 image will be deleted."
      click_button "Delete"
    end

    assert_current_path folder_path(@folder)
    assert_nil Album.find_by(id: @album.id)
  end

  test "image show delete button uses the modal and deletes the image" do
    visit route_helpers.image_path(@image)

    click_button "Delete image"

    within ".tree-delete-modal" do
      assert_text "Delete Image"
      assert_text @image.title
      assert_text "This image will be removed from the archive."
      click_button "Delete"
    end

    assert_current_path album_path(@album)
    assert_nil Image.find_by(id: @image.id)
  end

  test "album image context menu can rename an image inline" do
    visit album_path(@album)

    card = find(".image-card", text: @image.title)
    card.right_click

    within ".tree-context-menu" do
      click_button "Rename"
    end

    within card do
      input = find(".image-card__rename-input")
      input.set("Beacon Fire Revised")
      input.send_keys(:enter)
    end

    assert_current_path album_path(@album)
    assert_selector ".image-card__title", text: "Beacon Fire Revised"
    within card do
      assert_selector ".image-card__preview"
    end
    assert_equal "Beacon Fire Revised", @image.reload.title
  end

  test "album image context menu toggles title visibility" do
    visit album_path(@album)

    card = find(".image-card", text: @image.title)
    card.right_click

    within ".tree-context-menu" do
      click_button "Show Title"
    end

    assert_selector ".image-card__meta", text: /title visible on player screen/i
    assert_equal true, @image.reload.show_title
  end

  test "album image context menu deletes an image without leaving the album page" do
    visit album_path(@album)

    find(".image-card", text: @image.title).right_click

    within ".tree-context-menu" do
      click_button "Delete"
    end

    within ".tree-delete-modal" do
      assert_text "Delete Image"
      assert_text @image.title
      click_button "Delete"
    end

    assert_current_path album_path(@album)
    assert_no_selector ".image-card__title", text: @image.title
    assert_nil Image.find_by(id: @image.id)
  end
end
