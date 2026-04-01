require "test_helper"

class PresentationEventTest < ActiveSupport::TestCase
  test "is valid with a campaign and image" do
    presentation_event = build(:presentation_event)

    assert presentation_event.valid?
  end

  test "is valid without an image for cleared events" do
    presentation_event = build(:presentation_event, :cleared)

    assert presentation_event.valid?
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

  test "recent presentations returns the three most recent presented events" do
    campaign = create(:campaign)
    oldest = create(:presentation_event, campaign: campaign, created_at: 4.days.ago)
    second_oldest = create(:presentation_event, campaign: campaign, created_at: 3.days.ago)
    third_oldest = create(:presentation_event, campaign: campaign, created_at: 2.days.ago)
    newest = create(:presentation_event, campaign: campaign, created_at: 1.day.ago)
    create(:presentation_event, :cleared, campaign: campaign, created_at: Time.current)

    assert_equal [ newest.id, third_oldest.id, second_oldest.id ],
                 PresentationEvent.recent_presentations.pluck(:id)
    assert_not_includes PresentationEvent.recent_presentations.pluck(:id), oldest.id
  end
end
