class PlayerController < ApplicationController
  allow_unauthenticated_access

  layout "player"
  before_action :set_campaign

  def show
    @player_display = @campaign.player_display || build_player_display_from_preferences
    @current_image = @player_display.current_image
    @current_image_url = current_image_url
    @crossfade_duration = @campaign.user.crossfade_duration
  end

  private

  def set_campaign
    @campaign = Campaign.includes(:user, player_display: { current_image: [ file_attachment: :blob ] }).find(params[:id])
  end

  def current_image_url
    return nil unless @current_image&.file&.attached?
    url_for(@current_image.file)
  end

  def build_player_display_from_preferences
    @campaign.build_player_display(
      transition_type: @campaign.user.default_transition,
      show_title: @campaign.user.default_show_title,
      image_fit: @campaign.user.image_fit
    )
  end
end
