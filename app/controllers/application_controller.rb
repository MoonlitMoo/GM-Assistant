class ApplicationController < ActionController::Base
  include Authentication
  # Only allow modern browsers supporting webp images, web push, badges, import maps, CSS nesting, and CSS :has.
  allow_browser versions: :modern

  helper_method :breadcrumbs

  private

  def breadcrumbs
    @breadcrumbs || []
  end

  def touch_campaign_activity
    return if @campaign.blank?
    return if @campaign.destroyed?
    return if response.status >= 400

    @campaign.touch
  end
end
