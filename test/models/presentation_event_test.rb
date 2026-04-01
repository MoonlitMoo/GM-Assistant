require "test_helper"

class PresentationEventTest < ActiveSupport::TestCase
  test "is valid with a campaign and image" do
    presentation_event = build(:presentation_event)

    assert presentation_event.valid?
  end

  test "is valid without an image for cleared events" do
    presentation_event = build(:presentation_event, :cleared_event)

    assert presentation_event.valid?
  end

  test "is valid with both event types" do
    assert build(:presentation_event).valid?
    assert build(:presentation_event, :cleared_event).valid?
  end

  test "is invalid without a campaign" do
    presentation_event = build(:presentation_event, campaign: nil)

    assert_not presentation_event.valid?
    assert_includes presentation_event.errors[:campaign], "can't be blank"
  end

  test "is invalid without an event type" do
    presentation_event = build(:presentation_event, event_type: nil)

    assert_not presentation_event.valid?
    assert_includes presentation_event.errors[:event_type], "can't be blank"
  end

  test "recent for panel returns only presented events" do
    campaign = create(:campaign)
    presented_event = create(:presentation_event, campaign: campaign, created_at: timestamp("2026-04-01 10:00:00"))
    create(:presentation_event, :cleared_event, campaign: campaign, created_at: timestamp("2026-04-01 11:00:00"))

    assert_equal [ presented_event.id ], PresentationEvent.recent_for_panel(campaign).map(&:id)
  end

  test "recent for panel excludes events with null image ids" do
    campaign = create(:campaign)
    presented_event = create(:presentation_event, campaign: campaign, created_at: timestamp("2026-04-01 10:00:00"))
    create(:presentation_event, campaign: campaign, image: nil, image_title: "Missing image", created_at: timestamp("2026-04-01 11:00:00"))

    assert_equal [ presented_event.id ], PresentationEvent.recent_for_panel(campaign).map(&:id)
  end

  test "recent for panel excludes the currently live image when provided" do
    campaign = create(:campaign)
    excluded_image = create(:image, campaign: campaign)
    kept_image = create(:image, campaign: campaign)
    create(:presentation_event, campaign: campaign, image: excluded_image, image_title: excluded_image.title, created_at: timestamp("2026-04-01 11:00:00"))
    kept_event = create(:presentation_event, campaign: campaign, image: kept_image, image_title: kept_image.title, created_at: timestamp("2026-04-01 10:00:00"))

    assert_equal [ kept_event.id ],
                 PresentationEvent.recent_for_panel(campaign, excluding_image: excluded_image).map(&:id)
  end

  test "recent for panel deduplicates by image using the most recent event" do
    campaign = create(:campaign)
    repeated_image = create(:image, campaign: campaign)
    other_image = create(:image, campaign: campaign)
    older_event = create(:presentation_event, campaign: campaign, image: repeated_image, image_title: repeated_image.title, created_at: timestamp("2026-04-01 09:00:00"))
    newer_event = create(:presentation_event, campaign: campaign, image: repeated_image, image_title: repeated_image.title, created_at: timestamp("2026-04-01 11:00:00"))
    other_event = create(:presentation_event, campaign: campaign, image: other_image, image_title: other_image.title, created_at: timestamp("2026-04-01 10:00:00"))

    assert_equal [ newer_event.id, other_event.id ],
                 PresentationEvent.recent_for_panel(campaign).map(&:id)
    assert_not_includes PresentationEvent.recent_for_panel(campaign).map(&:id), older_event.id
  end

  test "recent for panel limits results to three entries" do
    campaign = create(:campaign)
    first = create(:presentation_event, campaign: campaign, created_at: timestamp("2026-04-01 12:00:00"))
    second = create(:presentation_event, campaign: campaign, created_at: timestamp("2026-04-01 11:00:00"))
    third = create(:presentation_event, campaign: campaign, created_at: timestamp("2026-04-01 10:00:00"))
    create(:presentation_event, campaign: campaign, created_at: timestamp("2026-04-01 09:00:00"))

    assert_equal [ first.id, second.id, third.id ],
                 PresentationEvent.recent_for_panel(campaign).map(&:id)
  end

  test "recent for panel returns results ordered by most recent first" do
    campaign = create(:campaign)
    oldest = create(:presentation_event, campaign: campaign, created_at: timestamp("2026-04-01 09:00:00"))
    middle = create(:presentation_event, campaign: campaign, created_at: timestamp("2026-04-01 10:00:00"))
    newest = create(:presentation_event, campaign: campaign, created_at: timestamp("2026-04-01 11:00:00"))

    assert_equal [ newest.id, middle.id, oldest.id ],
                 PresentationEvent.recent_for_panel(campaign).map(&:id)
  end

  test "image title snapshot persists after the image is destroyed" do
    presentation_event = create(:presentation_event)
    image_title = presentation_event.image_title

    presentation_event.image.destroy

    assert_nil presentation_event.reload.image
    assert_equal image_title, presentation_event.image_title
  end

  private

  def timestamp(value)
    Time.zone.parse(value)
  end
end
