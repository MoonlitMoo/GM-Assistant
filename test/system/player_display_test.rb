require_relative "application_system_test_case"

class PlayerDisplayTest < ApplicationSystemTestCase
  def self.test(name, *tags, &block)
    labeled_name = [ name, *tags.map { |tag| "[#{tag}]" } ].join(" ")
    super(labeled_name, &block)
  end

  setup do
    @campaign = create(:campaign, name: "Silver Tides")
    @folder = create(:folder, campaign: @campaign, parent: @campaign.root_folder, name: "Harbour Notes")
    @album = create(:album, campaign: @campaign, folder: @folder, name: "Lantern Studies")
    @image = create(:image, campaign: @campaign, album: @album, title: "Beacon Fire")
  end

  test "present button appears on the image show page", :js do
    visit route_helpers.image_path(@image)

    within ".image-show-actions" do
      assert_button "Present"
    end
  end

  test "when the current image is already presenting the present button reflects that state visually", :js do
    create(:player_display, campaign: @campaign, current_image: @image)

    visit route_helpers.image_path(@image)

    assert_selector ".image-show-actions .fantasy-button--active", text: "Presenting"
  end

  test "clear button appears alongside the present button on the image show page", :js do
    visit route_helpers.image_path(@image)

    within ".image-show-actions" do
      assert_button "Present"
      assert_button "Clear display", disabled: true
    end
  end

  test "hovering over an image thumbnail reveals a present button in the top right corner", :js do
    visit album_path(@album)

    opacity_before_hover = page.evaluate_script("getComputedStyle(document.querySelector('.image-card__present-button')).opacity")
    assert_equal "0", opacity_before_hover

    find(".image-card__thumb-shell").hover

    assert_selector ".image-card__present-button", text: "Present"
    opacity_after_hover = page.evaluate_script("getComputedStyle(document.querySelector('.image-card__present-button')).opacity")
    assert_equal "1", opacity_after_hover
  end

  test "clicking the present button updates the button state without a full page reload", :js do
    visit route_helpers.image_path(@image)

    within ".image-show-actions" do
      click_button "Present"
    end

    assert_current_path route_helpers.image_path(@image)
    assert_selector ".image-show-actions .fantasy-button--active", text: "Presenting"
    assert_button "Clear display", disabled: false
    assert_equal @image.id, @campaign.reload.player_display.current_image_id
  end

  test "clearing the display updates the active album overlay", :js do
    create(:player_display, campaign: @campaign, current_image: @image)

    visit album_path(@album)
    assert_selector ".image-card__present-button.fantasy-button--active", text: "Presenting"

    find("#gm-panel summary").click

    within "#gm-status" do
      click_link "Clear display"
    end

    image_card = find(".image-card", text: @image.title)

    assert_no_selector ".image-card__present-button.fantasy-button--active"

    image_card.hover

    within image_card do
      assert_selector ".image-card__present-button", text: "Present"
    end
  end

  test "navigating to the player page returns a page with the minimal player layout", :js do
    visit route_helpers.player_campaign_path(@campaign)

    assert_current_path route_helpers.player_campaign_path(@campaign)
    assert_selector "#player-screen.player-screen-root"
    assert_no_selector "#top-bar"
    assert_no_selector "#sidebar"
    assert_selector "body.player-layout-body"
  end

  test "if a player display exists with a current image that image is visible on the player screen on load", :js do
    create(:player_display, campaign: @campaign, current_image: @image)

    visit route_helpers.player_campaign_path(@campaign)

    assert_selector ".player-screen__image"
    assert_no_selector ".player-screen__blank"
  end

  test "if no player display exists the player screen loads without error and shows a blank state", :js do
    visit route_helpers.player_campaign_path(@campaign)

    assert_selector "#player-screen.player-screen-root"
    assert_selector ".player-screen__blank"
    assert_no_selector ".player-screen__image"
  end

  private

  def route_helpers
    Rails.application.routes.url_helpers
  end
end
