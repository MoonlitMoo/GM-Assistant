class ApplicationController < ActionController::Base
  before_action :authenticate_user!, unless: :devise_controller?
  # Only allow modern browsers supporting webp images, web push, badges, import maps, CSS nesting, and CSS :has.
  allow_browser versions: :modern

  helper_method :breadcrumbs

  private

  def after_sign_out_path_for(_resource_or_scope)
    new_user_session_path
  end

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
